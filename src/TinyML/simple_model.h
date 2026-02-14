// Lightweight, dependency-free TinyML fallback model
// - Provides a deterministic anomaly score in [0,1]
// - Used when USE_TFLM==0 so the flight controller has a working TinyML detector out-of-the-box

#pragma once

#include <Arduino.h>

static inline void simple_model_init() {
  // No state to initialize for this tiny model
}

// Very small deterministic "model": a linear combination of simple features passed
// through a sigmoid to produce a normalized anomaly score in [0,1].
static inline float _sigmoid(float x) {
  return 1.0f / (1.0f + expf(-x));
}

static inline float simple_model_predict(float roll_deg, float pitch_deg,
                                        float gx, float gy, float gz,
                                        float ax, float ay, float az,
                                        float throttle)
{
  // features (absolute/normalized)
  float a_roll = fabsf(roll_deg) * 0.01f;   // scale degrees -> small
  float a_pitch = fabsf(pitch_deg) * 0.01f; // scale degrees -> small
  float gyro_mag = sqrtf(gx*gx + gy*gy + gz*gz) * 0.001f; // scale down
  float acc_mag = sqrtf(ax*ax + ay*ay + az*az) - 1.0f; // 0 when nominal
  if (acc_mag < 0) acc_mag = 0.0f;
  float thro = throttle; // already 0..1

  // hand-tuned weights (conservative detector)
  const float w_roll = 1.0f;
  const float w_pitch = 1.0f;
  const float w_gyro = 0.8f;
  const float w_acc = 1.2f;
  const float w_thro = 0.6f;
  const float bias = 1.5f;

  float linear = w_roll * a_roll + w_pitch * a_pitch + w_gyro * gyro_mag + w_acc * acc_mag + w_thro * thro - bias;
  float score = _sigmoid(linear); // [0..1]
  // small post-processing: require some minimum evidence when throttle is low
  if (thro < 0.05f) score *= 0.5f;
  return constrain(score, 0.0f, 1.0f);
}
