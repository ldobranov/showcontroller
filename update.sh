#!/bin/bash

set -e

echo "======================================="
echo " ShowController Updater"
echo "======================================="

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root:"
    echo "sudo ./update.sh"
    exit 1
fi

echo
echo "Updating /opt/showcontroller..."

rsync -av --delete \
    --exclude ".git" \
    --exclude "__pycache__" \
    --exclude "config.json" \
    --exclude "auth.json" \
    --exclude "events.log" \
    --exclude "state.json" \
    --exclude "gpio.reload" \
    ./ /opt/showcontroller/

echo
echo "Setting permissions..."

chown -R raspberry:raspberry /opt/showcontroller

find /opt/showcontroller -type d -exec chmod 755 {} \;
find /opt/showcontroller -type f -exec chmod 644 {} \;

chmod +x /opt/showcontroller/install.sh 2>/dev/null || true
chmod +x /opt/showcontroller/update.sh 2>/dev/null || true

echo
echo "Reloading systemd..."

cp systemd/showcontroller-web.service /etc/systemd/system/
cp systemd/showcontroller-gpio.service /etc/systemd/system/

systemctl daemon-reload

echo
echo "Restarting services..."

systemctl restart showcontroller-web
systemctl restart showcontroller-gpio

echo
echo "======================================="
echo " Update completed."
echo "======================================="
echo
hostname -I | awk '{print "Open: http://" $1 "/"}'
