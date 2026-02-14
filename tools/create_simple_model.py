"""
Create a simple TFLite model for anomaly detection example.
This generates a minimal valid .tflite model that can be used as a placeholder replacement.
"""
import tensorflow as tf
import numpy as np

# Create a simple model: input -> dense -> output
model = tf.keras.Sequential([
    tf.keras.layers.Dense(1, input_shape=(3,), activation='sigmoid')  # 3 inputs for gyro/accel anomaly
])

# Compile
model.compile(optimizer='adam', loss='mse')

# Save as .tflite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

# Write to file
with open('tools/simple_anomaly_model.tflite', 'wb') as f:
    f.write(tflite_model)

print("Created simple_anomaly_model.tflite")