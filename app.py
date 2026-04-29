from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime  

# 🟢 1. App Initialization (Sirf EK baar)
app = Flask(__name__)
CORS(app)

# ==========================================
# 🔐 DATABASE CONNECTION (XAMPP MySQL)
# ==========================================
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="127.0.0.1", 
            user="root",
            password="",
            database="orbitx_db"
        )
        return conn
    except mysql.connector.Error as err:
        print(f"❌ DB Connection Failed: {err}")
        return None

# ==========================================
# 🌌 EXOPLANET DATABASE ENGINE
# ==========================================
exoplanet_db = []

def load_exoplanet_data():
    global exoplanet_db
    print("Fetching massive Exoplanet Data from NASA... Please wait.")
    try:
        url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+pl_name,sy_dist,pl_rade,disc_year+from+ps+where+default_flag=1&format=json"        
        response = requests.get(url, timeout=15)
        response.raise_for_status() 
        raw_data = response.json()
        
        for planet in raw_data:
            if planet.get('sy_dist') is not None and planet.get('pl_rade') is not None:
                exoplanet_db.append({
                    "name": planet['pl_name'],
                    "distance_ly": round(planet['sy_dist'] * 3.262, 2),
                    "radius_earth": round(planet['pl_rade'], 2),
                    "year": planet.get('disc_year', 'Unknown') 
                })
        print(f"✅ Success! {len(exoplanet_db)} Exoplanets loaded from NASA.")
        
    except Exception as e:
        print(f"❌ NASA API Failed: {e}")
        print("⚠️ Loading OrbitX Offline Backup Database...")
        exoplanet_db.extend([
            {"name": "Proxima Centauri b", "distance_ly": 4.24, "radius_earth": 1.03, "year": 2016},
            {"name": "TRAPPIST-1 e", "distance_ly": 39.46, "radius_earth": 0.92, "year": 2017},
            {"name": "Kepler-452 b", "distance_ly": 1799.0, "radius_earth": 1.63, "year": 2015}
        ])

load_exoplanet_data()

# ==========================================
# ☄️ NEO (NEAR-EARTH OBJECT) RADAR ENGINE 
# ==========================================
@app.route('/api/neo')
def get_neo():
    today = datetime.today().strftime('%Y-%m-%d')
    url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={today}&end_date={today}&api_key=DEMO_KEY"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        asteroids = []
        if 'near_earth_objects' in data:
            for obj in data['near_earth_objects'][today]:
                asteroids.append({
                    'name': obj['name'],
                    'hazardous': obj['is_potentially_hazardous_asteroid'],
                    'size_meters': round(obj['estimated_diameter']['meters']['estimated_diameter_max'], 2),
                    'speed_kmh': round(float(obj['close_approach_data'][0]['relative_velocity']['kilometers_per_hour']), 2),
                    'miss_distance_km': round(float(obj['close_approach_data'][0]['miss_distance']['kilometers']), 2)
                })
        
        asteroids = sorted(asteroids, key=lambda x: x['hazardous'], reverse=True)
        return jsonify({"status": "success", "data": asteroids})

    except Exception as e:
        print(f"Error fetching NEO data: {e}")
        return jsonify({"status": "error", "message": "Failed to decrypt NASA transmission."})

@app.route('/api/solar_weather')
def get_solar_weather():
    # Pichle 30 din ka data fetch karenge kyunki CME roz nahi aate
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    url = f"https://api.nasa.gov/DONKI/CME?startDate={start_date}&endDate={end_date}&api_key=DEMO_KEY"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        cme_events = []
        # Check if data is a list (API returns list of events)
        if isinstance(data, list):
            # Sirf latest 5 events uthayenge
            for obj in data[-5:]:
                cme_events.append({
                    'activityID': obj.get('activityID', 'UNKNOWN_ID'),
                    'startTime': obj.get('startTime', 'UNKNOWN_TIME').replace('T', ' | HOUR: '),
                    'note': obj.get('note', 'No detailed transmission available.')[:150] + '...', # Shorten the text
                    'instruments': [inst['displayName'] for inst in obj.get('instruments', [{'displayName': 'UNKNOWN'}])]
                })
        
        # Latest event sabse upar dikhane ke liye reverse kiya
        cme_events = cme_events[::-1]
        return jsonify({"status": "success", "data": cme_events})

    except Exception as e:
        print(f"Error fetching DONKI data: {e}")
        return jsonify({"status": "error", "message": "Failed to intercept Solar Telemetry. Shields status unknown."})

# ==========================================
# 🛡️ AUTHENTICATION ROUTES (UPDATED)
# ==========================================
@app.route('/')
def home():
    return "<h1>🚀 OrbitX Backend Engine is LIVE and Running!</h1>"

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    q1 = data.get('q1')
    q2 = data.get('q2')
    q3 = data.get('q3')
    
    if not all([username, email, password, q1, q2, q3]):
        return jsonify({"status": "error", "message": "All fields including security coordinates are required!"})

    conn = get_db_connection()
    if not conn: return jsonify({"status": "error", "message": "Database server down!"})
    
    try:
        cursor = conn.cursor()
        hashed_pw = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, q1_constellation, q2_mission, q3_nebula) VALUES (%s, %s, %s, %s, %s, %s)", 
            (username, email, hashed_pw, q1.lower(), q2.lower(), q3.lower())
        )
        conn.commit()
        return jsonify({"status": "success", "message": "Agent registered with Tactical Override enabled."})
    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": "Username/Email already exists!"})
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email, password = data.get('email'), data.get('password')
    
    conn = get_db_connection()
    if not conn: return jsonify({"status": "error", "message": "Database server down!"})
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            return jsonify({"status": "success", "username": user['username'], "message": "Welcome back!"})
        return jsonify({"status": "error", "message": "Invalid Email or Password!"})
    finally:
        conn.close()

@app.route('/api/reset_password', methods=['POST'])
def reset_password():
    data = request.json
    email = data.get('email')
    new_password = data.get('new_password')
    q1 = data.get('q1').lower() if data.get('q1') else ''
    q2 = data.get('q2').lower() if data.get('q2') else ''
    q3 = data.get('q3').lower() if data.get('q3') else ''

    if not all([email, new_password, q1, q2, q3]):
        return jsonify({"status": "error", "message": "All coordinates are required for Tactical Override!"})

    conn = get_db_connection()
    if not conn: return jsonify({"status": "error", "message": "Database server down!"})
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s AND q1_constellation = %s AND q2_mission = %s AND q3_nebula = %s", 
                       (email, q1, q2, q3))
        user = cursor.fetchone()
        
        if user:
            hashed_pw = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password_hash = %s WHERE email = %s", (hashed_pw, email))
            conn.commit()
            return jsonify({"status": "success", "message": "Override Successful. Password Decrypted and Updated."})
        else:
            return jsonify({"status": "error", "message": "TACTICAL OVERRIDE FAILED. Incorrect Coordinates."})
    finally:
        conn.close()

# ==========================================
# 🔭 OTHER UTILITY ROUTES
# ==========================================

@app.route('/api/exoplanets')
def filter_exoplanets():
    max_distance = float(request.args.get('max_dist', 10000))
    max_size = float(request.args.get('max_size', 100))
    filtered = [p for p in exoplanet_db if p['distance_ly'] <= max_distance and p['radius_earth'] <= max_size]
    return jsonify({"status": "success", "total_matches": len(filtered), "data": sorted(filtered, key=lambda x: x['distance_ly'])[:50]})

@app.route('/api/iss-location')
def get_iss_location():
    try:
        data = requests.get("http://api.open-notify.org/iss-now.json").json()
        return jsonify({"status": "success", "latitude": data['iss_position']['latitude'], "longitude": data['iss_position']['longitude']})
    except:
        return jsonify({"status": "error"})
    
@app.route('/api/iss-predict')
def predict_iss_location():
    try:
        target_time = request.args.get('timestamp')
        if not target_time:
            return jsonify({"status": "error", "message": "Time nahi mila bhai!"})
        
        url = f"https://api.wheretheiss.at/v1/satellites/25544/positions?timestamps={target_time}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        return jsonify({
            "status": "success",
            "latitude": data[0]['latitude'],
            "longitude": data[0]['longitude'],
            "timestamp": target_time
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# ==========================================
# ⭐ BOOKMARK (FAVORITES) ROUTES
# ==========================================

@app.route('/api/save_bookmark', methods=['POST'])
def save_bookmark():
    data = request.json
    username = data.get('username')
    planet_name = data.get('planet_name')

    if not username or not planet_name:
        return jsonify({"status": "error", "message": "Missing data!"})

    conn = get_db_connection()
    if not conn: return jsonify({"status": "error", "message": "Database server down!"})
    
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO bookmarks (username, planet_name) VALUES (%s, %s)", (username, planet_name))
        conn.commit()
        return jsonify({"status": "success", "message": f"{planet_name} added to your Universe!"})
    except mysql.connector.IntegrityError:
        return jsonify({"status": "error", "message": "Already saved in your Universe!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        conn.close()

@app.route('/api/my_bookmarks', methods=['POST'])
def my_bookmarks():
    data = request.json
    username = data.get('username')

    conn = get_db_connection()
    if not conn: return jsonify({"status": "error", "message": "Database server down!"})
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT planet_name FROM bookmarks WHERE username = %s", (username,))
        saved_planets = cursor.fetchall()
        
        planet_names = [p['planet_name'] for p in saved_planets]
        return jsonify({"status": "success", "data": planet_names})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        conn.close()

# ==========================================
# 🕵️‍♂️ CLASSIFIED FILES ROUTE
# ==========================================
@app.route('/api/classified')
def get_classified_files():
    secret_files = [
        {
            "id": "wow-signal",
            "title": "INCIDENT 1977: THE WOW! SIGNAL",
            "status": "UNSOLVED",
            "statusClass": "status-yellow",
            "date": "August 15, 1977",
            "origin": "Sagittarius Constellation",
            "content": """
                <p>On August 15, 1977, the Big Ear radio telescope intercepted a strong narrowband radio signal...</p>
                <p>Current Status: We are still listening. Something is out there.</p>
            """
        },
        {
            "id": "oumuamua",
            "title": "OBJECT: 'OUMUAMUA",
            "status": "CLASSIFIED",
            "statusClass": "status-red",
            "date": "October 19, 2017",
            "origin": "Interstellar Space (Vega)",
            "content": """
                <p>The first interstellar object detected passing through our Solar System. Officially classified as a comet, but its behavior defies known astrophysics.</p>
            """
        },
        {
            "id": "great-attractor",
            "title": "ANOMALY: THE GREAT ATTRACTOR",
            "status": "CRITICAL",
            "statusClass": "status-red",
            "date": "Ongoing",
            "origin": "Zone of Avoidance",
            "content": """
                <p>Our Milky Way galaxy is moving at 600 kilometers per second towards a massive, unseen region of space known as The Great Attractor.</p>
            """
        }
    ]
    return jsonify({"status": "success", "data": secret_files})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
