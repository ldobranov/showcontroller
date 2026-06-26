# ShowController v1.1

ShowController is a Raspberry Pi GPIO to UDP controller with a web interface.

It is designed for interactive installations, exhibits, stage/show control, museum installations, and similar systems where physical inputs need to trigger UDP messages on another machine.

## Features

- GPIO input manager
- Single and sequence input modes
- UDP press/release message engine
- Configurable GPIO, pull-up, trigger edge, debounce, hold, and press/release delay
- Web dashboard
- Live GPIO status with Server-Sent Events
- Diagnostics page
- Logs page
- System controls
- Backup and restore for configuration
- Hot reload for GPIO inputs without restarting the GPIO service
- Basic session login
- Password change page

## Runtime layout

The application is intended to run from:

```text
/opt/showcontroller
```

The GitHub source is kept at repository root for easier deployment.

## Quick install

Copy the project files into `/opt/showcontroller`:

```bash
sudo rm -rf /opt/showcontroller
sudo mkdir -p /opt/showcontroller
sudo cp -r ./* /opt/showcontroller/
```

Set permissions:

```bash
sudo chown -R raspberry:raspberry /opt/showcontroller
sudo chmod -R 755 /opt/showcontroller
sudo chmod 644 /opt/showcontroller/*.py
sudo chmod 644 /opt/showcontroller/*.json
sudo chmod 644 /opt/showcontroller/templates/*.html
```

Create runtime files if they do not exist:

```bash
cd /opt/showcontroller
touch events.log
[ -f state.json ] || echo '{"inputs":{}}' > state.json
chmod 664 events.log state.json
# auth.json will be created automatically on first web start
```

Install Python dependencies:

```bash
sudo apt update
sudo apt install -y python3-flask python3-gpiozero
```

Install systemd services from `systemd/` if needed:

```bash
sudo cp /opt/showcontroller/systemd/showcontroller-web.service /etc/systemd/system/
sudo cp /opt/showcontroller/systemd/showcontroller-gpio.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable showcontroller-web showcontroller-gpio
sudo systemctl restart showcontroller-web showcontroller-gpio
```

Open the web UI:

```text
http://<raspberry-ip>:8080
```

## UDP message format

The current engine expects messages in the form:

```text
<number>,1
```

When fired, ShowController sends:

```text
<number>,1
```

waits for the configured press/release delay, then sends:

```text
<number>,0
```

Example:

```text
20,1 -> 20,0
```

For single mode, set the message field to something like:

```text
1,1
```

For sequence mode, use one message per line:

```text
1,1
2,1
3,1
```

## Authentication

Default login:

```text
admin / showcontroller
```

Change the password from **Settings → Authentication** before using ShowController on a shared network. The password is stored as a hash in `/opt/showcontroller/auth.json`.

## Configuration

The main configuration file is:

```text
/opt/showcontroller/config.json
```

A backup can be downloaded and restored from the System page.

## Project status

This is v1.1. It is stable enough for field testing and small production installations, but hardware input quality still matters. For noisy analog-like sensors, use proper conditioning hardware, a comparator, or an ADC.
