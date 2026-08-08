from flask import redirect, request, send_file

import engine
from config import load_config
from logger import log
from services.backup import config_backup_path, restore_config_file
from services.modules import (
    apply_modules,
    modules_with_dependency_status,
    set_module_enabled,
    install_module_dependencies,
)
from services.service_manager import (
    get_ip,
    reboot_system as system_reboot,
    restart_service as system_restart_service,
    service_status,
)
from services.node_mode import (
    ensure_current_node_mode_available,
    get_current_node_mode,
    list_node_modes,
    switch_node_mode,
)
from services.updater import check_for_updates, get_last_update_status, install_update


def get_status():
    cfg = load_config()

    web = service_status("showcontroller-web")
    current_mode = get_current_node_mode()

    active_modes = []

    for runtime in list_node_modes(enabled_only=False):
        service = runtime.get("service")
        if service and service_status(service) == "active":
            active_modes.append(runtime.get("label") or runtime.get("mode"))

    mode_text = ", ".join(active_modes) if active_modes else f"{current_mode} inactive"

    return {
        "web": web,
        "logging": cfg.get("logging_enabled", True),
        "ip": get_ip(),
        "mode": mode_text,
        "mode_active": bool(active_modes),
    }


def register_system_routes(app, render_page):
    @app.route("/system")
    def system_page():
        return render_page(
            "system.html",
            active_page="system",
            update=get_last_update_status(),
            available_modules=modules_with_dependency_status(),
            node_modes=list_node_modes(enabled_only=True),
            current_node_mode=get_current_node_mode(),
        )


    @app.route("/system/modules", methods=["POST"])
    def system_modules():
        for mod in modules_with_dependency_status():
            set_module_enabled(mod["key"], request.form.get(mod["key"]) == "on")

        apply_modules()

        ok, error = ensure_current_node_mode_available()

        if ok:
            log("SYSTEM modules updated")
        else:
            log(f"SYSTEM modules updated, but node mode availability check failed: {error}")

        return redirect("/system")


    @app.route("/system/modules/<module_key>/install-dependencies", methods=["POST"])
    def system_install_module_dependencies(module_key):
        ok, message = install_module_dependencies(module_key)
        log(f"MODULE {module_key}: {message}")

        return redirect(
            f"/system?module_msg={message}&module_ok={1 if ok else 0}"
        )


    @app.route("/system/mode/<mode>", methods=["POST"])
    def system_mode(mode):
        ok, error = switch_node_mode(mode)

        if ok:
            log(f"SYSTEM node mode -> {mode}")
        else:
            log(f"SYSTEM node mode failed ({mode}): {error}")

        return redirect("/system")


    @app.route("/backup/config")
    def backup_config():
        return send_file(
            config_backup_path(),
            as_attachment=True,
            download_name="showcontroller-backup.zip",
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
        service = None
        runtime_mode = None

        if name == "web":
            service = "showcontroller-web.service"
        else:
            for runtime in list_node_modes(enabled_only=False):
                runtime_service = runtime.get("service")

                if not runtime_service:
                    continue

                service_name = runtime_service.replace(".service", "")
                short_name = service_name

                if short_name.startswith("showcontroller-"):
                    short_name = short_name[len("showcontroller-"):]

                aliases = {
                    runtime.get("mode"),
                    runtime_service,
                    service_name,
                    short_name,
                }

                if name in aliases:
                    service = runtime_service
                    runtime_mode = runtime.get("mode")
                    break

        if not service:
            log(f"SERVICE restart ignored, unknown service alias: {name}")
            return redirect("/system")

        if runtime_mode:
            current_mode = get_current_node_mode()

            if current_mode != runtime_mode:
                log(
                    f"SERVICE restart skipped: "
                    f"{runtime_mode} is not active node mode "
                    f"(current={current_mode})"
                )
                return redirect("/system")

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
