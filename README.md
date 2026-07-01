# ShowController v1.2

**ShowController** is a Raspberry Pi based GPIO and Video Controller designed for interactive installations, museums, escape rooms, stage automation, multimedia exhibits and TouchDesigner projects.

It provides a modern web interface for configuring GPIO inputs, sending UDP commands and controlling video playback without editing configuration files manually.

---

# Features

## GPIO Controller

- Multiple GPIO inputs
- Single and Sequence modes
- Press or Release triggering
- Timed and Real Release fire modes
- Configurable debounce
- Hold detection
- Pull-up / Pull-down support
- Hot GPIO reload without restarting the GPIO service

## UDP Engine

- Configurable destination IP and port
- Automatic press/release messages
- Sequence playback
- Real Release mode
- Compatible with TouchDesigner UDP workflows

## Video Player

- Video Node integration
- Idle / Main video switching
- Video playlist configuration
- Video Node restart from Web UI

## Web Interface

- Dashboard
- Inputs
- Videos
- Diagnostics
- Logs
- Settings
- System

## Authentication

- Session based login
- Password hashing
- Change password page

## Diagnostics

- Live GPIO monitoring
- Server-Sent Events (SSE)
- Runtime statistics
- Service status

## Configuration

- Backup / Restore
- Runtime configuration
- Automatic GPIO reload after saving Inputs
- No GPIO service restart required

---

# Architecture

```
 Browser
     │
     ▼
 Flask Web UI
     │
     ├──────────────┐
     ▼              ▼
 Engine        Video Node
     │
     ▼
 GPIO Engine
     │
     ▼
 UDP Output
     │
     ▼
 TouchDesigner
```

---

# Project structure

```
showcontroller/
│
├── app.py
├── engine.py
├── gpio.py
├── udp.py
├── auth.py
├── config.py
├── logger.py
├── state.py
│
├── routes/
│   ├── auth.py
│   ├── diagnostics.py
│   ├── main.py
│   ├── system.py
│   └── videos.py
│
├── services/
│   ├── backup.py
│   ├── eventbus.py
│   └── service_manager.py
│
├── static/
│   ├── css/
│   ├── img/
│   └── js/
│
├── templates/
├── docs/
├── examples/
├── hardware/
└── systemd/
```

---

# Runtime layout

Production installation:

```
/opt/showcontroller
```

Runtime files:

```
config.json
auth.json
state.json
events.log
gpio.reload
```

These files are **not tracked by Git**.

If `config.json` does not exist, it is automatically created from:

```
config.default.json
```

---

# Development layout

Development repository:

```
/home/raspberry/showcontroller
```

Production deployment:

```
/opt/showcontroller
```

Deploy using:

```bash
sudo rsync -av --delete \
  --exclude '.git' \
  --exclude 'config.json' \
  --exclude 'auth.json' \
  --exclude 'state.json' \
  --exclude 'events.log' \
  /home/raspberry/showcontroller/ \
  /opt/showcontroller/

sudo chown -R raspberry:raspberry /opt/showcontroller

sudo systemctl restart showcontroller-web
sudo systemctl restart showcontroller-gpio
```

---

# Installation

Clone the repository:

```bash
git clone https://github.com/ldobranov/showcontroller.git
```

Install system packages:

```bash
sudo apt update

sudo apt install -y \
    python3 \
    python3-flask \
    python3-gpiozero \
    mpv
```

Install the systemd services:

```bash
sudo cp systemd/showcontroller-web.service /etc/systemd/system/
sudo cp systemd/showcontroller-gpio.service /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable showcontroller-web
sudo systemctl enable showcontroller-gpio

sudo systemctl start showcontroller-web
sudo systemctl start showcontroller-gpio
```

Open:

```
http://<raspberry-ip>/
```

(Default HTTP port 80)

---

# Authentication

Default credentials:

```
Username: admin
Password: showcontroller
```

Change the password immediately after installation.

Passwords are stored as a secure hash in:

```
/opt/showcontroller/auth.json
```

---

# UDP Message Format

Messages are configured as:

```
<number>,<value>
```

Example:

```
20,1
```

### Timed mode

ShowController sends:

```
20,1
```

waits for the configured delay and then sends:

```
20,0
```

### Real Release mode

On button press:

```
20,1
```

On button release:

```
20,0
```

---

# Configuration

Main configuration:

```
/opt/showcontroller/config.json
```

Default template:

```
config.default.json
```

Configuration can be backed up and restored directly from the **System** page.

---

# System Services

The application is split into two independent services.

### showcontroller-web

- Flask Web Interface
- Authentication
- Configuration
- Diagnostics
- System management

### showcontroller-gpio

- GPIO monitoring
- Input processing
- UDP output
- Hot configuration reload

Both services are managed by **systemd**.

---

# Current Status

**Version 1.2**

Current stable release.

Included features:

- GPIO Controller
- Video Player mode
- Authentication
- Runtime configuration
- Live diagnostics
- Backup / Restore
- Hot GPIO reload
- Modular Flask routes
- Service architecture
- Port 80 Web Interface

---

# Roadmap

## Version 1.3

- REST API
- JavaScript modules
- Improved diagnostics
- Better Video UI

## Version 2.0

- Plugin architecture
- Scheduler
- MQTT support
- DMX support
- Audio Player
- Multi-device management

---

# License

MIT License

Copyright (c) Lazar Dobranov

```

---

### Само една забележка

Бих сменил заглавието от:

> **GPIO and Video Controller**

на:

> **Interactive Show Control Platform**

Това звучи много по-професионално и не ограничава проекта до GPIO и Video. Ако след година добавиш DMX, MQTT, OSC, Audio и REST API, README няма да се налага да се пренаписва. Според мен това е по-добро описание на посоката, в която се развива ShowController.
