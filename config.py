import json
import os

CONFIG_FILE = "/opt/showcontroller/config.json"

DEFAULT_CONFIG = {
    "name": "ShowController",
    "touchdesigner": {
        "ip": "192.168.0.100",
        "port": 8891
    },
    "inputs": [
        {
            "enabled": True,
            "name": "Input 1",
            "gpio": 17,
            "pullup": True,
            "trigger": "press",
            "mode": "sequence",
            "sequence": [
                "1,1",
                "2,1",
                "3,1"
            ],
            "debounce_ms": 80,
            "fire_delay_ms": 200,
            "hold_ms": 0
        }
    ],
    "logging_enabled": True
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
