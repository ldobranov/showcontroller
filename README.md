# ShowController v1.2.6

A modular Raspberry Pi controller for GPIO, Video Playback and interactive installations.

Designed for museums, escape rooms, exhibits, show control, digital signage and automation.

---

# Features

## GPIO Controller

- Unlimited GPIO inputs
- Press / Release events
- Single and Sequence modes
- Debounce, Hold and Delay
- Runtime GPIO reload
- Live diagnostics (SSE)

## Video Player

- Persistent VLC player
- GPIO triggered playback
- Idle image or idle video
- HDMI audio output
- Active High / Active Low sensor support
- HDMI-CEC TV control (optional)
- Optimized for Raspberry Pi 3 / 4

## Web Interface

- Dashboard
- Inputs
- Settings
- Videos
- Diagnostics
- Logs
- System management

## System

- Backup / Restore configuration
- OTA updates from GitHub
- Version tracking
- Service management
- GPIO / Video mode switching
- Raspberry reboot
- Authentication

---

# Requirements

```bash
sudo apt update

sudo apt install -y \
    python3-flask \
    python3-gpiozero \
    vlc
```

---

# Installation

```bash
git clone https://github.com/ldobranov/showcontroller.git

cd showcontroller

sudo ./install.sh
```

---

# Updating

From the Web UI:

```
System → Upgrade
```

or manually:

```bash
git fetch origin
git reset --hard origin/main

sudo ./update.sh
```

---

# Runtime Layout

Application:

```
/opt/showcontroller
```

Repository:

```
/home/raspberry/showcontroller
```

Configuration:

```
/opt/showcontroller/config
```

Videos:

```
/home/raspberry/videos
```

---

# Default Login

```
Username: admin
Password: showcontroller
```

Change the password immediately after installation.

---

# Project Structure

```
showcontroller/
│
├── app.py
├── engine.py
├── gpio.py
├── service.py
│
├── routes/
├── services/
├── templates/
├── static/
├── video_node/
├── systemd/
│
├── install.sh
├── update.sh
├── VERSION
└── README.md
```

---

# Current Version

**v1.2.6**

### Highlights

- Persistent VLC Video Player
- HDMI Audio support
- Active Low sensor support
- OTA GitHub Updates
- Version tracking
- Modular Flask routes
- Live GPIO diagnostics
- Runtime GPIO reload

---

# Roadmap

## v2.0 — ShowController Core

Separate the platform into a modular core and pluggable modules.

### Core

- Engine
- GPIO abstraction
- UDP
- Service Manager
- Configuration Manager
- Event Bus

### Modules

- GPIO Controller
- Video Player
- Audio Player
- DMX
- MQTT
- Modbus

Future modules will be installable independently while sharing the same ShowController Core.
