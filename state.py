import datetime
import json
import os
from contextlib import contextmanager

try:
    import fcntl
except ImportError:  # Not available on Windows; locking becomes a no-op.
    fcntl = None

STATE_FILE = "/opt/showcontroller/state.json"
STATE_LOCK_FILE = STATE_FILE + ".lock"

DEFAULT_STATE = {
    "inputs": {}
}


def now_iso():
    return datetime.datetime.now().isoformat(timespec="milliseconds")


@contextmanager
def _state_lock():
    """Hold an exclusive cross-process lock for the whole read-modify-write cycle.

    This prevents both file corruption and lost updates between the web and
    GPIO processes. Falls back to a no-op lock where fcntl is unavailable.
    """
    if fcntl is None:
        yield
        return

    os.makedirs(os.path.dirname(STATE_LOCK_FILE), exist_ok=True)
    lock_fd = open(STATE_LOCK_FILE, "w", encoding="utf-8")
    try:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        finally:
            lock_fd.close()


def _read_state_unlocked():
    if not os.path.exists(STATE_FILE):
        return {"inputs": {}}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"inputs": {}}


def _write_state_unlocked(data):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp_file = STATE_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, STATE_FILE)


def load_state():
    with _state_lock():
        return _read_state_unlocked()


def save_state(data):
    with _state_lock():
        _write_state_unlocked(data)


def _update_state(mutator):
    """Atomically read, mutate, and write the state under a single lock."""
    with _state_lock():
        data = _read_state_unlocked()
        mutator(data)
        _write_state_unlocked(data)


def ensure_input(data, input_name):
    if "inputs" not in data:
        data["inputs"] = {}
    if input_name not in data["inputs"]:
        data["inputs"][input_name] = {}
    return data["inputs"][input_name]


def get_input_index(input_name):
    data = load_state()
    return data.get("inputs", {}).get(input_name, {}).get("index", 0)


def set_input_index(input_name, index):
    def mutate(data):
        item = ensure_input(data, input_name)
        item["index"] = index

    _update_state(mutate)


def reset_input(input_name):
    set_input_index(input_name, 0)


def set_input_pressed(input_name, pressed):
    def mutate(data):
        item = ensure_input(data, input_name)
        item["pressed"] = pressed

    _update_state(mutate)


def set_input_event(input_name, pressed, event):
    def mutate(data):
        item = ensure_input(data, input_name)

        item["pressed"] = pressed
        item["last_event"] = event
        item["last_event_time"] = now_iso()

        if event == "press":
            item["press_count"] = int(item.get("press_count", 0)) + 1
        elif event == "release":
            item["release_count"] = int(item.get("release_count", 0)) + 1

    _update_state(mutate)


def get_input_pressed(input_name):
    data = load_state()
    return data.get("inputs", {}).get(input_name, {}).get("pressed", False)


def get_input_runtime(input_name):
    data = load_state()
    return data.get("inputs", {}).get(input_name, {})
