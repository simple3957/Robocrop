from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import requests
import firebase_admin
from firebase_admin import credentials, db
import os
from datetime import datetime, time
import logging
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import joblib

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)

# ThingSpeak configuration
THINGSPEAK_API_KEY = "82MUA3YL0JJ2OV0Z"
THINGSPEAK_CHANNEL_ID = "2575559"

# Firebase configuration
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://mgit1-5b90d-default-rtdb.asia-southeast1.firebasedatabase.app'
})

# Global variable to track manual override
manual_override = False

def get_recommendations(soil_moisture, temperature, humidity):
    """Generate detailed recommendations based on sensor values"""
    recommendations = []
    
    # Soil moisture recommendations
    if soil_moisture < 200:
        recommendations.append({
            'type': 'warning',
            'message': 'Soil moisture is very low. Immediate irrigation recommended.',
            'action': 'Start irrigation system'
        })
    elif soil_moisture < 300:
        recommendations.append({
            'type': 'info',
            'message': 'Soil moisture is below optimal level.',
            'action': 'Consider irrigation'
        })
    elif soil_moisture > 400:
        recommendations.append({
            'type': 'warning',
            'message': 'Soil moisture is very high. Risk of overwatering.',
            'action': 'Stop irrigation if active'
        })
    else:
        recommendations.append({
            'type': 'success',
            'message': 'Soil moisture is at optimal level.',
            'action': 'No action needed'
        })
    
    # Temperature recommendations
    if temperature > 30:
        recommendations.append({
            'type': 'warning',
            'message': 'High temperature detected. Increased water evaporation.',
            'action': 'Monitor soil moisture closely'
        })
    elif temperature < 15:
        recommendations.append({
            'type': 'info',
            'message': 'Low temperature detected. Reduced water evaporation.',
            'action': 'Reduce irrigation frequency'
        })
    
    # Humidity recommendations
    if humidity > 80:
        recommendations.append({
            'type': 'info',
            'message': 'High humidity detected. Reduced water evaporation.',
            'action': 'Consider reducing irrigation duration'
        })
    elif humidity < 40:
        recommendations.append({
            'type': 'warning',
            'message': 'Low humidity detected. Increased water evaporation.',
            'action': 'Monitor soil moisture closely'
        })
    
    # Overall recommendation
    if soil_moisture < 300 and temperature > 25 and humidity < 50:
        recommendations.append({
            'type': 'critical',
            'message': 'Critical conditions: Low moisture, high temperature, and low humidity.',
            'action': 'Immediate irrigation recommended'
        })
    
    return recommendations

# Initialize ML model
def initialize_model():
    try:
        model = joblib.load('irrigation_model.pkl')
        return model
    except:
        # Create training data with basic rules
        # Format: [soil_moisture, temperature, humidity, hour_of_day, should_irrigate]
        training_data = np.array([
            [100, 25, 60, 8, 1],   # Low moisture, morning
            [300, 25, 60, 8, 0],   # High moisture, morning
            [200, 30, 70, 14, 1],  # Medium moisture, hot afternoon
            [400, 30, 70, 14, 0],  # Very high moisture, hot afternoon
            [150, 20, 50, 20, 1],  # Low moisture, evening
            [350, 20, 50, 20, 0],  # High moisture, evening
        ])
        
        X = training_data[:, :-1]  # Features
        y = training_data[:, -1]   # Target
        
        model = RandomForestRegressor(n_estimators=100)
        model.fit(X, y)
        
        # Save the model
        joblib.dump(model, 'irrigation_model.pkl')
        return model

irrigation_model = initialize_model()

def get_thingspeak_data():
    try:
        url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/feeds.json?api_key={THINGSPEAK_API_KEY}&results=1"
        response = requests.get(url)
        data = response.json()
        return data['feeds'][0] if data['feeds'] else None
    except Exception as e:
        logging.error(f"Error fetching ThingSpeak data: {e}")
        return None

def get_firebase_data():
    try:
        ref = db.reference('/sensor_data')
        data = ref.get()
        return data or {}  # Return empty dict if None
    except Exception as e:
        logging.error(f"Error fetching Firebase data: {e}")
        return {}

def should_irrigate(soil_moisture, temperature, humidity, time_of_day):
    """AI-based decision making for irrigation"""
    try:
        # Prepare features for prediction
        features = np.array([[soil_moisture, temperature, humidity, time_of_day.hour]])
        
        # Get prediction
        prediction = irrigation_model.predict(features)[0]
        
        # If prediction is above threshold, irrigate
        return prediction > 0.5
    except Exception as e:
        logging.error(f"Error in AI prediction: {e}")
        # Fallback to basic rules if AI fails
        return soil_moisture < 300  # Irrigate if moisture is below 300

def check_schedule():
    """Check if current time is within scheduled irrigation time"""
    try:
        ref = db.reference('/irrigation_schedule')
        schedule = ref.get()
        if not schedule:
            return True  # If no schedule set, allow irrigation
            
        current_time = datetime.now().time()
        start_time = time.fromisoformat(schedule.get('start_time', '00:00'))
        end_time = time.fromisoformat(schedule.get('end_time', '23:59'))
        
        return start_time <= current_time <= end_time
    except Exception as e:
        logging.error(f"Error checking schedule: {e}")
        return True

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/data')
def get_data():
    thingspeak_data = get_thingspeak_data()
    firebase_data = get_firebase_data()
    
    # Get current sensor values with defaults
    soil_moisture = float(thingspeak_data.get('field2', 0)) if thingspeak_data else 0
    temperature = float(thingspeak_data.get('field1', 0)) if thingspeak_data else 0
    humidity = float(thingspeak_data.get('field3', 0)) if thingspeak_data else 0
    
    # Get recommendations
    recommendations = get_recommendations(soil_moisture, temperature, humidity)
    
    # Check if irrigation should be on based on AI and schedule
    should_irrigate_now = should_irrigate(soil_moisture, temperature, humidity, datetime.now())
    within_schedule = check_schedule()
    
    # Determine irrigation status
    if manual_override:
        irrigation_status = firebase_data.get('manual_status', 'OFF')
    else:
        irrigation_status = 'ON' if should_irrigate_now and within_schedule else 'OFF'
    
    # Update Firebase with new status
    try:
        ref = db.reference('/sensor_data')
        ref.update({
            'irrigation_status': irrigation_status,
            'last_updated': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error updating Firebase: {e}")
    
    # Get schedule from Firebase or use defaults
    schedule = firebase_data.get('irrigation_schedule', {})
    
    # Combine and process data
    combined_data = {
        'soil_temperature': temperature,
        'soil_moisture': soil_moisture,
        'humidity': humidity,
        'pest_data': firebase_data.get('pest_data', {}),
        'irrigation_status': irrigation_status,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'schedule': {
            'start_time': schedule.get('start_time', '00:00'),
            'end_time': schedule.get('end_time', '23:59')
        },
        'recommendations': recommendations,
        'manual_override': manual_override
    }
    
    return jsonify(combined_data)

@app.route('/api/schedule', methods=['POST'])
def update_schedule():
    try:
        data = request.json
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if not start_time or not end_time:
            return jsonify({'error': 'Start and end times are required'}), 400
            
        ref = db.reference('/irrigation_schedule')
        ref.set({
            'start_time': start_time,
            'end_time': end_time
        })
        
        return jsonify({'message': 'Schedule updated successfully'})
    except Exception as e:
        logging.error(f"Error updating schedule: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/irrigation/toggle', methods=['POST'])
def toggle_irrigation():
    global manual_override
    try:
        data = request.json
        status = data.get('status')
        
        if status not in ['ON', 'OFF']:
            return jsonify({'error': 'Invalid status'}), 400
            
        manual_override = True
        ref = db.reference('/sensor_data')
        ref.update({
            'manual_status': status,
            'last_updated': datetime.now().isoformat()
        })
        
        return jsonify({'message': f'Irrigation manually set to {status}'})
    except Exception as e:
        logging.error(f"Error toggling irrigation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/irrigation/auto', methods=['POST'])
def set_auto_mode():
    global manual_override
    try:
        manual_override = False
        return jsonify({'message': 'Switched to automatic mode'})
    except Exception as e:
        logging.error(f"Error switching to auto mode: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)