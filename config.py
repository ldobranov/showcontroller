import json
import os
import shutil
from contextlib import contextmanager

try:
    import fcntl
except ImportError:  # Not available on Windows; locking becomes a no-op.
    fcntl = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(BASE_DIR, "VERSION")
CONFIG_FILE = "/opt/showcontroller/config.json"
CONFIG_LOCK_FILE = CONFIG_FILE + ".lock"
DEFAULT_CONFIG_FILE = os.path.join(BASE_DIR, "config.default.json")


@contextmanager
def _config_lock():
    """Cross-process lock guarding config reads/writes."""
    if fcntl is None:
        yield
        return

    os.makedirs(os.path.dirname(CONFIG_LOCK_FILE), exist_ok=True)
    lock_fd = open(CONFIG_LOCK_FILE, "w", encoding="utf-8")
    try:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        finally:
            lock_fd.close()

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
    with _config_lock():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    cfg.setdefault("web", {})
    cfg["web"].setdefault("port", 80)

    return cfg


def save_config(data):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with _config_lock():
        tmp_file = CONFIG_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, CONFIG_FILE)


def get_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "unknown"
