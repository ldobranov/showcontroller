#!/bin/bash

set -e

echo "======================================="
echo " ShowController Installer"
echo "======================================="

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root:"
    echo "sudo bash install.sh"
    exit 1
fi

# When the project is downloaded as a ZIP archive the executable bit on the
# shell scripts is lost. Restore it here so both this run and future runs of
# ./install.sh / ./update.sh work as expected.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chmod +x "$SCRIPT_DIR/install.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/update.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/modules/video_player/tv_boot_cec.sh" 2>/dev/null || true

echo
echo "Installing system packages..."

apt update

apt install -y \
    python3 \
    python3-flask \
    python3-gpiozero \
    rsync

echo
echo "Creating installation and media directories..."

mkdir -p /opt/showcontroller
mkdir -p /home/raspberry/videos
chown raspberry:raspberry /home/raspberry/videos
chmod 755 /home/raspberry/videos

echo
echo "Copying project..."

rsync -av --delete \
    --exclude ".git" \
    --exclude "__pycache__" \
    --exclude "config.json" \
    --exclude "auth.json" \
    --exclude "events.log" \
    --exclude "state.json" \
    --exclude "gpio.reload" \
    --exclude "modules.json" \
    ./ /opt/showcontroller/

echo
echo "Syncing and updating main config.json..."
python3 -c "
import json, os
src_default = '$SCRIPT_DIR/config.default.json'
dest_config = '/opt/showcontroller/config.json'
if not os.path.exists(dest_config):
    if os.path.exists(src_default):
        with open(src_default, 'r') as f:
            data = json.load(f)
        with open(dest_config, 'w') as f:
            json.dump(data, f, indent=2)
        print('Created new config.json from template.')
else:
    with open(src_default, 'r') as f:
        default = json.load(f)
    with open(dest_config, 'r') as f:
        current = json.load(f)
    updated = False
    for key, value in default.items():
        if key not in current:
            current[key] = value
            updated = True
        elif isinstance(value, dict) and isinstance(current[key], dict):
            for sub_key, sub_value in value.items():
                if sub_key not in current[key]:
                    current[key][sub_key] = sub_value
                    updated = True
    if 'version' in default and current.get('version') != default['version']:
        current['version'] = default['version']
        updated = True
    if updated:
        with open(dest_config, 'w') as f:
            json.dump(current, f, indent=2)
        print('Successfully merged new keys into existing config.json.')
"

echo
echo "Preparing runtime files..."

# Both showcontroller-web and showcontroller-gpio run as root, so runtime
# state/config/lock files must be owned and writable by root to avoid the
# GPIO service crashing on permission-denied.
touch /opt/showcontroller/events.log
[ -f /opt/showcontroller/state.json ] || echo '{"inputs":{}}' > /opt/showcontroller/state.json

echo
echo "Setting permissions..."

# Application directory is owned by root (services run as root).
chown -R root:root /opt/showcontroller

find /opt/showcontroller -type d -exec chmod 755 {} \;
find /opt/showcontroller -type f -exec chmod 644 {} \;

chmod +x /opt/showcontroller/install.sh
chmod +x /opt/showcontroller/update.sh 2>/dev/null || true
chmod +x /opt/showcontroller/modules/video_player/tv_boot_cec.sh 2>/dev/null || true

echo
echo "Installing systemd services..."

cp /opt/showcontroller/systemd/showcontroller-web.service /etc/systemd/system/
cp /opt/showcontroller/systemd/showcontroller-gpio.service /etc/systemd/system/
cp /opt/showcontroller/systemd/showcontroller-tv-boot-cec.service /etc/systemd/system/ 2>/dev/null || true

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
