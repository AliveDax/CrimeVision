// State variables
let map;
let markerLayer = L.layerGroup();
let hotspotLayer = L.layerGroup();
let queryMarker = null;
let streamInterval = null;

let categoryChart = null;
let hourlyChart = null;

// Default map configurations (Centered on India national view)
const defaultCenter = [22.9734, 78.6569];
const defaultZoom = 5;

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initUI();
    loadDashboardData();
});

// Toast notification helper
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastText = document.getElementById('toast-text');
    
    toast.className = 'toast-msg';
    if (type === 'success') toast.classList.add('success');
    if (type === 'error') toast.classList.add('error');
    
    toastText.textContent = message;
    toast.style.display = 'block';
    
    setTimeout(() => {
        toast.style.display = 'none';
    }, 4000);
}

// Map setup
function initMap() {
    map = L.map('map', {
        zoomControl: false
    }).setView(defaultCenter, defaultZoom);
    
    // Premium Dark Matter CartoDB tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);
    
    L.control.zoom({ position: 'bottomright' }).addTo(map);
    
    markerLayer.addTo(map);
    hotspotLayer.addTo(map);
    
    // Map click behavior: capture lat/lon for prediction query
    map.on('click', (e) => {
        const lat = e.latlng.lat;
        const lon = e.latlng.lng;
        
        document.getElementById('pred-lat').value = lat.toFixed(5);
        document.getElementById('pred-lon').value = lon.toFixed(5);
        
        // Update query marker visual indicator
        if (queryMarker) {
            queryMarker.setLatLng(e.latlng);
        } else {
            const queryIcon = L.divIcon({
                className: 'custom-query-icon',
                html: '<i class="fa-solid fa-location-crosshairs" style="color: #0ea5e9; font-size: 24px; text-shadow: 0 0 8px rgba(14,165,233,0.8);"></i>',
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            });
            queryMarker = L.marker(e.latlng, { icon: queryIcon }).addTo(map);
        }
        
        // Ensure sidebar is expanded to show results separately
        if (window.showWidgetTab) {
            window.showWidgetTab(1);
        }
        
        // Trigger prediction directly
        calculatePrediction(lat, lon);
    });
}

// Controls UI listeners
function initUI() {
    const kSlider = document.getElementById('cluster-k');
    const kValue = document.getElementById('k-value');
    
    kSlider.addEventListener('input', (e) => {
        kValue.textContent = e.target.value;
    });
    
    // Recluster button
    document.getElementById('btn-recluster').addEventListener('click', () => {
        loadDashboardData();
    });
    
    // Calculate prediction manually button
    document.getElementById('btn-predict').addEventListener('click', () => {
        const lat = parseFloat(document.getElementById('pred-lat').value);
        const lon = parseFloat(document.getElementById('pred-lon').value);
        
        if (isNaN(lat) || isNaN(lon)) {
            showToast('Please select coordinates on the map or enter values manually.', 'error');
            return;
        }
        calculatePrediction(lat, lon);
    });
    
    // Reset dataset button
    document.getElementById('btn-reset').addEventListener('click', () => {
        fetch('/api/reset', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showToast(data.message, 'success');
                    document.getElementById('upload-status-lbl').textContent = "Using default preloaded dataset.";
                    loadDashboardData();
                }
            })
            .catch(() => showToast('Failed to reset dataset.', 'error'));
    });
    
    // File upload
    const fileInput = document.getElementById('csv-file-input');
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        showToast('Uploading custom crime dataset...', 'info');
        
        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast(data.message, 'success');
                document.getElementById('upload-status-lbl').textContent = `Using custom uploaded dataset (${data.records_count} rows).`;
                loadDashboardData();
            } else {
                showToast(data.message || 'Upload failed', 'error');
            }
        })
        .catch(() => {
            showToast('Connection error during file upload.', 'error');
        });
    });
    
    // Live CCTNS stream listener
    const chkLive = document.getElementById('chk-live-stream');
    const tickerContainer = document.getElementById('live-ticker-container');
    const tickerList = document.getElementById('live-ticker-list');
    const tickerPlaceholder = document.getElementById('live-ticker-placeholder');
    
    chkLive.addEventListener('change', (e) => {
        if (e.target.checked) {
            tickerContainer.style.display = 'block';
            tickerList.innerHTML = '';
            tickerPlaceholder.style.display = 'block';
            showToast('Listening for live CCTNS FIR logs...', 'info');
            // Poll CCTNS stream every 6 seconds
            streamInterval = setInterval(() => {
                pollLiveCCTNSFeed(tickerList, tickerPlaceholder);
            }, 6000);
        } else {
            tickerContainer.style.display = 'none';
            if (streamInterval) {
                clearInterval(streamInterval);
                streamInterval = null;
            }
            showToast('CCTNS Live Feed disconnected.', 'info');
        }
    });
    
    // Sidebar hover/click expanders
    const sidebar = document.getElementById('sidebar');
    const closeTrigger = document.querySelector('.sidebar-close-trigger');
    const expandArrow = document.querySelector('.sidebar-expand-arrow');
    
    const expandSidebar = () => {
        sidebar.classList.remove('collapsed');
        sidebar.classList.add('expanded');
    };
    
    const collapseSidebar = () => {
        sidebar.classList.remove('expanded');
        sidebar.classList.add('collapsed');
    };
    
    closeTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        collapseSidebar();
    });
    
    expandArrow.addEventListener('click', (e) => {
        e.stopPropagation();
        if (sidebar.classList.contains('collapsed')) {
            expandSidebar();
        } else {
            collapseSidebar();
        }
    });
    
    // Sidebar icon navigation tabs switcher
    const icons = document.querySelectorAll('.sidebar-icon-btn');
    const widgets = [
        document.getElementById('widget-controls'),
        document.getElementById('widget-predict'),
        document.getElementById('widget-live-stream'),
        document.getElementById('widget-upload')
    ];
    
    const showWidgetTab = (index) => {
        expandSidebar();
        widgets.forEach((w, idx) => {
            if (idx === index) {
                w.style.display = 'block';
            } else {
                w.style.display = 'none';
            }
        });
        icons.forEach((icon, idx) => {
            if (idx === index) {
                icon.classList.add('active-icon');
            } else {
                icon.classList.remove('active-icon');
            }
        });
    };
    
    // Make showWidgetTab accessible globally
    window.showWidgetTab = showWidgetTab;
    
    // Bind click events on toolbar icons
    icons.forEach((icon, index) => {
        icon.addEventListener('click', (e) => {
            e.stopPropagation();
            showWidgetTab(index);
        });
    });
    
    // Initialize to show controls tab separately by default (others hidden)
    showWidgetTab(0);
    
    // Charts bottom-right drawer slide controls
    const chartsDrawer = document.getElementById('charts-drawer');
    const btnDrawerOpen = document.getElementById('btn-charts-drawer-toggle');
    const btnDrawerClose = document.getElementById('btn-close-drawer');
    
    btnDrawerOpen.addEventListener('click', () => {
        chartsDrawer.classList.remove('collapsed-drawer');
        btnDrawerOpen.style.display = 'none';
        
        // Resize charts to prevent canvas layout glitches when expanded
        setTimeout(() => {
            if (categoryChart) categoryChart.resize();
            if (hourlyChart) hourlyChart.resize();
        }, 400);
    });
    
    btnDrawerClose.addEventListener('click', () => {
        chartsDrawer.classList.add('collapsed-drawer');
        setTimeout(() => {
            btnDrawerOpen.style.display = 'flex';
        }, 300);
    });
}

// Fetch dashboard statistical insights and markers from backend
function loadDashboardData() {
    const kVal = document.getElementById('cluster-k').value;
    const catVal = document.getElementById('filter-category').value;
    
    showToast('Running K-Means analytics...', 'info');
    
    fetch(`/api/analyze?k=${kVal}&category=${catVal}`)
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                showToast(data.message, 'error');
                return;
            }
            
            // Clear layers
            markerLayer.clearLayers();
            hotspotLayer.clearLayers();
            if (queryMarker) {
                map.removeLayer(queryMarker);
                queryMarker = null;
            }
            
            // Update stats
            document.getElementById('val-total-incidents').textContent = data.summary.total_incidents;
            document.getElementById('val-hotspots').textContent = data.hotspots.length;
            
            // Primary Concern mode
            let topConcern = "None";
            let topCount = 0;
            for (let cat in data.summary.category_counts) {
                if (data.summary.category_counts[cat] > topCount) {
                    topCount = data.summary.category_counts[cat];
                    topConcern = cat;
                }
            }
            document.getElementById('val-primary-concern').textContent = topConcern;
            
            // Render points and center map
            const coords = [];
            
            // Incident mapping
            const colorMapping = {
                'Theft': '#0ea5e9',      // Blue
                'Assault': '#f43f5e',    // Rose Red
                'Burglary': '#a855f7',   // Purple
                'Cyber Crime': '#f59e0b', // Orange
                'Harassment': '#10b981'  // Green
            };
            
            data.incidents.forEach(p => {
                const col = colorMapping[p.category] || '#64748b';
                
                const circle = L.circleMarker([p.latitude, p.longitude], {
                    radius: 3.5,
                    fillColor: col,
                    color: '#ffffff',
                    weight: 0.5,
                    opacity: 0.6,
                    fillOpacity: 0.75
                });
                
                const popupContent = `
                    <div class="map-popup-header">${p.category}</div>
                    <div class="map-popup-detail"><span class="map-popup-label">Time:</span> ${p.timestamp}</div>
                    <div class="map-popup-detail"><span class="map-popup-label">Severity Index:</span> ${p.severity}/5</div>
                    <div class="map-popup-detail" style="margin-top:0.4rem; font-style:italic;">"${p.description}"</div>
                `;
                circle.bindPopup(popupContent);
                markerLayer.addLayer(circle);
                
                coords.push([p.latitude, p.longitude]);
            });
            
            // Render hotspots as heat-colored pulsing centroid nodes
            data.hotspots.forEach(hot => {
                // Outer circle for hotspot area proportional to amount of records
                const areaCircle = L.circle([hot.latitude, hot.longitude], {
                    radius: 10000 + (hot.density_percentage * 1500), // scale radius based on density percentage
                    color: '#f43f5e',
                    weight: 1,
                    fillColor: '#f43f5e',
                    fillOpacity: 0.18 + (hot.average_severity * 0.03) // higher severity = darker hotspot
                });
                
                // Centroid focal dot
                const centerDot = L.circleMarker([hot.latitude, hot.longitude], {
                    radius: 8,
                    fillColor: '#f43f5e',
                    color: '#ffffff',
                    weight: 1.5,
                    fillOpacity: 1.0
                });
                
                const hotspotPopup = `
                    <div class="map-popup-header" style="color:#f43f5e;"><i class="fa-solid fa-fire"></i> Hotspot #${hot.id}</div>
                    <div class="map-popup-detail"><span class="map-popup-label">Relative Load:</span> ${hot.size} incidents (${hot.density_percentage}%)</div>
                    <div class="map-popup-detail"><span class="map-popup-label">Dominant Category:</span> ${hot.dominant_category}</div>
                    <div class="map-popup-detail"><span class="map-popup-label">Average Severity:</span> ${hot.average_severity}/5</div>
                `;
                areaCircle.bindPopup(hotspotPopup);
                centerDot.bindPopup(hotspotPopup);
                
                hotspotLayer.addLayer(areaCircle);
                hotspotLayer.addLayer(centerDot);
            });
            
            // Fit map boundary viewport automatically if coords are loaded
            if (coords.length > 0) {
                map.fitBounds(L.latLngBounds(coords), { padding: [40, 40] });
            }
            
            // Redraw charts
            updateCharts(data.summary);
            showToast('Data processing models compiled successfully.', 'success');
        })
        .catch(() => showToast('Failed to fetch clustering data.', 'error'));
}

// Compute spatial KNN predictions for selected points
function calculatePrediction(lat, lon) {
    const hourVal = document.getElementById('pred-hour').value;
    
    fetch(`/api/predict?lat=${lat}&lon=${lon}&hour=${hourVal}`)
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                showToast(data.message, 'error');
                return;
            }
            
            const pred = data.prediction;
            
            // Toggle container visible
            const resultsDiv = document.getElementById('pred-results');
            resultsDiv.style.display = 'block';
            
            // Update labels
            const badge = document.getElementById('res-badge');
            badge.textContent = pred.risk_level;
            badge.className = 'risk-level-badge ' + pred.risk_level.toLowerCase();
            
            const scoreLabel = document.getElementById('res-score');
            scoreLabel.textContent = `${pred.risk_score}%`;
            
            const catLabel = document.getElementById('res-cat');
            catLabel.textContent = pred.predicted_category;
            
            const fillMeter = document.getElementById('res-meter');
            fillMeter.style.width = `${pred.risk_score}%`;
            
            // Progress fill colors based on threat rating
            if (pred.risk_level === 'Low') {
                fillMeter.style.backgroundColor = 'var(--risk-low)';
            } else if (pred.risk_level === 'Medium') {
                fillMeter.style.backgroundColor = 'var(--risk-med)';
            } else {
                fillMeter.style.backgroundColor = 'var(--risk-high)';
            }
            
            // Advice description block
            const adviceBlock = document.getElementById('res-advice');
            adviceBlock.className = 'advice-card ' + pred.risk_level.toLowerCase();
            adviceBlock.querySelector('p').textContent = pred.safety_recommendation;
            
            showToast(`Evaluated geographic risk score: ${pred.risk_score}%`, 'success');
        })
        .catch(() => showToast('Failed to compute safety prediction.', 'error'));
}

// Draw & refresh metrics graphs
function updateCharts(summary) {
    // 1. Categories distribution Chart
    const categoriesData = Object.values(summary.category_counts);
    const categoriesLabels = Object.keys(summary.category_counts);
    
    const categoryColors = [
        '#0ea5e9', // Theft - Blue
        '#f43f5e', // Assault - Red
        '#a855f7', // Burglary - Purple
        '#f59e0b', // Vandalism - Orange
        '#10b981'  // Drug Offense - Green
    ];
    
    if (categoryChart) {
        categoryChart.data.labels = categoriesLabels;
        categoryChart.data.datasets[0].data = categoriesData;
        categoryChart.update();
    } else {
        const ctx1 = document.getElementById('chart-categories').getContext('2d');
        categoryChart = new Chart(ctx1, {
            type: 'doughnut',
            data: {
                labels: categoriesLabels,
                datasets: [{
                    data: categoriesData,
                    backgroundColor: categoryColors,
                    borderWidth: 1,
                    borderColor: '#1e293b'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#e2e8f0',
                            font: { family: 'Inter', size: 10 }
                        }
                    }
                }
            }
        });
    }
    
    // 2. Hourly trend Chart
    const hoursData = summary.hourly_counts;
    const hoursLabels = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, '0')}:00`);
    
    if (hourlyChart) {
        hourlyChart.data.datasets[0].data = hoursData;
        hourlyChart.update();
    } else {
        const ctx2 = document.getElementById('chart-hourly').getContext('2d');
        hourlyChart = new Chart(ctx2, {
            type: 'line',
            data: {
                labels: hoursLabels,
                datasets: [{
                    label: 'Crimes Count',
                    data: hoursData,
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.1)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        ticks: { color: '#64748b', font: { size: 9 } },
                        grid: { color: 'rgba(255, 255, 255, 0.03)' }
                    },
                    y: {
                        ticks: { color: '#64748b', font: { size: 9 } },
                        grid: { color: 'rgba(255, 255, 255, 0.03)' }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}

function pollLiveCCTNSFeed(tickerList, tickerPlaceholder) {
    fetch('/api/stream-update')
        .then(res => res.json())
        .then(data => {
            if (data.success && data.new_crimes.length > 0) {
                tickerPlaceholder.style.display = 'none';
                
                document.getElementById('val-total-incidents').textContent = data.total_records_count;
                
                const colorMapping = {
                    'Theft': '#0ea5e9',
                    'Assault': '#f43f5e',
                    'Burglary': '#a855f7',
                    'Cyber Crime': '#f59e0b',
                    'Harassment': '#10b981'
                };
                
                data.new_crimes.forEach(c => {
                    const li = document.createElement('li');
                    li.style.borderBottom = '1px solid var(--card-border)';
                    li.style.padding = '0.35rem 0';
                    li.style.animation = 'slideUp 0.3s ease-out forwards';
                    
                    const timeOnly = c.timestamp.split(' ')[1];
                    li.innerHTML = `
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:600; color: ${colorMapping[c.category] || '#ffffff'};">[${c.category}]</span>
                            <span style="font-size:0.65rem; color:var(--text-muted);">${timeOnly}</span>
                        </div>
                        <div style="color:var(--text-secondary); font-size:0.7rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                            ${c.description}
                        </div>
                    `;
                    
                    tickerList.insertBefore(li, tickerList.firstChild);
                    
                    while (tickerList.children.length > 10) {
                        tickerList.removeChild(tickerList.lastChild);
                    }
                    
                    const pulseMarker = L.circleMarker([c.latitude, c.longitude], {
                        radius: 7.5,
                        fillColor: colorMapping[c.category] || '#64748b',
                        color: '#ffffff',
                        weight: 2,
                        fillOpacity: 1.0
                    });
                    
                    const livePopupContent = `
                        <div class="map-popup-header" style="color: var(--risk-high);"><i class="fa-solid fa-satellite-dish fa-beat"></i> Live FIR Report</div>
                        <div class="map-popup-detail"><span class="map-popup-label">FIR ID:</span> ${c.id}</div>
                        <div class="map-popup-detail"><span class="map-popup-label">Category:</span> ${c.category}</div>
                        <div class="map-popup-detail"><span class="map-popup-label">Time:</span> ${c.timestamp}</div>
                        <div class="map-popup-detail" style="margin-top:0.4rem; font-style:italic;">"${c.description}"</div>
                    `;
                    pulseMarker.bindPopup(livePopupContent);
                    markerLayer.addLayer(pulseMarker);
                    pulseMarker.openPopup();
                });
                
                showToast(`Received ${data.new_records_count} live CCTNS dispatch logs.`, 'success');
            }
        })
        .catch(() => console.log('CCTNS Feed polling error.'));
}

