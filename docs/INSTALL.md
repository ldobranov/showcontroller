# Installation

This project is intended to run from `/opt/showcontroller` on Raspberry Pi OS.

```bash
sudo apt update
sudo apt install -y python3-flask python3-gpiozero
sudo rm -rf /opt/showcontroller
sudo mkdir -p /opt/showcontroller
sudo cp -r ./* /opt/showcontroller/
sudo chown -R raspberry:raspberry /opt/showcontroller
sudo chmod -R 755 /opt/showcontroller
sudo chmod 644 /opt/showcontroller/*.py
sudo chmod 644 /opt/showcontroller/*.json
sudo chmod 644 /opt/showcontroller/templates/*.html
cd /opt/showcontroller
touch events.log
[ -f state.json ] || echo '{"inputs":{}}' > state.json
chmod 664 events.log state.json
```

Install services:

```bash
sudo cp /opt/showcontroller/systemd/showcontroller-web.service /etc/systemd/system/
sudo cp /opt/showcontroller/systemd/showcontroller-gpio.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable showcontroller-web showcontroller-gpio
sudo systemctl restart showcontroller-web showcontroller-gpio
```
