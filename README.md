🌱 Smart AI-Powered IoT Irrigation System
This project combines AI, IoT (ESP32), and a Flask web dashboard to automate irrigation based on real-time sensor data and machine learning predictions. It supports crop-specific watering based on temperature, humidity, and rainfall for sustainable agriculture.

🚀 Features
Real-time soil moisture and weather monitoring

Crop-specific water need prediction (on-device ML via TensorFlow Lite)

ESP32 + soil moisture sensor + relay-controlled water pump

Flask dashboard with crop selector, system status, and historical logs

📁 Project Structure
.
├── firmware/           # ESP32 C++ code (Arduino-compatible)
│   ├── model.h         # TFLite model (header file)
│   └── main.ino        # Main firmware sketch
│
├── dashboard/          # Flask Web App
│   ├── app.py
│   ├── templates/
│   ├── static/
│   └── requirements.txt
│
├── model/              # ML model training notebook and scripts
│   └── train_model.ipynb
│
└── README.md
🛠️ Requirements
1. 📡 ESP32 Firmware
Arduino IDE

ESP32 board support

Libraries:

TensorFlowLite_ESP32

WiFi.h

HTTPClient.h

Wire.h

2. 🧠 Python Dashboard
Python 3.8+

Flask

pandas, numpy

(Optional) dotenv for config

Install Python dependencies:

bash
Copy
Edit
cd dashboard
pip install -r requirements.txt
🔌 Hardware Setup
ESP32 Dev Board

Soil Moisture Sensor (Analog)

Relay Module + Pump

Wi-Fi credentials hardcoded in main.ino

⚙️ How to Run
ESP32
Open firmware/main.ino in Arduino IDE.

Replace Wi-Fi credentials.

Flash to ESP32.

It reads sensor values and sends data via HTTP POST to Flask.

Flask Dashboard
bash
Copy
Edit
cd dashboard
python app.py
Visit http://localhost:5000 to access the dashboard.

Set crop, monitor live data, and view logs.

🧠 ML Model
train_model.ipynb trains a Keras model using crop ID, month, temp, and humidity.

Model is converted to .tflite, then to .h for ESP32.

Prediction happens on-device, not on server.

📊 Output Preview

🔒 Security Notes
Basic user login included (Flask sessions)

Protects dashboard with simple auth

For deployment, consider HTTPS + proper user auth

📌 To-Do
Add rain sensor integration

Improve mobile responsiveness

Cloud data storage (Firebase/MongoDB)
