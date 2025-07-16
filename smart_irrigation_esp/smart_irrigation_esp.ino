// === Wi-Fi & HTTP ===
#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>

// === TensorFlow Lite for ESP32 ===
#include <TensorFlowLite_ESP32.h>
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"

// === TFLite Model ===
#include "unified_crop_model.h"

// === Pin Configuration ===
#define SENSOR_PIN 34
#define RELAY_PIN 23

// === WiFi & Server Config ===
const char* ssid = "S215G";
const char* password = "Heistheman";
const char* serverURL = "http://192.168.16.166:5000/data";

//== Crop Name==
const char* cropNames[] = {
  "Apple", "Banana", "Blackgram", "Chickpea", "Coconut",
  "Coffee", "Cotton", "Grapes", "Jute", "Kidneybeans",
  "Lentil", "Maize", "Mango", "Mothbeans", "Mungbean",
  "Muskmelon", "Orange", "Papaya", "Pigeonpeas",
  "Pomegranate", "Rice", "Watermelon"
};



// === Delhi Weather Data ===
float delhiTemperature[12] = {14.4, 17.71, 23.31, 29.26, 32.8, 32.3, 30.5, 29.3, 29.0, 26.1, 20.1, 15.3};
float delhiRainfall[12]   = {19.19, 17.68, 13.25, 9.56, 15.92, 56.01, 180.09, 229.14, 105.22, 24.82, 8.39, 8.23};
float delhiHumidity[12]   = {52, 45, 38, 28, 30, 43, 66, 75, 69, 55, 55, 58};

// === Calibration ===
const float VOLTS_PER_SECOND = 0.122;
const float MIN_WATER_TIME = 1.0;
const float MAX_WATER_TIME = 30.0;

// === TFLite Setup ===
constexpr int kTensorArenaSize = 16 * 1024;
alignas(16) uint8_t tensor_arena[kTensorArenaSize];

namespace {
  tflite::ErrorReporter* error_reporter = nullptr;
  const tflite::Model* model = nullptr;
  tflite::MicroInterpreter* interpreter = nullptr;
  TfLiteTensor* input = nullptr;
  TfLiteTensor* output = nullptr;
  tflite::MicroMutableOpResolver<5> op_resolver;
}

int current_crop = 0;

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  // Initialize TFLite error reporter
  static tflite::MicroErrorReporter micro_error_reporter;
  error_reporter = &micro_error_reporter;

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");

  configTime(0, 0, "pool.ntp.org");

  // Load the model
  model = tflite::GetModel(unified_crop_model);
  if (model->version() != TFLITE_SCHEMA_VERSION) {
    Serial.printf("Model version mismatch! Expected %d, got %d\n", TFLITE_SCHEMA_VERSION, model->version());
    while (1);
  }

  // Register required ops
  op_resolver.AddFullyConnected();
  op_resolver.AddRelu();
  op_resolver.AddReshape();

  static tflite::MicroInterpreter static_interpreter(model, op_resolver, tensor_arena, kTensorArenaSize, error_reporter);
  interpreter = &static_interpreter;

  if (interpreter->AllocateTensors() != kTfLiteOk) {
    Serial.println("Tensor allocation failed!");
    while (1);
  }

  input = interpreter->input(0);
  output = interpreter->output(0);
}

void send_to_dashboard(float voltage, float water_need, bool pump_on, int month, float watering_time) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected!");
    return;
  }

  WiFiClient client;
  HTTPClient http;
  client.setTimeout(5000);
  http.begin(client, serverURL);
  http.addHeader("Content-Type", "application/json");

  String jsonPayload = "{";
  jsonPayload += "\"voltage\":" + String(voltage, 2) + ",";
  jsonPayload += "\"water_need\":" + String(water_need, 2) + ",";
  jsonPayload += "\"pump_active\":" + String(pump_on ? "true" : "false") + ",";
  jsonPayload += "\"month\":" + String(month + 1) + ",";
  jsonPayload += "\"crop_type\":" + String(current_crop) + ",";
  jsonPayload += "\"watering_time\":" + String(watering_time, 2);
  jsonPayload += "}";

  Serial.println("Sending data to server:");
  Serial.println(jsonPayload);

  int httpCode = http.POST(jsonPayload);
  if (httpCode > 0) {
    Serial.printf("HTTP Response Code: %d\n", httpCode);
    String response = http.getString();
    Serial.println("Server Response: " + response);

    int cropIdx = response.indexOf("SETTINGS:");
    if (cropIdx != -1) {
      current_crop = response.substring(cropIdx + 9).toInt();
      Serial.print("Updated crop from dashboard: ");
      Serial.println(current_crop);
    }
  } else {
    Serial.print("POST failed: ");
    Serial.println(http.errorToString(httpCode));
  }

  http.end();
}

void water_soil(float current_voltage, float target_voltage) {
  float diff = current_voltage - target_voltage;
  if (diff < 0.05) {
    Serial.println("Soil is moist enough — no watering.");
    return;
  }

  float time_sec = constrain(diff / VOLTS_PER_SECOND, MIN_WATER_TIME, MAX_WATER_TIME);
  Serial.printf("Watering for %.2f seconds...\n", time_sec);
  digitalWrite(RELAY_PIN, HIGH);
  delay(time_sec * 1000);
  digitalWrite(RELAY_PIN, LOW);
}

void loop() {
  time_t now = time(nullptr);
  struct tm* timeinfo = localtime(&now);
  int month = timeinfo->tm_mon;

  int raw = analogRead(SENSOR_PIN);
  float voltage = raw * 3.3 / 4095.0;

  float temperature = delhiTemperature[month];
  float humidity = delhiHumidity[month];
  float rainfall = delhiRainfall[month];

  input->data.f[0] = current_crop;
  input->data.f[1] = month + 1;
  input->data.f[2] = temperature;
  input->data.f[3] = humidity;

  if (interpreter->Invoke() != kTfLiteOk) {
    Serial.println("Model inference failed.");
    return;
  }

  float predicted_need = output->data.f[0];
  float unmet_need = max(0.0f, predicted_need - rainfall);
  float target_voltage = 1.62 - (unmet_need / 300.0);

  Serial.println("\n=== SMART IRRIGATION STATUS (DELHI) ===");
  Serial.printf("Crop: %s (ID %d) | Month: %d\n", cropNames[current_crop], current_crop, month + 1);
  Serial.printf("Soil Voltage: %.2f V | Predicted Water Need: %.2f mm\n", voltage, predicted_need);
  Serial.printf("Target Voltage: %.2f V | Rainfall: %.2f mm | Temp: %.1f°C | Humidity: %.1f%%\n",
                target_voltage, rainfall, temperature, humidity);

  if (rainfall < predicted_need && voltage > target_voltage) {
    float diff = voltage - target_voltage;
    float time_sec = constrain(diff / VOLTS_PER_SECOND, MIN_WATER_TIME, MAX_WATER_TIME);
    Serial.println("→ Soil is dry and rainfall is low: watering...");
    water_soil(voltage, target_voltage);
    send_to_dashboard(voltage, predicted_need, true, month, time_sec);
  } else {
    Serial.println("→ No watering needed.");
    send_to_dashboard(voltage, predicted_need, false, month, 0.0);
  }

  delay(10000);
}
