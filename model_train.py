import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import matplotlib.pyplot as plt

# === Step 1: Load dataset ===
df = pd.read_csv("final.csv")

def get_target(row):
    month = int(row["month_encoded"])
    return row[f"water_need_{month}"]

df["target_water_need"] = df.apply(get_target, axis=1)

X = df[["label_encoded", "month_encoded", "temperature", "humidity"]]
y = df["target_water_need"]

# === Step 2: Normalize inputs ===
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# === Step 3: Split for training ===
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# === Step 4: Build model ===
model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(X_train.shape[1],)),
    tf.keras.layers.Dense(32, activation="relu"),
    tf.keras.layers.Dense(16, activation="relu"),
    tf.keras.layers.Dense(1)
])
model.compile(optimizer="adam", loss="mse", metrics=["mae"])

# === Step 5: Train ===
model.fit(X_train, y_train, epochs=300, batch_size=16, verbose=1)

# === Step 6: Evaluate ===
y_pred = model.predict(X_test).flatten()
mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"\n✅ Evaluation:")
print(f"  MAE: {mae:.2f} mm")
print(f"  MSE: {mse:.2f} mm²")
print(f"  R² Score: {r2:.2f}")

# === Optional: Visualize Prediction vs Actual ===
plt.figure(figsize=(8, 6))
plt.scatter(y_test, y_pred, alpha=0.7)
plt.plot([min(y_test), max(y_test)], [min(y_test), max(y_test)], color='red')
plt.xlabel("Actual Water Need (mm)")
plt.ylabel("Predicted Water Need (mm)")
plt.title("Predicted vs Actual Water Need")
plt.grid(True)
plt.show()

# === Step 7: Export model ===
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

with open("unified_crop_model.tflite", "wb") as f:
    f.write(tflite_model)

joblib.dump(scaler, "unified_crop_scaler.pkl")
print("✅ Model and scaler saved.")

for layer in model.layers:
    weights, biases = layer.get_weights()
    print("\nWeights:\n", weights)
    print("Biases:\n", biases)
