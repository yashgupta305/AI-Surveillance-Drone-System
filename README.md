# AI Surveillance Drone System 🚁

An advanced AI-powered surveillance drone integrating real-time AI video transmission, LiDAR-based perception, and intelligent ground control for monitoring and autonomous operations.

---

## 🚁 Drone Overview
![Drone](images/drone_full.jpg)

A custom-built hexacopter platform designed for real-time sensing, edge processing, and remote operation.

---

## 🔧 Hardware Stack

### Core Components:
- **Flight Controller:** Pixhawk6c
- **Onboard Computer:** Raspberry Pi 5  
- **Transmission System:** Skydroid H12 Pro  
- **Camera:** SIYI A8 Mini (RTSP stream)  
- **LiDAR:** YDLiDAR A1M8  
- **Optical Flow Sensor:** For position estimation (GPS-denied environments)
- **GPS:** M9N GPS

### Upcoming Integration:
- 🔥 Thermal Camera (for night surveillance & heat signature detection)

![Hardware](images/Hardware_setup.jpg)

---

## 📡 LiDAR Visualization (RViz)

Real-time LiDAR scan data processed using ROS2 and visualized in RViz.

![LiDAR](images/lidar_output.png)

---

## 🖥️ Ground Control Station (GCS)

A custom web-based control system for monitoring and controlling the drone in real time.

### Features:
- 📺 Live video feed (RTSP stream from SIYI A8 Mini)  
- 📊 Telemetry (battery, flight mode, system stats)  
- 🚧 Obstacle detection (LiDAR-based distance estimation)  
- 🎮 Manual control interface (gimbal + movement)  
- 🧭 Real-time LiDAR mapping panel  

![GCS](images/gcs_dashboard.png)

---

## 🧠 System Architecture

The system is divided into multiple layers:

1. **Drone Layer**
   - Pixhawk (flight control)
   - Sensors (LiDAR, camera, optical flow)

2. **Onboard Processing**
   - Raspberry Pi 5
   - Sensor data processing
   - MAVLink communication

3. **Communication Layer**
   - Skydroid H12 Pro (RC + telemetry)
   - RTSP video streaming

4. **Ground Station**
   - Web-based interface
   - Real-time monitoring & control

---

## 🚀 Key Features

- Real-time video streaming from onboard camera  
- LiDAR-based obstacle detection and distance estimation  
- MAVLink communication with Pixhawk  
- Web-based Ground Control Station (GCS)  
- Modular architecture for AI integration  
- Designed for GPS-denied navigation (optical flow support)  

---

## 🧠 Tech Stack

- Python  
- OpenCV  
- ROS2  
- MAVLink (pymavlink / MAVSDK)  
- Flask (Backend - GCS)  
- HTML / CSS / JavaScript (Frontend)  

---

## 📁 Project Structure

---

## 📌 Future Work

- SLAM-based environment mapping 🗺️  
- AI object detection (YOLO / Edge AI) 🤖  
- Thermal vision integration 🔥  
- Autonomous path planning 🧭  
- Cloud-based monitoring system ☁️  

---

## 🎯 Applications

- Surveillance & security  
- Search and rescue operations  
- Defense & reconnaissance  
- Smart monitoring systems  

---

## ⚙️ Drone Hardware Specifications

- Frame: Carbon Fiber Hexacopter Frame  
- Motors: Brushless DC Motors  
- Propellers: Carbon Fiber Props  
- ESC: 30A BLHeli ESCs  
- Battery: LiPo Battery Pack  

---

## 👨‍💻 Author

**Yash Gupta**
