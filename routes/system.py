from flask import redirect, request, send_file

import engine
from config import load_config
from logger import log
from services.backup import config_backup_path, restore_config_file
from services.modules import (
    apply_modules,
    enabled_module_services,
    modules_with_dependency_status,
    set_module_enabled,
    install_module_dependencies,
)
from services.service_manager import (
    disable_service,
    enable_service,
    kill_process,
    get_ip,
    reboot_system as system_reboot,
    restart_service as system_restart_service,
    service_status,
)
from services.updater import check_for_updates, get_last_update_status, install_update


def get_status():
    cfg = load_config()

    web = service_status("showcontroller-web")
    active_modules = []

    for item in enabled_module_services():
        if service_status(item["service"]) == "active":
            active_modules.append(item["module_name"])

    return {
        "web": web,
        "logging": cfg.get("logging_enabled", True),
        "ip": get_ip(),
        "mode": ", ".join(active_modules) if active_modules else "No active module",
        "mode_active": bool(active_modules),
    }


def register_system_routes(app, render_page):
    @app.route("/system")
    def system_page():
        return render_page(
            "system.html",
            active_page="system",
            update=get_last_update_status(),
            available_modules=modules_with_dependency_status(),
        )

    @app.route("/system/modules", methods=["POST"])
    def system_modules():
        for mod in modules_with_dependency_status():
            set_module_enabled(mod["key"], request.form.get(mod["key"]) == "on")

        apply_modules()
        log("SYSTEM modules updated")
        return redirect("/system")

    @app.route("/system/modules/<module_key>/install-dependencies", methods=["POST"])
    def system_install_module_dependencies(module_key):
        ok, message = install_module_dependencies(module_key)
        log(f"MODULE {module_key}: {message}")

        return redirect(
            f"/system?module_msg={message}&module_ok={1 if ok else 0}"
        )

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

        # Hard cleanup: VLC can survive if video-node is killed during stop/restart.
        kill_process("vlc.*--rc-host 127.0.0.1:4212")
        kill_process("/opt/showcontroller/modules/video_player/node.py")
        kill_process("cec-client")

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
            try:
                restore_config_file(file)
                log("CONFIG restored from web")
                engine.request_gpio_reload("config restored")
            except ValueError as exc:
                log(f"CONFIG restore failed: {exc}")
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

    @app.route("/system/check-updates", methods=["POST"])
    def check_updates():
        result = check_for_updates()
        log(f"UPDATE check: {result.get('message')}")
        return redirect("/system")

    @app.route("/system/install-update", methods=["POST"])
    def install_update_route():
        ok, message = install_update()
        log(f"UPDATE install: {message}")
        return redirect("/system")
