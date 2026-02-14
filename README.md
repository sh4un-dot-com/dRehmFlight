![dRehmFlight Logo](https://github.com/nickrehm/dRehmFlight/blob/master/dRehmFlight%20Logo.png)

[Intro Video](https://www.youtube.com/watch?v=tlD0C5CrWcA&lc=Ugx6m02xjHk8QH19vd94AaABAg)

[RcGroups Support Thread](https://www.rcgroups.com/forums/showthread.php?3706571-dRehmFlight-VTOL-Teensy-Flight-Controller-and-Stabilization)

## Overview
This project is a work in progress, and was originally developed for research vehicle platforms at the University of Maryland Alfred Gessow Rotorcraft Center. Current Version: Beta 1.2.

dRehmFlight is a simple, bare-bones flight controller intended for all types of vertical takeoff and landing (VTOL) vehicles from simple multirotors to more complex transitioning vehicles. This flight controller software and hardware package was developed with people in mind who may not be particularly fluent in object-oriented programming. The goal is to have an easy to understand flow of discrete operations that allows anyone with basic knowledge of coding in C/Arduino to peer into the code, make the changes they need for their specific application, and quickly have something flying. It is assumed that anyone using this code has previous experience building and flying model aircraft and is familiar with basic RC technology and terminology. The Teensy 4.0 board used for dRehmFlight is an extremely powerful microcontroller that allows for understandable code to run at very high speeds: perfect for a hobby-level flight controller. 

Rather than a comprehensive package suitable for plug-and-play type setup, this package serves more as a toolkit, where all the required difficult computations and processes are done for you. From there, it is simple to adapt to your specific vehicle configuration with full access to every variable and pinout, unlike other flight controller packages. The code is easily modified and expandable to include your own actuators, data collection methods, and sensors. Much more information is provided in the comprehensive dRehmFlight VTOL Documentation .pdf.

This code is entirely free to use and will stay that way forever. If you found this helpful for your project, donations are appreciated: [Paypal Donation](https://www.paypal.me/NicholasRehm)



### Hardware Requirements
This flight controller is based off of the Teensy 4.0 microcontroller and MPU6050 6DOF IMU. The following components (available on Amazon) are required to complete the flight controller assembly:


**Teensy 4.0**: https://amzn.to/2V1q2Gw

**GY-521 MPU6050 IMU**: https://amzn.to/3edF1Vn

These (and all Amazon links contained within the supporting documentation) are Amazon Affiliate links; by purchasing from these, I receive a small portion of the revenue at no cost to you. I appreciate any and all support!

### Software Requirments
Code is uploaded to the board using the Arduino IDE; download the latest version here: https://www.arduino.cc/en/main/software

To connect to the Teensy, you must also download and install the Teensyduino arduino add-on; download and instructions available here: https://www.pjrc.com/teensy/td_download.html


## Tutorial Videos
[Building the Flight Controller Hardware](https://www.youtube.com/watch?v=EBXBEB-Xv7w&)

[Setting Up Your Radio Connection](https://www.youtube.com/watch?v=Wdc1o6eSsMo)

[Mounting and Configuring the IMU](https://www.youtube.com/watch?v=pi4PiBFPt70)

[How the Flight Controller Code Works](https://www.youtube.com/watch?v=_n5GBudUf5Q&lc=UgwvXX18w7FtJH1ClLl4AaABAg)

## Flight Videos
dRehmflight has been successfully implemented on the following platforms:

**Autonomous Quadrotor:** https://www.youtube.com/watch?v=GZLUbTSWPI8

**Quadrotor Biplane VTOL:** https://www.youtube.com/watch?v=rk4tUKM6bd0

**Dual Cyclocopter MAV:** https://www.youtube.com/watch?v=uP87-yU1l6I

**VTOL F-35 Tricopter:** https://www.youtube.com/watch?v=Ds-ODWydxeY&

**Model SpaceX Starhopper:** https://www.youtube.com/watch?v=VsyFejn40Ss

**Model SpaceX Starship:** https://www.youtube.com/watch?v=5lwH7xJnB4I

I would love to see your flying creations and maybe feature them here as well. Please email me at nrehm@umd.edu with any videos/pics of your project. -Nick Rehm


## Disclaimer
This code is a shared, open source flight controller for small micro aerial vehicles and is intended to be modified to suit your needs. It is NOT intended to be used on manned vehicles. I do not claim any responsibility for any damage or injury that may be inflicted as a result of the use of this code. Use and modify at your own risk. More specifically put:

THIS SOFTWARE IS PROVIDED BY THE CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fgithub.com%2Fnickrehm%2FdRehmFlight&count_bg=%23E30F0F&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=hits&edge_flat=false)](https://hits.seeyoufarm.com)

## Advanced integrations: TinyML (TFLM), native MAVLink, and offboard optimizer

- TinyML (TensorFlow Lite Micro): this repo includes a lightweight C fallback anomaly detector so anomaly detection works out-of-the-box. To run a real TFLM model:
  1. Add TensorFlow Lite Micro to your Arduino/PlatformIO project (install library or add source files).
  2. Convert your .tflite model to a C array (e.g. with xxd) and add it as `model_data.h` in the sketch root.
  3. Build with `-DUSE_TFLM=1` (see PlatformIO sample below).
  The sketch will automatically use the TFLM runtime when `USE_TFLM` is defined; otherwise it runs the conservative C fallback.

- Native MAVLink: the firmware contains a conditional native MAVLink path. To enable full MAVLink messaging:
  1. Add MAVLink headers (generate via mavlink generator or install a MAVLink library) and ensure include path is available.
  2. Build with `-DUSE_MAVLINK_LIB` to enable the native branch. If not defined, a JSON-based MAVBRIDGE fallback is used.

- Offboard optimizers:
  - `tools/autoopt_simple_es.py` — improved ES with population, adaptive sigma and CSV logging.
  - `tools/autoopt_cmaes.py` — sep/diag CMA‑ES style optimizer for more robust search.
  - `tools/autoopt_bayes.py` — surrogate-based Bayesian-style optimizer (EI acquisition) with simulation mode and CSV logging.
  All optimizers use the serial `APPLY_GAINS` + `AUTOOPT` telemetry flow; use bench testing only (props off).

### PlatformIO example (quick-start)

Add this to `platformio.ini` or adapt your build system:

[env:teensy40]
platform = teensy
board = teensy40
framework = arduino
build_flags = -DUSE_TFLM=0  ; set to 1 once you've added a valid model_data.h and TFLM sources
; to enable native MAVLink add: -DUSE_MAVLINK_LIB (the repo contains a minimal MAVLink stub; replace with real headers if desired)


### Tools: converting models & generating MAVLink headers
- Convert a trained TFLite model into `model_data.h`:
  python tools/convert_tflite_to_model_data.py path/to/your_model.tflite Versions/dRehmFlight_Teensy_BETA_1.2/model_data.h
  then build with `-DUSE_TFLM=1`.

- Generate MAVLink headers (local machine with pymavlink):
  pip install pymavlink
  python tools/generate_mavlink_headers.py --dialect common --out src/Mavlink/gen
  Copy generated headers into the sketch include path and build with `-DUSE_MAVLINK_LIB`.


---

If you'd like, I can (pick one or tell me "all"):
- Convert a trained anomaly model to `model_data.h` and add it to the repo ✅
- Add generated MAVLink headers (small subset) so native MAVLink compiles out-of-the-box ✅
- Add more advanced offboard optimizer (CMA-ES / Bayesian) ✅

