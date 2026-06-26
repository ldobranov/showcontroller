import os
import time

from config import load_config, save_config
from logger import log
from state import (
    get_input_index,
    get_input_runtime,
    reset_input,
    set_input_index,
)
from udp import send_udp


DEFAULT_PRESS_RELEASE_DELAY = 0.2
GPIO_RELOAD_FILE = "/opt/showcontroller/gpio.reload"


def request_gpio_reload(reason="manual"):
    """Signal the separate GPIO service to reload config without restarting."""
    try:
        with open(GPIO_RELOAD_FILE, "w", encoding="utf-8") as f:
            f.write(f"{time.time()} {reason}\n")
        log(f"GPIO reload requested: {reason}")
    except Exception as exc:
        log(f"GPIO reload request failed: {exc}")



def get_inputs():
    cfg = load_config()
    return cfg.get("inputs", [])


def get_inputs_with_state():
    result = []
    for inp in get_inputs():
        item = dict(inp)
        runtime = get_input_runtime(inp.get("name", ""))
        item["pressed"] = runtime.get("pressed", False)
        item["last_event"] = runtime.get("last_event", "")
        item["last_event_time"] = runtime.get("last_event_time", "")
        item["press_count"] = runtime.get("press_count", 0)
        item["release_count"] = runtime.get("release_count", 0)
        result.append(item)
    return result


def get_first_input():
    inputs = get_inputs()
    return inputs[0] if inputs else None


def get_input_by_name(input_name):
    for input_cfg in get_inputs():
        if input_cfg.get("name") == input_name:
            return input_cfg
    return None


def get_current_message(input_cfg=None):
    if input_cfg is None:
        input_cfg = get_first_input()

    if not input_cfg:
        return "-"

    if input_cfg.get("mode") == "sequence":
        seq = input_cfg.get("sequence", [])
        if not seq:
            return "-"
        idx = get_input_index(input_cfg["name"])
        return seq[idx % len(seq)]

    return input_cfg.get("message", "-")




def get_fire_delay(input_cfg):
    delay_ms = int(input_cfg.get("fire_delay_ms", int(DEFAULT_PRESS_RELEASE_DELAY * 1000)))
    return delay_ms / 1000

def send_press_release(msg, delay=DEFAULT_PRESS_RELEASE_DELAY):
    """Send one TouchDesigner-style press/release pair: X,1 then X,0."""
    if not msg or "," not in msg:
        return

    base = msg.rsplit(",", 1)[0]

    send_udp(base + ",1")
    time.sleep(delay)
    send_udp(base + ",0")

def get_current_input_message(input_cfg):
    if not input_cfg:
        return ""

    mode = input_cfg.get("mode", "single")

    if mode == "sequence":
        seq = input_cfg.get("sequence", [])
        if not seq:
            return ""

        name = input_cfg["name"]
        idx = get_input_index(name) % len(seq)
        return seq[idx]

    return input_cfg.get("message", "").strip()


def send_press_only(msg):
    msg = (msg or "").strip()
    if not msg:
        return

    if "," in msg:
        base = msg.rsplit(",", 1)[0]
        send_udp(base + ",1")
    else:
        send_udp(msg)


def send_release_only(msg):
    msg = (msg or "").strip()
    if not msg:
        return

    if "," in msg:
        base = msg.rsplit(",", 1)[0]
        send_udp(base + ",0")
    else:
        send_udp(msg)


def advance_input(input_cfg):
    if not input_cfg:
        return

    if input_cfg.get("mode", "single") == "sequence":
        seq = input_cfg.get("sequence", [])
        if not seq:
            return

        name = input_cfg["name"]
        idx = get_input_index(name) % len(seq)
        next_idx = (idx + 1) % len(seq)
        set_input_index(name, next_idx)
        log(f"ADVANCE {name} next_index={next_idx}")


def fire_input_press(input_cfg):
    if not input_cfg or not input_cfg.get("enabled", True):
        return

    msg = get_current_input_message(input_cfg)
    send_press_only(msg)
    log(f"PRESS FIRE {input_cfg.get('name', 'unknown')} -> {msg}")


def fire_input_release(input_cfg):
    if not input_cfg or not input_cfg.get("enabled", True):
        return

    msg = get_current_input_message(input_cfg)
    send_release_only(msg)
    log(f"RELEASE FIRE {input_cfg.get('name', 'unknown')} -> {msg}")
    advance_input(input_cfg)


def fire_input(input_cfg):
    """Single entry point for firing an input from Web, GPIO, API, MQTT, etc."""
    if not input_cfg or not input_cfg.get("enabled", True):
        return

    mode = input_cfg.get("mode", "single")

    if mode == "sequence":
        seq = input_cfg.get("sequence", [])
        if not seq:
            return

        name = input_cfg["name"]
        idx = get_input_index(name) % len(seq)
        msg = seq[idx]

        send_press_release(msg, get_fire_delay(input_cfg))

        next_idx = (idx + 1) % len(seq)
        set_input_index(name, next_idx)
        log(f"FIRED {name} -> {msg} next_index={next_idx}")

    elif mode == "single":
        msg = input_cfg.get("message", "").strip()
        if msg:
            send_press_release(msg, get_fire_delay(input_cfg))
            log(f"FIRED {input_cfg.get('name', 'unknown')} -> {msg}")


def trigger_input_by_name(input_name):
    fire_input(get_input_by_name(input_name))


def trigger_first_input():
    fire_input(get_first_input())


def reset_input_by_name(input_name):
    input_cfg = get_input_by_name(input_name)
    if input_cfg:
        reset_input(input_cfg["name"])
        log(f"RESET {input_cfg['name']}")


def reset_first_input():
    input_cfg = get_first_input()
    if input_cfg:
        reset_input(input_cfg["name"])
        log(f"RESET {input_cfg['name']}")


def save_settings_from_form(form):
    cfg = load_config()

    cfg["name"] = form.get("name", "ShowController").strip()
    cfg["logging_enabled"] = form.get("logging_enabled") == "on"
    cfg["touchdesigner"] = {
        "ip": form.get("td_ip", "192.168.0.127").strip(),
        "port": int(form.get("td_port", "8891").strip()),
    }

    save_config(cfg)
    log("CONFIG saved from web")


def save_inputs_from_form(form):
    cfg = load_config()

    enabled_list = form.getlist("enabled")
    names = form.getlist("input_name")
    gpios = form.getlist("gpio")
    pullups = form.getlist("pullup")
    triggers = form.getlist("trigger")
    modes = form.getlist("mode")
    messages = form.getlist("message")
    sequences = form.getlist("sequence")

    debounce_ms_list = form.getlist("debounce_ms")
    fire_delay_ms_list = form.getlist("fire_delay_ms")
    hold_ms_list = form.getlist("hold_ms")
    fire_modes = form.getlist("fire_mode")

    inputs = []

    for i, raw_name in enumerate(names):
        name = raw_name.strip()
        if not name:
            continue

        gpio = int(gpios[i].strip())
        mode = modes[i].strip()
        trigger = triggers[i].strip()

        debounce_ms = int((debounce_ms_list[i].strip() if i < len(debounce_ms_list) else "250") or 250)
        fire_delay_ms = int((fire_delay_ms_list[i].strip() if i < len(fire_delay_ms_list) else "200") or 200)
        hold_ms = int((hold_ms_list[i].strip() if i < len(hold_ms_list) else "0") or 0)
        fire_mode = (fire_modes[i].strip() if i < len(fire_modes) else "timed") or "timed"

        item = {
            "enabled": str(i) in enabled_list,
            "name": name,
            "gpio": gpio,
            "pullup": str(i) in pullups,
            "trigger": trigger,
            "debounce_ms": debounce_ms,
            "fire_delay_ms": fire_delay_ms,
            "hold_ms": hold_ms,
            "fire_mode": fire_mode,
            "mode": mode,
        }

        if mode == "sequence":
            item["sequence"] = [
                line.strip()
                for line in sequences[i].splitlines()
                if line.strip()
            ]
            item["message"] = messages[i].strip() if i < len(messages) else ""
        else:
            item["message"] = messages[i].strip() if i < len(messages) else ""
            item["sequence"] = [
                line.strip()
                for line in sequences[i].splitlines()
                if line.strip()
            ] if i < len(sequences) else []

        inputs.append(item)

    cfg["inputs"] = inputs
    save_config(cfg)
    log(f"INPUTS saved from web: {len(inputs)} configured")
    request_gpio_reload(f"inputs saved: {len(inputs)} configured")
