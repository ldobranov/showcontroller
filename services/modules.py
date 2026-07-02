import importlib
import json
import os
import subprocess

from functools import wraps
from flask import abort


MODULES_FILE = "/opt/showcontroller/modules.json"

MODULE_DEFINITIONS = [
    "modules.gpio_controller.module",
    "modules.video_player.module",
]

DEFAULT_MODULES = {
    "gpio": True,
    "video": True,
}


def get_available_modules():
    result = []

    for module_path in MODULE_DEFINITIONS:
        mod = importlib.import_module(module_path)

        result.append({
            "key": mod.KEY,
            "name": mod.NAME,
            "menu": getattr(mod, "MENU", []),
            "services": getattr(mod, "SERVICES", []),
            "module": mod,
        })

    return result


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


def enabled_modules_info():
    enabled = load_modules()
    return [
        item for item in get_available_modules()
        if enabled.get(item["key"], False)
    ]


def module_menu_items():
    items = []

    for item in enabled_modules_info():
        items.extend(item["menu"])

    return items

def enabled_module_services():
    services = []

    for item in enabled_modules_info():
        for service in item["services"]:
            services.append({
                "module_key": item["key"],
                "module_name": item["name"],
                "service": service,
            })

    return services

def apply_modules():
    enabled = load_modules()

    for item in get_available_modules():
        is_enabled = enabled.get(item["key"], False)

        for service in item["services"]:
            if is_enabled:
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

def register_enabled_modules(app, render_page):
    for item in enabled_modules_info():
        item["module"].register(app, render_page)

def module_required(name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not module_enabled(name):
                abort(404)
            return func(*args, **kwargs)
        return wrapper
    return decorator
