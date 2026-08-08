import importlib
import json
import os
import subprocess

from functools import wraps
from flask import abort
from pathlib import Path

MODULES_FILE = "/opt/showcontroller/modules.json"

BASE_DIR = Path(__file__).resolve().parents[1]
MODULES_DIR = BASE_DIR / "modules"


def default_modules():
    return {
        item["key"]: item.get("enabled_by_default", True)
        for item in get_available_modules()
    }


def discover_module_manifests():
    manifests = []

    if not MODULES_DIR.exists():
        return manifests

    for path in sorted(MODULES_DIR.iterdir()):
        if not path.is_dir():
            continue

        if not (path / "manifest.py").exists():
            continue

        manifests.append(f"modules.{path.name}.manifest")

    return manifests


def module_installer_status(item):
    installer_path = item.get("installer")

    if not installer_path:
        return {
            "packages": [],
            "missing": [],
            "ok": True,
        }

    try:
        installer = importlib.import_module(installer_path)
        return installer.status()
    except Exception as exc:
        return {
            "packages": item.get("apt_packages", []),
            "missing": item.get("apt_packages", []),
            "ok": False,
            "error": str(exc),
        }


def install_module_dependencies(module_key):
    for item in get_available_modules():
        if item["key"] != module_key:
            continue

        installer_path = item.get("installer")
        if not installer_path:
            return True, "Module has no installer."

        try:
            installer = importlib.import_module(installer_path)
            result = installer.install()

            return True, result.get("message", "Dependencies installed.")

        except Exception as ex:
            return False, str(ex)

    return False, "Unknown module."


def import_callable(path):
    module_path, function_name = path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, function_name)


def get_available_modules():
    result = []
    seen_keys = set()

    for module_path in discover_module_manifests():
        try:
            manifest_module = importlib.import_module(module_path)
            manifest = manifest_module.MODULE

            if not manifest.get("key") or not manifest.get("name") or not manifest.get("register"):
                continue

            key = manifest["key"]

            if key in seen_keys:
                continue

            register = import_callable(manifest["register"])

        except Exception as exc:
            print(f"[modules] failed loading {module_path}: {exc}", flush=True)
            continue

        seen_keys.add(key)

        result.append({
            "key": key,
            "name": manifest["name"],
            "enabled_by_default": manifest.get("enabled_by_default", True),
            "menu": manifest.get("menu", []),
            "services": manifest.get("services", []),
            "runtime": manifest.get("runtime"),
            "register": register,
            "description": manifest.get("description", ""),
            "version": manifest.get("version", ""),
            "apt_packages": manifest.get("apt_packages", []),
            "installer": manifest.get("installer"),
        })

    return result


def load_modules():
    if not os.path.exists(MODULES_FILE):
        save_modules(default_modules())

    try:
        with open(MODULES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    final = default_modules()
    final.update(data)
    return final


def save_modules(data):
    os.makedirs(os.path.dirname(MODULES_FILE), exist_ok=True)
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


def module_runtimes(role=None, enabled_only=True):
    enabled = load_modules()
    result = []

    for item in get_available_modules():
        if enabled_only and not enabled.get(item["key"], False):
            continue

        runtime = item.get("runtime")
        if not runtime:
            continue

        if role and runtime.get("role") != role:
            continue

        result.append({
            **runtime,
            "module_key": item["key"],
            "module_name": item["name"],
        })

    return result


def node_runtimes(enabled_only=True):
    return module_runtimes(role="node", enabled_only=enabled_only)


def get_node_runtime(mode, enabled_only=True):
    for runtime in node_runtimes(enabled_only=enabled_only):
        if runtime.get("mode") == mode:
            return runtime

    return None


def modules_with_dependency_status():
    enabled = load_modules()
    result = []

    for item in get_available_modules():
        dep_status = module_installer_status(item)

        result.append({
            **item,
            "enabled": enabled.get(item["key"], False),
            "apt_packages": dep_status.get("packages", item.get("apt_packages", [])),
            "missing_packages": dep_status.get("missing", []),
            "dependencies_ok": dep_status.get("ok", True),
            "dependency_error": dep_status.get("error", ""),
        })

    return result


def apply_modules():
    enabled = load_modules()

    for item in get_available_modules():
        module_enabled = enabled.get(item["key"], False)

        for service in item.get("services", []):
            if module_enabled:
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
        item["register"](app, render_page)


def module_required(name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not module_enabled(name):
                abort(404)
            return func(*args, **kwargs)
        return wrapper
    return decorator
