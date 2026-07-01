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

COMMIT="$(git rev-parse --short HEAD)"
VERSION="$(cat VERSION)"
INSTALLED_AT="$(date -Iseconds)"

cat > /opt/showcontroller/version.json <<EOF
{
  "version": "$VERSION",
  "commit": "$COMMIT",
  "installed_at": "$INSTALLED_AT"
}
EOF

chown raspberry:raspberry /opt/showcontroller/version.json
chmod 644 /opt/showcontroller/version.json

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
echo
echo "Restarting services..."

systemctl restart showcontroller-web

if systemctl is-enabled --quiet showcontroller-video-node; then
    systemctl restart showcontroller-video-node
elif systemctl is-enabled --quiet showcontroller-gpio; then
    systemctl restart showcontroller-gpio
else
    echo "No active mode service enabled."
fi
echo
echo "======================================="
echo " Update completed."
echo "======================================="
echo
hostname -I | awk '{print "Open: http://" $1 "/"}'
