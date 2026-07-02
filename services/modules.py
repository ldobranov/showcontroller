import json
import os
import subprocess

MODULES_FILE = "/opt/showcontroller/modules.json"

MODULE_SERVICES = {
    "gpio": "showcontroller-gpio.service",
    "video": "showcontroller-video-node.service",
}

DEFAULT_MODULES = {
    "gpio": True,
    "video": True
}

def apply_modules():
    modules = load_modules()

    for name, service in MODULE_SERVICES.items():
        enabled = modules.get(name, False)

        if enabled:
            subprocess.run(
                ["systemctl", "enable", "--now", service],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.run(
                ["systemctl", "disable", "--now", service],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

def load_modules():
    if not os.path.exists(MODULES_FILE):
        save_modules(DEFAULT_MODULES)

    with open(MODULES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    final = DEFAULT_MODULES.copy()
    final.update(data)
    return final


def save_modules(data):
    with open(MODULES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def module_enabled(name):
    return load_modules().get(name, False)


def set_module_enabled(name, enabled):
    data = load_modules()
    data[name] = bool(enabled)
    save_modules(data)
