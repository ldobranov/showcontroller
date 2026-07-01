# ShowController v1.2.4

A modular Raspberry Pi based GPIO / Video Controller for interactive installations, museums, escape rooms and stage automation.

---

## Features

### GPIO Controller
- Unlimited GPIO inputs
- Press / Release events
- Single and Sequence modes
- Configurable debounce
- Hold detection
- Runtime GPIO reload
- Live diagnostics (SSE)

### Video Player
- Persistent VLC player
- GPIO triggered playback
- Idle image / idle video support
- HDMI-CEC TV power on (optional)
- 1080p playback (Pi4 recommended)
- Optimized for Raspberry Pi

### Web Interface
- Dashboard
- Inputs
- Settings
- Videos
- Diagnostics
- Logs
- System page

### System
- Backup / Restore configuration
- OTA update from GitHub
- Restart services
- Switch GPIO / Video mode
- Reboot Raspberry
- Version tracking
- Authentication

---

## Requirements

```bash
sudo apt update

sudo apt install -y \
    python3-flask \
    python3-gpiozero \
    vlc
```

---

## Installation

```bash
git clone https://github.com/ldobranov/showcontroller.git
cd showcontroller

sudo ./install.sh
```

---

## Updating

Automatic:

System → Upgrade → Check for updates

or

```bash
git fetch origin
git reset --hard origin/main
sudo ./update.sh
```

---

## Runtime directory

```
/opt/showcontroller
```

Repository:

```
/home/raspberry/showcontroller
```

---

## Default Login

```
admin
showcontroller
```

---

## Project structure

```
showcontroller/
    app.py
    engine.py
    routes/
    services/
    templates/
    static/
    video_node/
    systemd/
```

---

## Current Version

```
v1.2.4
```

```
Persistent VLC player
OTA updates
Modular Flask routes
Service manager
Live GPIO diagnostics
```

---

## Roadmap

### v2.0

- Multiple Video Nodes
- Network discovery
- Scheduler
- MQTT
- REST API
- Plugin system
