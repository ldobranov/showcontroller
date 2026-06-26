import json
import time

from config import load_config
from state import get_input_runtime


def gpio_status_payload():
    cfg = load_config()
    inputs = []
    for inp in cfg.get("inputs", []):
        name = inp.get("name", "")
        runtime = get_input_runtime(name)
        inputs.append({
            "name": name,
            "gpio": inp.get("gpio"),
            "enabled": inp.get("enabled", True),
            "mode": inp.get("mode", "single"),
            "trigger": inp.get("trigger", "release"),
            "pressed": runtime.get("pressed", False),
            "last_event": runtime.get("last_event", ""),
            "last_event_time": runtime.get("last_event_time", ""),
            "press_count": runtime.get("press_count", 0),
            "release_count": runtime.get("release_count", 0),
        })

    return {
        "type": "gpio_status",
        "time": time.time(),
        "inputs": inputs,
    }


def sse_format(data):
    return "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"


def gpio_event_stream(interval=0.05, heartbeat_interval=10):
    """
    SSE stream based on state.json/config.json, not shared memory.
    This works even when web and GPIO are separate systemd services.
    """
    last_payload = None
    last_heartbeat = time.time()

    # Send initial payload immediately.
    payload = gpio_status_payload()
    last_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    yield sse_format(payload)

    while True:
        payload = gpio_status_payload()
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        if encoded != last_payload:
            last_payload = encoded
            yield sse_format(payload)

        if time.time() - last_heartbeat >= heartbeat_interval:
            last_heartbeat = time.time()
            yield sse_format({"type": "heartbeat", "time": time.time()})

        time.sleep(interval)
