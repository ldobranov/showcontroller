#!/bin/bash

set -e

echo "======================================="
echo " ShowController Installer"
echo "======================================="

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root:"
    echo "sudo ./install.sh"
    exit 1
fi

echo
echo "Installing system packages..."

apt update

apt install -y \
    python3 \
    python3-flask \
    python3-gpiozero \
    vlc

echo
echo "Creating installation directory..."

mkdir -p /opt/showcontroller

echo
echo "Copying project..."

rsync -av --delete \
    --exclude ".git" \
    --exclude "__pycache__" \
    --exclude "config.json" \
    --exclude "auth.json" \
    --exclude "events.log" \
    --exclude "state.json" \
    ./ /opt/showcontroller/

echo
echo "Setting permissions..."

chown -R raspberry:raspberry /opt/showcontroller

find /opt/showcontroller -type d -exec chmod 755 {} \;
find /opt/showcontroller -type f -exec chmod 644 {} \;

chmod +x /opt/showcontroller/install.sh

echo
echo "Installing systemd services..."

cp systemd/showcontroller-web.service /etc/systemd/system/
cp systemd/showcontroller-gpio.service /etc/systemd/system/

systemctl daemon-reload

systemctl enable showcontroller-web
systemctl enable showcontroller-gpio

echo
echo "Starting services..."

systemctl restart showcontroller-web
systemctl restart showcontroller-gpio

echo
echo "======================================="
echo " Installation completed."
echo "======================================="
echo
echo "Open:"
echo
hostname -I | awk '{print "http://" $1 "/"}'
echo
