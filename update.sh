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
    --exclude "modules.json" \
    --exclude "config/video.json" \
    --exclude "config/video_deps_installed" \
    ./ /opt/showcontroller/

COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
VERSION="$(cat VERSION 2>/dev/null || echo unknown)"
INSTALLED_AT="$(date -Iseconds)"

cat > /opt/showcontroller/version.json <<EOF
{
  "version": "$VERSION",
  "commit": "$COMMIT",
  "installed_at": "$INSTALLED_AT"
}
EOF

chown raspberry:raspberry /opt/showcontroller/version.json 2>/dev/null || true
chmod 644 /opt/showcontroller/version.json

echo
echo "Setting permissions..."

chown -R raspberry:raspberry /opt/showcontroller

find /opt/showcontroller -type d -exec chmod 755 {} \;
find /opt/showcontroller -type f -exec chmod 644 {} \;

chmod +x /opt/showcontroller/install.sh 2>/dev/null || true
chmod +x /opt/showcontroller/update.sh 2>/dev/null || true
chmod +x /opt/showcontroller/modules/video_player/tv_boot_cec.sh 2>/dev/null || true

echo
echo "Reloading systemd..."

cp systemd/showcontroller-web.service /etc/systemd/system/
cp systemd/showcontroller-gpio.service /etc/systemd/system/
cp systemd/showcontroller-video-node.service /etc/systemd/system/ 2>/dev/null || true
cp systemd/showcontroller-tv-boot-cec.service /etc/systemd/system/ 2>/dev/null || true

systemctl daemon-reload

echo
echo "Restarting services..."

systemctl restart showcontroller-web

for svc in showcontroller-gpio showcontroller-video-node; do
    if systemctl is-enabled --quiet "$svc"; then
        systemctl restart "$svc"
    fi
done

echo
echo "======================================="
echo " Update completed."
echo "======================================="
echo
hostname -I | awk '{print "Open: http://" $1 "/"}'
