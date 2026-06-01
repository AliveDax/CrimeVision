import os
import csv
import math
import random
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for

app = Flask(__name__)
app.secret_key = 'crime-vision-secret-key-12345'

# Folder to store custom uploaded CSV files
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
DEFAULT_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'crime_data_default.csv')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global in-memory crime dataset list
CRIME_DATA = []
data_lock = threading.Lock()

def parse_datetime(dt_str):
    """Helper to parse datetime from CSV timestamp safely."""
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%m/%d/%Y %H:%M', '%Y-%m-%d'):
        try:
            return datetime.strptime(dt_str.strip(), fmt)
        except ValueError:
            continue
    # Fallback to current time if unparseable
    return datetime.now()

def load_data(filepath=None):
    """Loads CSV crime data into the global memory list."""
    global CRIME_DATA
    if not filepath:
        filepath = DEFAULT_DATA_PATH
    
    if not os.path.exists(filepath):
        with data_lock:
            CRIME_DATA = []
        return False
        
    loaded = []
    with data_lock:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    lat = float(row.get('latitude', 0.0))
                    lon = float(row.get('longitude', 0.0))
                    severity = int(row.get('severity', 1))
                    
                    # Skip invalid coordinate data
                    if lat == 0.0 or lon == 0.0:
                        continue
                    
                    dt = parse_datetime(row.get('timestamp', ''))
                    
                    loaded.append({
                        'id': row.get('id', f"CRM-{random.randint(10000, 99999)}"),
                        'timestamp': row.get('timestamp', ''),
                        'datetime': dt,
                        'hour': dt.hour,
                        'latitude': lat,
                        'longitude': lon,
                        'category': row.get('category', 'Theft').strip(),
                        'severity': severity,
                        'description': row.get('description', 'No details available.').strip()
                    })
                except (ValueError, TypeError):
                    continue
        CRIME_DATA = loaded
    return True

# Load default data on app startup
load_data()

def haversine_distance(p1, p2):
    """Computes real-world distance in km between two lat/lon coordinates."""
    lat1, lon1 = p1
    lat2, lon2 = p2
    R = 6371.0  # Earth's radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def flat_earth_distance(p1, p2):
    """
    Computes approximate flat-Earth distance in km.
    Extremely fast for local grid comparisons.
    """
    lat1, lon1 = p1
    lat2, lon2 = p2
    dlat = (lat2 - lat1) * 111.3
    dlon = (lon2 - lon1) * 111.3 * math.cos(math.radians((lat1 + lat2) / 2.0))
    return math.sqrt(dlat**2 + dlon**2)

def run_kmeans(points, k, max_iters=15):
    """
    Performs K-Means clustering on the points using optimized flat-Earth distance.
    Trains centroids on a sub-sample if the dataset is large, then assigns all points.
    """
    if not points:
        return [], []
    
    sample_size = 10000
    if len(points) > sample_size:
        training_points = random.sample(points, sample_size)
    else:
        training_points = points
        
    coords = [(p['latitude'], p['longitude']) for p in training_points]
    unique_coords = list(set(coords))
    
    actual_k = min(k, len(unique_coords))
    if actual_k <= 0:
        return [], []
    
    centroids = random.sample(unique_coords, actual_k)
    
    for _ in range(max_iters):
        clusters_indices = [[] for _ in range(actual_k)]
        for pt_idx, pt in enumerate(coords):
            dists = [flat_earth_distance(pt, centroid) for centroid in centroids]
            closest_idx = dists.index(min(dists))
            clusters_indices[closest_idx].append(pt_idx)
            
        new_centroids = []
        for c_idx, pt_indices in enumerate(clusters_indices):
            if not pt_indices:
                new_centroids.append(centroids[c_idx])
                continue
            
            avg_lat = sum(coords[idx][0] for idx in pt_indices) / len(pt_indices)
            avg_lon = sum(coords[idx][1] for idx in pt_indices) / len(pt_indices)
            new_centroids.append((avg_lat, avg_lon))
            
        converged = True
        for old, new in zip(centroids, new_centroids):
            if flat_earth_distance(old, new) > 0.0005:  # ~0.5 meters
                converged = False
                break
        if converged:
            break
        centroids = new_centroids
        
    # Re-group all points in the full dataset to their closest trained centroid
    clusters_points = [[] for _ in range(actual_k)]
    for p in points:
        pt = (p['latitude'], p['longitude'])
        dists = [flat_earth_distance(pt, centroid) for centroid in centroids]
        closest_idx = dists.index(min(dists))
        clusters_points[closest_idx].append(p)
            
    return centroids, clusters_points


def compute_knn_prediction(lat, lon, hour, k_neighbors=15):
    """
    Calculates crime risk level, dominant crime type, and recommendations
    using a spatio-temporal K-Nearest Neighbors approach.
    """
    if not CRIME_DATA:
        return {
            'risk_score': 0,
            'risk_level': 'Low',
            'predicted_category': 'None',
            'safety_recommendation': 'No historical crime records available for analysis.'
        }
        
    # Spatial Bounding-Box Indexing:
    # Filter global 1,000,000 database to a local +/- 0.4 degree square (~44km radius)
    lat_min, lat_max = lat - 0.4, lat + 0.4
    lon_min, lon_max = lon - 0.4, lon + 0.4
    
    candidates = [
        item for item in CRIME_DATA
        if lat_min <= item['latitude'] <= lat_max and lon_min <= item['longitude'] <= lon_max
    ]
    
    if not candidates:
        return {
            'risk_score': 0,
            'risk_level': 'Low',
            'predicted_category': 'Theft',
            'safety_recommendation': 'No crime records reported in the immediate region. Area is highly secure.',
            'nearest_incident_distance': 'N/A'
        }
        
    # Calculate weighted combined distance on local candidates only
    hour_scale = 0.2
    incidents_with_dist = []
    
    for item in candidates:
        geo_dist = haversine_distance((lat, lon), (item['latitude'], item['longitude']))
        h_diff = abs(hour - item['hour'])
        hour_dist = min(h_diff, 24 - h_diff)
        combined_dist = geo_dist + (hour_dist * hour_scale)
        incidents_with_dist.append((combined_dist, geo_dist, item))
        
    incidents_with_dist.sort(key=lambda x: x[0])
    neighbors = incidents_with_dist[:min(k_neighbors, len(incidents_with_dist))]
    
    # 1. Risk Score: based on average spatial distance of closest neighbors
    avg_spatial_dist = sum(n[1] for n in neighbors) / len(neighbors)
    avg_severity = sum(n[2]['severity'] for n in neighbors) / len(neighbors)
    
    max_d = 25.0
    risk_index = 100 * (1 - (min(avg_spatial_dist, max_d) / max_d))
    
    risk_score = int(risk_index * (0.3 + 0.7 * (avg_severity / 5.0)))
    risk_score = max(0, min(100, risk_score))
    
    if risk_score < 30:
        risk_level = 'Low'
    elif risk_score < 70:
        risk_level = 'Medium'
    else:
        risk_level = 'High'
        
    # 2. Predicted Category: standard mode selector (voting) of neighbors
    cat_votes = {}
    for n in neighbors:
        cat = n[2]['category']
        cat_votes[cat] = cat_votes.get(cat, 0) + 1
    predicted_category = max(cat_votes, key=cat_votes.get) if cat_votes else "Theft"
    
    # 3. Formulate safety guidelines
    recommendations = {
        'Theft': "Secure physical belongings. High concentration of mobile snatching and pickpocketing reported nearby around this hour.",
        'Assault': "Stay in populated areas. Avoid walking alone in poorly lit backstreets. Keep emergency contacts like 112 active.",
        'Burglary': "Ensure physical locks and security grills are secure. Residents should verify security patrol updates.",
        'Cyber Crime': "Never share OTPs, UPI pins, or scan unverified payment QRs. Be cautious of unsolicited calls offering banking updates.",
        'Harassment': "Eve-teasing or public nuisance reported nearby. Stay close to transit stations and use women's safety helpline 1091 if needed."
    }
    safety_recommendation = recommendations.get(predicted_category, "Observe local surroundings, travel via primary streets, and keep your phone accessible.")
    
    return {
        'risk_score': risk_score,
        'risk_level': risk_level,
        'predicted_category': predicted_category,
        'safety_recommendation': safety_recommendation,
        'nearest_incident_distance': f"{avg_spatial_dist:.2f} km"
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['GET'])
def analyze():
    # Number of clusters
    k = request.args.get('k', 5, type=int)
    category_filter = request.args.get('category', 'All')
    
    # Filter data if requested
    filtered_points = CRIME_DATA
    if category_filter != 'All':
        filtered_points = [p for p in CRIME_DATA if p['category'] == category_filter]
        
    if not filtered_points:
        return jsonify({
            'success': False,
            'message': 'No data points match the filter criteria.'
        })
        
    # Run custom K-Means clustering
    centroids, clusters_points = run_kmeans(filtered_points, k)
    
    # Compute metadata for each cluster
    clusters_info = []
    for idx, (lat, lon) in enumerate(centroids):
        c_points = clusters_points[idx]
        if not c_points:
            continue
            
        # Count category occurrences in this cluster
        cat_counts = {}
        for p in c_points:
            cat = p['category']
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        dominant_cat = max(cat_counts, key=cat_counts.get) if cat_counts else "Unknown"
        
        avg_severity = sum(p['severity'] for p in c_points) / len(c_points)
        
        clusters_info.append({
            'id': idx + 1,
            'latitude': lat,
            'longitude': lon,
            'size': len(c_points),
            'dominant_category': dominant_cat,
            'average_severity': round(avg_severity, 2),
            'density_percentage': round((len(c_points) / len(filtered_points)) * 100, 1)
        })
        
    # Sort hotspots by size descending
    clusters_info.sort(key=lambda x: x['size'], reverse=True)
    
    # Aggregate general statistics for charts
    categories_all = {}
    hours_all = [0] * 24
    severity_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    
    for p in filtered_points:
        cat = p['category']
        categories_all[cat] = categories_all.get(cat, 0) + 1
        hours_all[p['hour']] += 1
        severity_counts[p['severity']] = severity_counts.get(p['severity'], 0) + 1
        
    return jsonify({
        'success': True,
        'summary': {
            'total_incidents': len(filtered_points),
            'hotspots_detected': len(clusters_info),
            'category_counts': categories_all,
            'hourly_counts': hours_all,
            'severity_counts': severity_counts
        },
        'hotspots': clusters_info,
        'incidents': [{
            'latitude': p['latitude'],
            'longitude': p['longitude'],
            'category': p['category'],
            'severity': p['severity'],
            'timestamp': p['timestamp'],
            'description': p['description']
        } for p in filtered_points[:400]] # Limit displayed map pins for performance
    })

@app.route('/api/predict', methods=['GET'])
def predict():
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        hour = int(request.args.get('hour', 12))
        
        prediction = compute_knn_prediction(lat, lon, hour)
        return jsonify({
            'success': True,
            'prediction': prediction
        })
    except (ValueError, TypeError):
        return jsonify({
            'success': False,
            'message': 'Invalid coordinates or parameters supplied.'
        })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Empty file selected'}), 400
        
    if file and file.filename.endswith('.csv'):
        filename = "user_uploaded_crime_data.csv"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Try loading data and fall back on failure
        success = load_data(filepath)
        if success and len(CRIME_DATA) > 0:
            return jsonify({
                'success': True,
                'message': f'Dataset uploaded successfully! Loaded {len(CRIME_DATA)} crime incidents.',
                'records_count': len(CRIME_DATA)
            })
        else:
            # Revert to default
            load_data()
            return jsonify({
                'success': False,
                'message': 'Failed to parse CSV. Ensure it has correct headers: timestamp, latitude, longitude, category, severity.'
            }), 400
            
    return jsonify({'success': False, 'message': 'Only CSV files are supported.'}), 400
LATEST_STREAMED_CRIMES = []

@app.route('/api/reset', methods=['POST'])
def reset_data():
    load_data()
    return jsonify({
        'success': True,
        'message': f'Reset to default dataset. Loaded {len(CRIME_DATA)} incidents.',
        'records_count': len(CRIME_DATA)
    })

@app.route('/api/register-fir', methods=['POST'])
def register_fir():
    global LATEST_STREAMED_CRIMES
    try:
        data = request.json
        crime_id = data.get('id')
        timestamp = data.get('timestamp')
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        category = data.get('category')
        severity = int(data.get('severity'))
        desc = data.get('description')
        
        item = {
            'id': crime_id,
            'timestamp': timestamp,
            'datetime': parse_datetime(timestamp),
            'hour': parse_datetime(timestamp).hour,
            'latitude': lat,
            'longitude': lon,
            'category': category,
            'severity': severity,
            'description': desc
        }
        
        with data_lock:
            CRIME_DATA.append(item)
            LATEST_STREAMED_CRIMES.append({
                'id': item['id'],
                'latitude': item['latitude'],
                'longitude': item['longitude'],
                'category': item['category'],
                'severity': item['severity'],
                'timestamp': item['timestamp'],
                'description': item['description']
            })
            
            # Limit memory footprint
            if len(CRIME_DATA) > 1100000:
                CRIME_DATA.pop(0)
            if len(LATEST_STREAMED_CRIMES) > 50:
                LATEST_STREAMED_CRIMES.pop(0)
                
        return jsonify({'success': True, 'message': 'FIR synced successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/stream-update', methods=['GET'])
def stream_update():
    global LATEST_STREAMED_CRIMES
    with data_lock:
        new_crimes = list(LATEST_STREAMED_CRIMES)
        LATEST_STREAMED_CRIMES.clear()
        
    return jsonify({
        'success': True,
        'new_records_count': len(new_crimes),
        'new_crimes': new_crimes,
        'total_records_count': len(CRIME_DATA)
    })




if __name__ == '__main__':
    app.run(debug=True, port=5000)
