import datetime
import json
import os

STATE_FILE = "/opt/showcontroller/state.json"

DEFAULT_STATE = {
    "inputs": {}
}


def now_iso():
    return datetime.datetime.now().isoformat(timespec="milliseconds")


def load_state():
    if not os.path.exists(STATE_FILE):
        save_state(DEFAULT_STATE)
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"inputs": {}}


def save_state(data):
    tmp_file = STATE_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, STATE_FILE)


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
    data = load_state()
    item = ensure_input(data, input_name)
    item["index"] = index
    save_state(data)


def reset_input(input_name):
    set_input_index(input_name, 0)


def set_input_pressed(input_name, pressed):
    data = load_state()
    item = ensure_input(data, input_name)
    item["pressed"] = pressed
    save_state(data)


def set_input_event(input_name, pressed, event):
    data = load_state()
    item = ensure_input(data, input_name)

    item["pressed"] = pressed
    item["last_event"] = event
    item["last_event_time"] = now_iso()

    if event == "press":
        item["press_count"] = int(item.get("press_count", 0)) + 1
    elif event == "release":
        item["release_count"] = int(item.get("release_count", 0)) + 1

    save_state(data)


def get_input_pressed(input_name):
    data = load_state()
    return data.get("inputs", {}).get(input_name, {}).get("pressed", False)


def get_input_runtime(input_name):
    data = load_state()
    return data.get("inputs", {}).get(input_name, {})
