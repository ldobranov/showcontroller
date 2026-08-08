#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_COMMIT="${1:-}"
LOCK_FILE="/run/lock/showcontroller-update.lock"
STATUS_FILE="/opt/showcontroller/config/update_status.json"
CANDIDATE_DIR=""
SNAPSHOT_DIR=""
PREVIOUS_COMMIT=""
UPDATE_STARTED=0

write_status() {
    local ok="$1"
    local message="$2"
    local state="$3"
    python3 - "$STATUS_FILE" "$ok" "$message" "$state" "${TARGET_COMMIT:-}" <<'PY'
import json, os, sys, tempfile
path, ok, message, state, target = sys.argv[1:]
os.makedirs(os.path.dirname(path), exist_ok=True)
fd, tmp = tempfile.mkstemp(prefix="update-status-", dir=os.path.dirname(path))
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"ok": ok == "true", "message": message, "state": state,
                   "target": target}, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)
finally:
    if os.path.exists(tmp):
        os.unlink(tmp)
PY
}

cleanup() {
    [ -z "$CANDIDATE_DIR" ] || rm -rf -- "$CANDIDATE_DIR"
    [ -z "$SNAPSHOT_DIR" ] || rm -rf -- "$SNAPSHOT_DIR"
}

rollback() {
    local exit_code=$?
    trap - ERR
    if [ "$UPDATE_STARTED" -eq 1 ] && [ -n "$SNAPSHOT_DIR" ] && [ -d "$SNAPSHOT_DIR/installed" ]; then
        echo "Update failed; restoring the previous installation."
        rsync -a --delete "$SNAPSHOT_DIR/installed/" /opt/showcontroller/ || true
        if [ -n "$PREVIOUS_COMMIT" ]; then
            git -C "$REPO_DIR" reset --hard "$PREVIOUS_COMMIT" || true
        fi
        cp /opt/showcontroller/systemd/*.service /etc/systemd/system/ 2>/dev/null || true
        systemctl daemon-reload || true
        systemctl restart showcontroller-web || true
        restart_active_runtime || true
        write_status false "Update failed and the previous version was restored." rolled_back || true
    else
        write_status false "Update stopped before installation; no files were changed." failed || true
    fi
    cleanup
    exit "$exit_code"
}

restart_active_runtime() {
    local service
    service="$(cd /opt/showcontroller && python3 - <<'PY'
from services.modules import get_node_runtime
from services.node_mode import get_current_node_mode
runtime = get_node_runtime(get_current_node_mode(), enabled_only=True)
if runtime and runtime.get("service"):
    print(runtime["service"])
PY
)"
    [ -z "$service" ] || systemctl restart "$service"
}

health_check() {
    systemctl is-active --quiet showcontroller-web
    local http_code
    http_code="$(curl --silent --output /dev/null --write-out '%{http_code}' \
        --max-time 10 http://127.0.0.1/ || true)"
    [[ "$http_code" =~ ^[1234][0-9][0-9]$ ]]
}

trap rollback ERR
trap cleanup EXIT

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo bash scripts/safe_update.sh <commit>" >&2
    exit 1
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "Another ShowController update is already running." >&2
    exit 1
fi

if [[ ! "$TARGET_COMMIT" =~ ^[0-9a-fA-F]{40}$ ]]; then
    echo "A full 40-character target commit is required." >&2
    exit 1
fi

cd "$REPO_DIR"
git diff --quiet && git diff --cached --quiet || {
    echo "Update refused because the repository has local changes." >&2
    exit 1
}

REMOTE_COMMIT="$(git rev-parse origin/main)"
[ "$TARGET_COMMIT" = "$REMOTE_COMMIT" ] || {
    echo "Update target no longer matches origin/main; check again." >&2
    exit 1
}

PREVIOUS_COMMIT="$(git rev-parse HEAD)"
git merge-base --is-ancestor "$PREVIOUS_COMMIT" "$TARGET_COMMIT" || {
    echo "Update refused because it is not a fast-forward." >&2
    exit 1
}

write_status true "Validating update before installation." validating
CANDIDATE_DIR="$(mktemp -d /tmp/showcontroller-candidate.XXXXXX)"
git archive "$TARGET_COMMIT" | tar -x -C "$CANDIDATE_DIR"
bash "$CANDIDATE_DIR/scripts/run_tests.sh"

SNAPSHOT_DIR="$(mktemp -d /var/tmp/showcontroller-rollback.XXXXXX)"
mkdir -p "$SNAPSHOT_DIR/installed"
cp -a /opt/showcontroller/. "$SNAPSHOT_DIR/installed/"

write_status true "Installing validated update." installing
UPDATE_STARTED=1
git reset --hard "$TARGET_COMMIT"
bash "$REPO_DIR/update.sh"

health_check
UPDATE_STARTED=0
write_status true "Update completed and health checks passed." completed
echo "Safe update completed successfully."
