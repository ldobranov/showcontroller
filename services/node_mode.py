import json
import subprocess
from pathlib import Path

from services.modules import node_runtimes, get_node_runtime


MODE_FILE = Path("/opt/showcontroller/config/node_mode.json")


def _run_systemctl(*args):
    return subprocess.run(
        ["systemctl", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _pkill(pattern):
    if not pattern:
        return

    subprocess.run(
        ["pkill", "-9", "-f", pattern],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def load_node_mode(default="gpio"):
    try:
        data = json.loads(MODE_FILE.read_text(encoding="utf-8"))
        mode = data.get("mode")
        if mode:
            return mode
    except Exception:
        pass

    return default


def save_node_mode(mode):
    MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    MODE_FILE.write_text(
        json.dumps({"mode": mode}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def list_node_modes(enabled_only=True):
    return node_runtimes(enabled_only=enabled_only)


def get_current_node_mode():
    return load_node_mode()


def stop_node_runtime(runtime):
    service = runtime.get("service")

    if service:
        _run_systemctl("stop", service)
        _run_systemctl("disable", service)

    for pattern in runtime.get("cleanup", []):
        _pkill(pattern)


def stop_all_node_runtimes(enabled_only=False):
    for runtime in node_runtimes(enabled_only=enabled_only):
        stop_node_runtime(runtime)


def start_node_runtime(runtime):
    service = runtime.get("service")

    if not service:
        return False, "Runtime has no service"

    result = _run_systemctl("enable", "--now", service)

    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip() or "systemctl failed"
        return False, msg

    return True, ""


def switch_node_mode(mode):
    runtime = get_node_runtime(mode, enabled_only=True)

    if not runtime:
        return False, f"Node mode not available or module disabled: {mode}"

    stop_all_node_runtimes(enabled_only=False)

    ok, error = start_node_runtime(runtime)

    if not ok:
        return False, error

    save_node_mode(mode)
    return True, ""

def ensure_current_node_mode_available():
    current_mode = get_current_node_mode()
    current_runtime = get_node_runtime(current_mode, enabled_only=True)

    if current_runtime:
        return True, ""

    available = list_node_modes(enabled_only=True)

    if available:
        fallback_mode = available[0].get("mode")
        return switch_node_mode(fallback_mode)

    stop_all_node_runtimes(enabled_only=False)
    return False, "No enabled node modes available"
