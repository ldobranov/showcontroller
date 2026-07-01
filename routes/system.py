from services.service_manager import (
    disable_service,
    enable_service,
    get_ip,
    reboot_system as system_reboot,
    restart_service as system_restart_service,
    service_status,
)
from services.backup import config_backup_path, restore_config_file
from flask import redirect, request, send_file

import engine
from config import load_config
from logger import log


def get_status():
    cfg = load_config()

    web = service_status("showcontroller-web")
    gpio = service_status("showcontroller-gpio")
    video = service_status("showcontroller-video-node")

    if video == "active":
        mode = "Video Player"
        mode_active = True
    elif gpio == "active":
        mode = "GPIO Controller"
        mode_active = True
    else:
        mode = "Unknown"
        mode_active = False

    return {
        "web": web,
        "logging": cfg.get("logging_enabled", True),
        "ip": get_ip(),
        "mode": mode,
        "mode_active": mode_active,
    }

def register_system_routes(app, render_page):
    @app.route("/system")
    def system_page():
        return render_page("system.html", active_page="system")

    @app.route("/system/mode/video", methods=["POST"])
    def system_mode_video():
        log("SYSTEM mode -> VIDEO")
        disable_service("showcontroller-gpio.service")
        enable_service("showcontroller-video-node.service")
        return redirect("/system")

    @app.route("/system/mode/gpio", methods=["POST"])
    def system_mode_gpio():
        log("SYSTEM mode -> GPIO")
        disable_service("showcontroller-video-node.service")
        enable_service("showcontroller-gpio.service")
        return redirect("/system")

    @app.route("/backup/config")
    def backup_config():
      return send_file(
        config_backup_path(),
        as_attachment=True,
        download_name="showcontroller-config.json",
      )

    @app.route("/restore/config", methods=["POST"])
    def restore_config():
        file = request.files.get("config_file")
        if file:
            restore_config_file(file)
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
        system_restart_service(service)
        return redirect("/system")

    @app.route("/system/reboot", methods=["POST"])
    def reboot_system():
        log("SYSTEM reboot requested")
        system_reboot()
        return redirect("/system")
