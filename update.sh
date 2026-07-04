#!/bin/bash

set -e

echo "======================================="
echo " ShowController Updater"
echo "======================================="

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root:"
    echo "sudo bash update.sh"
    exit 1
fi

# Restore executable bit on shell scripts (lost when downloaded as a ZIP).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chmod +x "$SCRIPT_DIR/install.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/update.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/modules/video_player/tv_boot_cec.sh" 2>/dev/null || true

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
    --exclude "config/node_mode.json" \
    ./ /opt/showcontroller/

# update.sh may run as root inside a repo owned by another user (e.g. the
# OTA updater). Mark the repo as safe so git does not refuse with a
# "dubious ownership" error.
git config --global --add safe.directory "$SCRIPT_DIR" 2>/dev/null || true

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

chown root:root /opt/showcontroller/version.json 2>/dev/null || true
chmod 644 /opt/showcontroller/version.json

echo
echo "Setting permissions..."

# Keep application code root-owned. Runtime services use their own working directories.
chown -R root:root /opt/showcontroller

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

ACTIVE_NODE_SERVICE="$(cd /opt/showcontroller && python3 - <<'PY'
from services.node_mode import get_current_node_mode
from services.modules import get_node_runtime

mode = get_current_node_mode()
runtime = get_node_runtime(mode, enabled_only=True)

if runtime and runtime.get("service"):
    print(runtime["service"])
PY
)"

if [ -n "$ACTIVE_NODE_SERVICE" ]; then
    echo "Restarting active node service: $ACTIVE_NODE_SERVICE"
    systemctl restart "$ACTIVE_NODE_SERVICE" || true
else
    echo "No active node service to restart"
fi

echo
echo "======================================="
echo " Update completed."
echo "======================================="
echo
hostname -I | awk '{print "Open: http://" $1 "/"}'
