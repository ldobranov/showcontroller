import json
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(BASE_DIR, "VERSION")
CONFIG_FILE = "/opt/showcontroller/config.json"
DEFAULT_CONFIG_FILE = os.path.join(BASE_DIR, "config.default.json")

def ensure_config():
    """Create local runtime config.json from config.default.json if missing."""
    if os.path.exists(CONFIG_FILE):
        return

    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    if os.path.exists(DEFAULT_CONFIG_FILE):
        shutil.copyfile(DEFAULT_CONFIG_FILE, CONFIG_FILE)
    else:
        fallback = {
            "name": "ShowController",
            "touchdesigner": {
                "ip": "192.168.0.100",
                "port": 8891
            },
            "inputs": [],
            "logging_enabled": True,
            "version": "1.1.0"
        }
        save_config(fallback)


def load_config():
    ensure_config()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    cfg.setdefault("web", {})
    cfg["web"].setdefault("port", 80)

    return cfg


def save_config(data):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "unknown"
