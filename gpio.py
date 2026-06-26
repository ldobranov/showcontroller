import os
import time

from gpiozero import Button

import engine
from config import load_config
from logger import log
from state import set_input_event, set_input_pressed

buttons = []
CONFIG_FILE = "/opt/showcontroller/config.json"
GPIO_RELOAD_FILE = "/opt/showcontroller/gpio.reload"


def file_mtime(path):
    try:
        return os.path.getmtime(path)
    except Exception:
        return 0


def reload_token():
    return (file_mtime(CONFIG_FILE), file_mtime(GPIO_RELOAD_FILE))


def close_gpio():
    global buttons
    for btn in buttons:
        try:
            btn.close()
        except Exception as exc:
            log(f"GPIO CLOSE error: {exc}")
    buttons = []


def reload_gpio():
    log("GPIO RELOAD started")
    close_gpio()
    setup_gpio()
    log(f"GPIO RELOAD finished: {len(buttons)} active inputs")


def setup_gpio():
    cfg = load_config()
    inputs = cfg.get("inputs", [])

    for input_cfg in inputs:
        name = input_cfg.get("name", "unknown")

        if not input_cfg.get("enabled", True):
            log(f"GPIO SKIP disabled input {name}")
            continue

        gpio = int(input_cfg.get("gpio"))
        pullup = bool(input_cfg.get("pullup", True))
        trigger = input_cfg.get("trigger", "release")
        debounce_ms = int(input_cfg.get("debounce_ms", 250))

        btn = Button(
            gpio,
            pull_up=pullup,
            bounce_time=debounce_ms / 1000,
        )

        btn.when_pressed = make_event_handler(input_cfg, "press")
        btn.when_released = make_event_handler(input_cfg, "release")

        buttons.append(btn)
        log(f"GPIO READY {name} GPIO{gpio} trigger={trigger} pullup={pullup} debounce_ms={debounce_ms}")


def make_event_handler(input_cfg, event):
    def handler():
        name = input_cfg.get("name", "unknown")
        gpio = input_cfg.get("gpio", "?")
        fire_mode = input_cfg.get("fire_mode", "timed")
        trigger = input_cfg.get("trigger", "release")

        if event == "press":
            set_input_pressed(name, True)
            log(f"GPIO PRESS {name} GPIO{gpio}")

            if fire_mode == "real_release":
                engine.fire_input_press(input_cfg)
            elif trigger == "press":
                engine.fire_input(input_cfg)

        else:
            set_input_pressed(name, False)
            log(f"GPIO RELEASE {name} GPIO{gpio}")

            if fire_mode == "real_release":
                engine.fire_input_release(input_cfg)
            elif trigger == "release":
                engine.fire_input(input_cfg)

    return handler

def run_gpio():
    setup_gpio()
    log("GPIO ENGINE started")

    last_token = reload_token()

    try:
        while True:
            current_token = reload_token()
            if current_token != last_token:
                last_token = current_token
                reload_gpio()
            time.sleep(0.5)
    finally:
        close_gpio()
        log("GPIO ENGINE stopped")
