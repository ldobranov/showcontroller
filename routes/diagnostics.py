import os
import platform
import shutil
import subprocess
import sys
import time

from flask import jsonify

from logger import get_logs
from services import eventbus
from services.service_manager import service_status
from services.modules import enabled_module_services

def read_first_line(path, default="unknown"):
    try:
        with open(path, "r") as f:
            return f.readline().strip()
    except Exception:
        return default


def command_output(command, default="unknown"):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=2,
        )
        output = result.stdout.strip()
        return output if output else default
    except Exception:
        return default


def get_cpu_temperature():
    raw = read_first_line("/sys/class/thermal/thermal_zone0/temp", "")
    try:
        return round(int(raw) / 1000, 1)
    except Exception:
        return None


def get_uptime():
    try:
        seconds = int(float(read_first_line("/proc/uptime", "0").split()[0]))
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60

        if days:
            return f"{days}d {hours}h {minutes}m"
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except Exception:
        return "unknown"


def get_memory_info():
    total = available = None

    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    total = int(line.split()[1]) * 1024
                elif line.startswith("MemAvailable:"):
                    available = int(line.split()[1]) * 1024
    except Exception:
        pass

    if total is None or available is None:
        return {
            "total": None,
            "available": None,
            "used_percent": None,
        }

    used = total - available

    return {
        "total": total,
        "available": available,
        "used_percent": round((used / total) * 100, 1),
    }

def format_bytes(value):
    try:
        value = float(value)
    except Exception:
        return "unknown"

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024

    return f"{value:.1f} PB"


def get_core_diagnostics():
    disk = shutil.disk_usage("/")

    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "raspberry_model": read_first_line("/proc/device-tree/model"),
        "hostname": command_output(["hostname"]),
        "uptime": get_uptime(),
        "load_average": ", ".join(str(x) for x in os.getloadavg()),
        "temperature": get_cpu_temperature(),
        "memory": get_memory_info(),
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "used_percent": round((disk.used / disk.total) * 100, 1),
        },
        "services": get_core_services(),
    }


def get_core_services():
    services = [
        {
            "name": "WEB",
            "service": "showcontroller-web.service",
            "status": service_status("showcontroller-web.service"),
            "type": "core",
        }
    ]

    for item in enabled_module_services():
        service_name = item["service"]

        services.append({
            "name": item["module_name"],
            "service": service_name,
            "status": service_status(service_name),
            "type": "module",
        })

    return services

def register_diagnostics_routes(app, render_page):
    @app.route("/diagnostics")
    def diagnostics_page():
        return render_page(
            "diagnostics.html",
            active_page="diagnostics",
            diagnostics=get_core_diagnostics(),
            logs=get_logs(20),
            format_bytes=format_bytes,
        )

    @app.route("/api/gpio/status")
    def api_gpio_status():
        return jsonify(eventbus.gpio_status_payload())

    @app.route("/api/routes")
    def api_routes():
        return jsonify(sorted(str(rule) for rule in app.url_map.iter_rules()))
