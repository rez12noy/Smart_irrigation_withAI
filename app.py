from flask import Flask, request,render_template, jsonify, send_from_directory, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import datetime
import sqlite3
import time
import os

app = Flask(__name__)
app.secret_key = 'rez101' 
CORS(app)

# Initialize database
def init_db():
    conn = sqlite3.connect('irrigation.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sensor_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp DATETIME,
                  voltage REAL,
                  water_need REAL,
                  pump_active INTEGER,
                  month INTEGER,
                  crop_type INTEGER,
                  watering_time REAL DEFAULT 0.0)''')
    
    # Create user table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL)''')
    
    conn.commit()
    conn.close()

init_db()

# Crop mapping
crops = {
    0: "Apple", 1: "Banana", 2: "Blackgram", 3: "Chickpea", 4: "Coconut",
    5: "Coffee", 6: "Cotton", 7: "Grapes", 8: "Jute", 9: "Kidneybeans",
    10: "Lentil", 11: "Maize", 12: "Mango", 13: "Mothbeans", 14: "Mungbean",
    15: "Muskmelon", 16: "Orange", 17: "Papaya", 18: "Pigeonpeas",
    19: "Pomegranate", 20: "Rice", 21: "Watermelon"
}

# System state
current_system_crop = 0
last_crop_update = 0

# Delhi weather data
delhi_temperature = [14.4, 17.71, 23.31, 29.26, 32.8, 32.3, 30.5, 29.3, 29.0, 26.1, 20.1, 15.3]
delhi_rainfall = [19.19, 17.68, 13.25, 9.56, 15.92, 56.01, 180.09, 229.14, 105.22, 24.82, 8.39, 8.23]
delhi_humidity = [52, 45, 38, 28, 30, 43, 66, 75, 69, 55, 55, 58]

@app.route('/')
def index():
    if 'user' not in session:
        return redirect('/auth')  # Not logged in → redirect to login page
    return render_template('dashboard.html')


@app.route('/auth')
def auth_page():
    return send_from_directory('templates', 'auth.html')


@app.route('/data', methods=['POST'])
def handle_data():
    global current_system_crop, last_crop_update
    try:
        # Debug: Print raw request data
        print(f"\nRaw request data: {request.data}")
        
        data = request.get_json()
        if not data:
            print("Error: No JSON data received")
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Debug: Print received JSON
        print(f"Parsed JSON data: {data}")
        
        # Validate required fields
        required_fields = ['voltage', 'water_need', 'pump_active', 'month', 'crop_type']
        for field in required_fields:
            if field not in data:
                print(f"Error: Missing required field {field}")
                return jsonify({"status": "error", "message": f"Missing field: {field}"}), 400

        # Process data
        watering_time = data.get('watering_time', 0.0)
        
        # Debug: Print before DB operation
        print("Attempting database insert...")
        
        try:
            conn = sqlite3.connect('irrigation.db', timeout=10)
            c = conn.cursor()
            
            # Debug: Verify table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sensor_data'")
            if not c.fetchone():
                print("Error: sensor_data table doesn't exist")
                return jsonify({"status": "error", "message": "Database table not found"}), 500
            
            c.execute('''INSERT INTO sensor_data 
                        (timestamp, voltage, water_need, pump_active, month, crop_type, watering_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (datetime.now().isoformat(),  # Store as ISO format string
                      float(data['voltage']),
                      float(data['water_need']),
                      bool(data['pump_active']),
                      int(data['month']),
                      int(data['crop_type']),
                      float(watering_time)))
            
            conn.commit()
            print("Database insert successful")
            
            response = {
                "status": "success",
                "message": f"SETTINGS:{current_system_crop}",
                "current_crop": current_system_crop
            }
            return jsonify(response)
            
        except sqlite3.Error as e:
            print(f"Database error: {str(e)}")
            return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

@app.route('/settings', methods=['GET', 'POST'])
def handle_settings():
    global current_system_crop, last_crop_update
    
    if request.method == 'POST':
        try:
            data = request.json
            if 'crop' not in data:
                return jsonify({"status": "error", "message": "Missing crop parameter"}), 400
                
            crop_id = int(data['crop'])
            if crop_id not in crops:
                return jsonify({"status": "error", "message": "Invalid crop ID"}), 400
                
            current_system_crop = crop_id
            last_crop_update = time.time()
            
            return jsonify({
                "status": "success",
                "message": f"SETTINGS:{current_system_crop}",
                "current_crop": current_system_crop,
                "crop_name": crops[current_system_crop]
            })
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    
    return jsonify({
        "current_crop": current_system_crop,
        "crop_name": crops.get(current_system_crop, "Unknown"),
        "available_crops": crops
    })

@app.route('/current', methods=['GET'])
def get_current():
    conn = sqlite3.connect('irrigation.db', timeout=10)
    c = conn.cursor()
    c.execute('''SELECT timestamp, voltage, water_need, pump_active, month, crop_type, watering_time
                 FROM sensor_data 
                 WHERE crop_type = ? 
                 ORDER BY timestamp DESC LIMIT 1''', 
              (current_system_crop,))
    row = c.fetchone()
    conn.close()

    month_idx = 0
    if row:
        month_idx = (row[4] - 1) % 12

    return jsonify({
        "timestamp": row[0] if row else None,
        "voltage": row[1] if row else None,
        "water_need": row[2] if row else None,
        "pump_active": bool(row[3]) if row else None,
        "month": row[4] if row else datetime.now().month,
        "crop_type": row[5] if row else current_system_crop,
        "watering_time": row[6] if row else 0.0,
        "current_crop": current_system_crop,
        "weather": {
            "temperature": delhi_temperature[month_idx],
            "rainfall": delhi_rainfall[month_idx],
            "humidity": delhi_humidity[month_idx]
        }
    })

@app.route('/history', methods=['GET'])
def get_history():
    conn = sqlite3.connect('irrigation.db', timeout=10)
    c = conn.cursor()
    c.execute('''SELECT timestamp, voltage, water_need, pump_active, month, crop_type, watering_time
                 FROM sensor_data ORDER BY timestamp DESC LIMIT 50''')
    rows = c.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "timestamp": row[0],
            "voltage": row[1],
            "water_need": row[2],
            "pump_active": bool(row[3]),
            "month": row[4],
            "crop_type": crops.get(row[5], "Unknown"),
            "watering_time": row[6]
        })
    
    return jsonify(history)


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email and password required'}), 400

    hashed_password = generate_password_hash(password)
    try:
        conn = sqlite3.connect('irrigation.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, hashed_password))
        conn.commit()
        return jsonify({'status': 'success', 'message': 'User registered successfully'})
    except sqlite3.IntegrityError:
        return jsonify({'status': 'error', 'message': 'Email already exists'}), 409
    finally:
        conn.close()


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    conn = sqlite3.connect('irrigation.db')
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE email = ?', (email,))
    row = c.fetchone()
    conn.close()

    if row and check_password_hash(row[0], password):
        session['user'] = email
        return jsonify({'status': 'success', 'message': 'Logged in successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return redirect('/auth')


@app.route('/check-auth', methods=['GET'])
def check_auth():
    if 'user' in session:
        return jsonify({'authenticated': True, 'user': session['user']})
    else:
        return jsonify({'authenticated': False})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)