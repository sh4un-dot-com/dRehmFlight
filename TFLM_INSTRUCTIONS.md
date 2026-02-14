Enabling TensorFlow Lite Micro (TFLM) for on-device inference

This project ships a minimal C fallback model so you can compile without
installing TensorFlow Lite Micro. If you want to enable real TFLite inference
on a Teensy board, follow these steps.

1) Edit `platformio.ini` and set the build flag to enable TFLM:

```ini
build_flags = -DUSE_TFLM=1
```

2) Add a TFLM-compatible Arduino library to `lib_deps` in `platformio.ini`.
   Which library to use depends on your environment; examples you can try:

- Use a community port (may or may not exist):
  `lib_deps = https://github.com/eloquentarduino/tflite-micro-arduino.git`

- Use an official or vendor-supported port. If you have a local copy of
  TensorFlow Lite Micro for Arduino, add it as a local library or a git URL.

3) Ensure you have a valid `model_data.h` in `src/TinyML/` (this repo contains
   a small example at `src/TinyML/model_data.h`).

4) Build:

```powershell
pio run -e teensy40
```

Notes:
- PlatformIO may not have an official single-click package for TFLM; using
  TFLM on Arduino often requires manually adding the library and adapting
  include paths. If build fails with `tensorflow/lite/micro/...: No such file`,
  install or point `lib_deps` at a library that provides those headers.

- If you want me to enable `build_flags = -DUSE_TFLM=1` and add a specific
  `lib_deps` entry, tell me which Arduino TFLM port you'd like me to target
  (or I can try a few common URLs and attempt a build for you).
