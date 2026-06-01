import os
import csv
import time
import json
import random
import urllib.request
from datetime import datetime

def generate_crime_incident():
    categories = ["Theft", "Assault", "Burglary", "Cyber Crime", "Harassment"]
    severities = {
        "Theft": 2,
        "Assault": 4,
        "Burglary": 3,
        "Cyber Crime": 3,
        "Harassment": 2
    }
    descriptions = {
        "Theft": [
            "Mobile phone snatching from public transit", 
            "Bicycle/Two-wheeler lifting from parking lot", 
            "Pickpocketing reported in crowded railway station", 
            "Luggage theft from long-distance train compartment",
            "Shop lifting from retail marketplace",
            "Pickpocketing near historical monument/tourist site"
        ],
        "Assault": [
            "Road rage altercation leading to simple assault", 
            "Scuffle over land or property dispute", 
            "Physical altercation outside drinking establishment", 
            "Neighbor clash over shared resources",
            "Aggravated physical brawl in commercial area"
        ],
        "Burglary": [
            "Housebreaking during daytime locks", 
            "Forced entry and burglary at locked retail shop", 
            "Office laptops and hardware stolen overnight", 
            "Burglary in residential society apartment",
            "Nighttime intrusion and theft in jewelry store"
        ],
        "Cyber Crime": [
            "UPI transaction fraud using cloned QR codes", 
            "OTP phishing scam claiming bank account block", 
            "Identity theft and credit card cloning transaction", 
            "Work-from-home job scam involving digital payment",
            "Phishing email targeting financial credentials"
        ],
        "Harassment": [
            "Eve-teasing incident reported near educational institute", 
            "Stalking complaint on public transit corridor", 
            "Verbal harassment and public nuisance at market", 
            "Inappropriate behavior on local train/bus route",
            "Obscene calls and digital stalking report",
            "Tourist guide solicitation escalating to harassment"
        ]
    }
    
    # Combined index with 22 metros and 9 key rural / tourist zones
    # Structure: (District Name, State, Lat, Lon, Weight, Crime Likelihood Ratios, Bounding Box Key)
    india_regions = [
        # --- Metropolitan Regions (Urban) ---
        ("Delhi Central", "Delhi", 28.6139, 77.2090, 0.14, {"Theft": 0.45, "Assault": 0.15, "Burglary": 0.10, "Cyber Crime": 0.15, "Harassment": 0.15}, False),
        ("Lucknow", "Uttar Pradesh", 26.8467, 80.9462, 0.07, {"Theft": 0.30, "Assault": 0.25, "Burglary": 0.25, "Cyber Crime": 0.10, "Harassment": 0.10}, False),
        ("Patna", "Bihar", 25.5941, 85.1376, 0.06, {"Theft": 0.20, "Assault": 0.35, "Burglary": 0.30, "Cyber Crime": 0.05, "Harassment": 0.10}, False),
        ("Jaipur", "Rajasthan", 26.9124, 75.7873, 0.05, {"Theft": 0.35, "Assault": 0.25, "Burglary": 0.15, "Cyber Crime": 0.10, "Harassment": 0.15}, False),
        ("Chandigarh", "Chandigarh", 30.7333, 76.7794, 0.02, {"Theft": 0.40, "Assault": 0.15, "Burglary": 0.15, "Cyber Crime": 0.20, "Harassment": 0.10}, False),
        ("Srinagar", "Jammu & Kashmir", 34.0837, 74.7973, 0.015, {"Theft": 0.25, "Assault": 0.40, "Burglary": 0.15, "Cyber Crime": 0.05, "Harassment": 0.15}, False),
        ("Dehradun", "Uttarakhand", 30.3165, 78.0322, 0.015, {"Theft": 0.30, "Assault": 0.20, "Burglary": 0.30, "Cyber Crime": 0.10, "Harassment": 0.10}, False),
        
        ("Mumbai City", "Maharashtra", 19.0760, 72.8777, 0.11, {"Theft": 0.40, "Assault": 0.20, "Burglary": 0.15, "Cyber Crime": 0.15, "Harassment": 0.10}, "mumbai"),
        ("Pune", "Maharashtra", 18.5204, 73.8567, 0.05, {"Theft": 0.30, "Assault": 0.15, "Burglary": 0.15, "Cyber Crime": 0.25, "Harassment": 0.15}, False),
        ("Ahmedabad", "Gujarat", 23.0225, 72.5714, 0.04, {"Theft": 0.45, "Assault": 0.15, "Burglary": 0.25, "Cyber Crime": 0.10, "Harassment": 0.05}, False),
        ("Goa North", "Goa", 15.4909, 73.8278, 0.01, {"Theft": 0.40, "Assault": 0.15, "Burglary": 0.20, "Cyber Crime": 0.10, "Harassment": 0.15}, "goa"),
        
        ("Bengaluru Urban", "Karnataka", 12.9716, 77.5946, 0.10, {"Theft": 0.25, "Assault": 0.15, "Burglary": 0.15, "Cyber Crime": 0.30, "Harassment": 0.15}, False),
        ("Chennai", "Tamil Nadu", 13.0827, 80.2707, 0.06, {"Theft": 0.40, "Assault": 0.25, "Burglary": 0.15, "Cyber Crime": 0.10, "Harassment": 0.10}, "chennai"),
        ("Hyderabad", "Telangana", 17.3850, 78.4867, 0.06, {"Theft": 0.30, "Assault": 0.15, "Burglary": 0.15, "Cyber Crime": 0.25, "Harassment": 0.15}, False),
        ("Kochi", "Kerala", 9.9312, 76.2673, 0.02, {"Theft": 0.25, "Assault": 0.20, "Burglary": 0.15, "Cyber Crime": 0.15, "Harassment": 0.25}, "kochi"),
        ("Visakhapatnam", "Andhra Pradesh", 17.6868, 83.2185, 0.02, {"Theft": 0.35, "Assault": 0.25, "Burglary": 0.20, "Cyber Crime": 0.10, "Harassment": 0.10}, False),
        
        ("Kolkata", "West Bengal", 22.5726, 88.3639, 0.05, {"Theft": 0.35, "Assault": 0.20, "Burglary": 0.10, "Cyber Crime": 0.15, "Harassment": 0.20}, False),
        ("Ranchi", "Jharkhand", 23.3441, 85.3096, 0.02, {"Theft": 0.25, "Assault": 0.35, "Burglary": 0.25, "Cyber Crime": 0.05, "Harassment": 0.10}, False),
        ("Bhubaneswar", "Odisha", 20.2961, 85.8245, 0.02, {"Theft": 0.30, "Assault": 0.25, "Burglary": 0.25, "Cyber Crime": 0.10, "Harassment": 0.10}, False),
        ("Guwahati", "Assam", 26.1158, 91.7086, 0.02, {"Theft": 0.35, "Assault": 0.25, "Burglary": 0.20, "Cyber Crime": 0.05, "Harassment": 0.15}, False),
        
        ("Bhopal", "Madhya Pradesh", 23.2599, 77.4126, 0.03, {"Theft": 0.35, "Assault": 0.25, "Burglary": 0.20, "Cyber Crime": 0.10, "Harassment": 0.10}, False),
        ("Raipur", "Chhattisgarh", 21.2514, 81.6296, 0.02, {"Theft": 0.30, "Assault": 0.30, "Burglary": 0.25, "Cyber Crime": 0.05, "Harassment": 0.10}, False),
        
        # --- Rural & Tourist Regions ---
        ("Manali Tourism Hub", "Himachal Pradesh", 32.2396, 77.1887, 0.015, {"Theft": 0.45, "Assault": 0.10, "Burglary": 0.10, "Cyber Crime": 0.05, "Harassment": 0.30}, False),
        ("Jaisalmer Desert Frontier", "Rajasthan", 26.9157, 70.9083, 0.015, {"Theft": 0.50, "Assault": 0.10, "Burglary": 0.10, "Cyber Crime": 0.05, "Harassment": 0.25}, False),
        ("Hampi Ruins", "Karnataka", 15.3350, 76.4600, 0.01, {"Theft": 0.55, "Assault": 0.10, "Burglary": 0.10, "Cyber Crime": 0.05, "Harassment": 0.20}, False),
        ("Munnar Tea Estates", "Kerala", 10.0889, 77.0595, 0.01, {"Theft": 0.45, "Assault": 0.15, "Burglary": 0.15, "Cyber Crime": 0.05, "Harassment": 0.20}, False),
        ("Rishikesh Sanctuary", "Uttarakhand", 30.0869, 78.2676, 0.015, {"Theft": 0.45, "Assault": 0.10, "Burglary": 0.10, "Cyber Crime": 0.05, "Harassment": 0.30}, False),
        ("Darjeeling Tea Highlands", "West Bengal", 27.0410, 88.2627, 0.01, {"Theft": 0.50, "Assault": 0.10, "Burglary": 0.15, "Cyber Crime": 0.05, "Harassment": 0.20}, False),
        ("Palolem Beach (South Goa)", "Goa", 15.0100, 74.0200, 0.015, {"Theft": 0.45, "Assault": 0.15, "Burglary": 0.10, "Cyber Crime": 0.05, "Harassment": 0.25}, "goa_south"),
        ("Alleppey Backwaters", "Kerala", 9.4981, 76.3388, 0.01, {"Theft": 0.50, "Assault": 0.15, "Burglary": 0.10, "Cyber Crime": 0.05, "Harassment": 0.20}, "alleppey"),
        ("Khajuraho Heritage Site", "Madhya Pradesh", 24.8318, 79.9199, 0.01, {"Theft": 0.50, "Assault": 0.10, "Burglary": 0.10, "Cyber Crime": 0.05, "Harassment": 0.25}, False)
    ]
    
    weights = [r[4] for r in india_regions]
    region = random.choices(india_regions, weights=weights)[0]
    dist_name, state, base_lat, base_lon, _, crime_ratios, constraint_key = region
    
    category = random.choices(list(crime_ratios.keys()), weights=list(crime_ratios.values()))[0]
    
    # Generate coordinates with land-locking boundaries
    while True:
        lat = random.gauss(base_lat, 0.12)
        lon = random.gauss(base_lon, 0.12)
        
        if constraint_key == "mumbai":
            if 18.90 <= lat <= 19.28 and 72.81 <= lon <= 72.94:
                break
        elif constraint_key == "chennai":
            if 12.92 <= lat <= 13.20 and 80.12 <= lon <= 80.29:
                break
        elif constraint_key == "kochi":
            if 9.85 <= lat <= 10.08 and 76.222 <= lon <= 76.35:
                break
        elif constraint_key == "goa":
            if 15.35 <= lat <= 15.65 and 73.79 <= lon <= 74.05:
                break
        elif constraint_key == "goa_south":
            if 14.95 <= lat <= 15.15 and 73.95 <= lon <= 74.15:
                break
        elif constraint_key == "alleppey":
            if 9.40 <= lat <= 9.60 and 76.30 <= lon <= 76.45:
                break
        else:
            break
            
    severity = severities[category]
    severity = max(1, min(5, severity + random.choice([-1, 0, 1])))
    
    desc_template = random.choice(descriptions[category])
    is_tourist = any(kw in dist_name for kw in ["Tourism", "Ruins", "Beach", "Backwaters", "Heritage", "Estates", "Highlands", "Sanctuary", "Frontier"])
    
    if is_tourist:
        description = f"TOURIST ADVISORY: {desc_template} reported near {dist_name}, {state}"
    else:
        description = f"{desc_template} in {dist_name}, {state}"
        
    crime_id = f"CCTNS-BOT-{random.randint(1000000, 9999999)}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return {
        'id': crime_id,
        'timestamp': timestamp,
        'latitude': round(lat, 6),
        'longitude': round(lon, 6),
        'category': category,
        'severity': severity,
        'description': description
    }

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'data', 'crime_data_default.csv')
    server_url = "http://127.0.0.1:5000/api/register-fir"
    
    print("=" * 60)
    print("      CCTNS LIVE STREAM COLLECTOR BACKGROUND BOT")
    print("=" * 60)
    print(f"Target CSV dataset: {csv_path}")
    print(f"Target Flask server API: {server_url}")
    print("Bot is starting up... Press Ctrl+C to terminate.")
    print("-" * 60)
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    while True:
        try:
            # Generate random interval 15 - 20 seconds
            sleep_time = random.uniform(15.0, 20.0)
            time.sleep(sleep_time)
            
            # Generate new record
            incident = generate_crime_incident()
            
            # 1. Append to CSV file on disk
            try:
                file_exists = os.path.exists(csv_path)
                with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(["id", "timestamp", "latitude", "longitude", "category", "severity", "description"])
                    writer.writerow([
                        incident['id'],
                        incident['timestamp'],
                        f"{incident['latitude']:.6f}",
                        f"{incident['longitude']:.6f}",
                        incident['category'],
                        incident['severity'],
                        incident['description']
                    ])
                disk_status = "Saved to CSV"
            except Exception as e:
                disk_status = f"Disk Error ({e})"
                
            # 2. Post webhook notification to Flask API
            api_status = "Not Connected"
            try:
                payload = json.dumps(incident).encode('utf-8')
                req = urllib.request.Request(
                    server_url,
                    data=payload,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    if res_data.get('success'):
                        api_status = "Synced to UI"
                    else:
                        api_status = f"API Refused ({res_data.get('message')})"
            except urllib.error.URLError as e:
                api_status = f"Server Offline ({e.reason})"
            except Exception as e:
                api_status = f"API Error ({e})"
                
            # Log action
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {incident['id']} | "
                  f"{incident['category']} in {incident['description'].split('near ')[-1] if 'near ' in incident['description'] else incident['description'].split('in ')[-1]} | "
                  f"Disk: {disk_status} | API: {api_status}")
                  
        except KeyboardInterrupt:
            print("\nCollector bot stopped by user.")
            break
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Unexpected error: {e}")

if __name__ == "__main__":
    main()
