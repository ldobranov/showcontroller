# Installation

This project is intended to run from `/opt/showcontroller` on Raspberry Pi OS.

The recommended way to install is:

```bash
sudo bash install.sh
```

`install.sh` restores the executable bit on the shell scripts (which is lost
when the project is downloaded as a ZIP), copies the project into
`/opt/showcontroller`, sets ownership/permissions and installs the services.

## Manual installation

Both `showcontroller-web` and `showcontroller-gpio` run as **root**, so the
application directory and its runtime files must be root-owned and writable by
root.

```bash
sudo apt update
sudo apt install -y python3-flask python3-gpiozero
sudo rm -rf /opt/showcontroller
sudo mkdir -p /opt/showcontroller
sudo cp -r ./* /opt/showcontroller/
sudo chown -R root:root /opt/showcontroller
sudo chmod -R 755 /opt/showcontroller
sudo chmod 644 /opt/showcontroller/*.py
sudo chmod 644 /opt/showcontroller/*.json
sudo chmod 644 /opt/showcontroller/templates/*.html
cd /opt/showcontroller
sudo touch events.log
[ -f state.json ] || echo '{"inputs":{}}' | sudo tee state.json > /dev/null
sudo chmod 644 events.log state.json
```

Install services:

```bash
sudo cp /opt/showcontroller/systemd/showcontroller-web.service /etc/systemd/system/
sudo cp /opt/showcontroller/systemd/showcontroller-gpio.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable showcontroller-web showcontroller-gpio
sudo systemctl restart showcontroller-web showcontroller-gpio
```
