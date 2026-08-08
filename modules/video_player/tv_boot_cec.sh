#!/bin/bash

set -u

CONFIG="/opt/showcontroller/config/video.json"
MODULES="/opt/showcontroller/modules.json"
MARKER="/opt/showcontroller/config/video_deps_installed"

log() {
    echo "[tv-boot-cec] $1"
}

read_json_bool() {
    local file="$1"
    local key="$2"
    local default="$3"

    python3 - "$file" "$key" "$default" <<'PY'
import json
import sys

path, key, default = sys.argv[1], sys.argv[2], sys.argv[3]

try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    value = data.get(key)

    if value is None:
        print(default)
    elif bool(value):
        print("true")
    else:
        print("false")
except Exception:
    print(default)
PY
}

read_json_int() {
    local file="$1"
    local key="$2"
    local default="$3"

    python3 - "$file" "$key" "$default" <<'PY'
import json
import sys

path, key, default = sys.argv[1], sys.argv[2], int(sys.argv[3])

try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    value = int(data.get(key, default))
    value = max(0, min(300, value))
    print(value)
except Exception:
    print(default)
PY
}

if [ ! -f "$MARKER" ]; then
    log "dependencies marker missing, skipping"
    exit 0
fi

if [ -f "$MODULES" ]; then
    module_enabled="$(python3 - "$MODULES" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    print("true" if data.get("video", False) else "false")
except Exception:
    print("false")
PY
)"
else
    module_enabled="false"
fi

if [ "$module_enabled" != "true" ]; then
    log "video module disabled, skipping"
    exit 0
fi

if [ ! -f "$CONFIG" ]; then
    log "video config missing, skipping"
    exit 0
fi

boot_enabled="$(read_json_bool "$CONFIG" "cec_boot_enabled" "false")"
select_source="$(read_json_bool "$CONFIG" "cec_boot_select_source" "false")"
delay_seconds="$(read_json_int "$CONFIG" "cec_boot_delay" "60")"

if [ "$boot_enabled" != "true" ]; then
    log "boot CEC disabled in video config, skipping"
    exit 0
fi

if ! command -v cec-client >/dev/null 2>&1; then
    log "cec-client not installed, skipping"
    exit 0
fi

log "waiting ${delay_seconds}s"
sleep "$delay_seconds"

pkill -9 -f cec-client 2>/dev/null || true

if [ "$select_source" = "true" ]; then
    log "sending: on 0 + as"
    printf "on 0\nas\n" | timeout 10 cec-client -s -d 1 >/dev/null 2>&1 || true
else
    log "sending: on 0"
    printf "on 0\n" | timeout 8 cec-client -s -d 1 >/dev/null 2>&1 || true
fi

pkill -9 -f cec-client 2>/dev/null || true

log "done"
exit 0
