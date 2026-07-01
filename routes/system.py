import subprocess

from flask import redirect, request, send_file

import engine
from config import load_config
from logger import log


def get_ip():
    try:
        return subprocess.check_output("hostname -I", shell=True).decode().strip()
    except Exception:
        return "unknown"


def service_status(name):
    try:
        result = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def get_status():
    cfg = load_config()
    return {
        "web": service_status("showcontroller-web"),
        "gpio": service_status("showcontroller-gpio"),
        "video": service_status("showcontroller-video-node"),
        "logging": cfg.get("logging_enabled", True),
        "ip": get_ip(),
    }


def register_system_routes(app, render_page):
    @app.route("/system")
    def system_page():
        return render_page("system.html", active_page="system")

    @app.route("/system/mode/video", methods=["POST"])
    def system_mode_video():
        log("SYSTEM mode -> VIDEO")
        subprocess.run(["sudo", "systemctl", "disable", "--now", "showcontroller-gpio.service"])
        subprocess.run(["sudo", "systemctl", "enable", "--now", "showcontroller-video-node.service"])
        return redirect("/system")

    @app.route("/system/mode/gpio", methods=["POST"])
    def system_mode_gpio():
        log("SYSTEM mode -> GPIO")
        subprocess.run(["sudo", "systemctl", "disable", "--now", "showcontroller-video-node.service"])
        subprocess.run(["sudo", "systemctl", "enable", "--now", "showcontroller-gpio.service"])
        return redirect("/system")

    @app.route("/backup/config")
    def backup_config():
        return send_file(
            "/opt/showcontroller/config.json",
            as_attachment=True,
            download_name="showcontroller-config.json",
        )

    @app.route("/restore/config", methods=["POST"])
    def restore_config():
        file = request.files.get("config_file")
        if file:
            file.save("/opt/showcontroller/config.json")
            log("CONFIG restored from web")
            engine.request_gpio_reload("config restored")
        return redirect("/system")

    @app.route("/system/reload-inputs", methods=["POST"])
    def reload_inputs():
        engine.request_gpio_reload("manual from system page")
        return redirect("/system")

    @app.route("/services/restart/<name>", methods=["POST"])
    def restart_service(name):
        if name not in ["web", "gpio", "video-node"]:
            return redirect("/system")

        if name == "video-node":
            service = "showcontroller-video-node"
        else:
            service = f"showcontroller-{name}"

        log(f"SERVICE restart requested: {service}")
        subprocess.Popen(["sudo", "systemctl", "restart", service])
        return redirect("/system")

    @app.route("/system/reboot", methods=["POST"])
    def reboot_system():
        log("SYSTEM reboot requested")
        subprocess.Popen(["sudo", "reboot"])
        return redirect("/system")
