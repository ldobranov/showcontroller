from flask import redirect, request, url_for

from logger import clear_logs, get_logs
from services.service_manager import service_status
from services.modules import enabled_modules_info, enabled_module_services, node_runtimes

from config import load_config, save_config
from services.healthchecks import is_valid_ping_url, send_heartbeat

def register_main_routes(app, render_page):
    def get_dashboard_modules():
        services_by_module = {}

        for item in enabled_module_services():
            services_by_module.setdefault(item["module_key"], []).append({
                "name": item["service"],
                "status": service_status(item["service"]),
            })

        for runtime in node_runtimes(enabled_only=True):
            service = runtime.get("service")

            if not service:
                continue

            services_by_module.setdefault(runtime["module_key"], []).append({
                "name": service,
                "status": service_status(service),
            })

        modules = []

        for item in enabled_modules_info():
            modules.append({
                "key": item["key"],
                "name": item["name"],
                "services": services_by_module.get(item["key"], []),
            })

        return modules

    @app.route("/")
    def dashboard():
        return render_page(
            "dashboard.html",
            running_modules=get_dashboard_modules(),
            logs=get_logs(8),
            active_page="dashboard",
        )

    @app.route("/settings")
    def settings_page():
        return render_page("settings.html", active_page="settings")

    @app.route("/settings/save", methods=["POST"])
    def save_settings():
        import engine
        engine.save_settings_from_form(request.form)
        return redirect("/settings")

    @app.route("/settings/healthchecks/save", methods=["POST"])
    def save_healthchecks():
        cfg = load_config()

        enabled = request.form.get("healthchecks_enabled") == "on"
        ping_url = request.form.get("healthchecks_ping_url", "").strip()

        if enabled and not is_valid_ping_url(ping_url):
            return redirect(
                url_for(
                    "settings_page",
                    hc_ok="0",
                    hc_msg="Invalid Healthchecks.io Ping URL.",
                )
            )

        cfg["healthchecks"] = {
            "enabled": enabled,
            "ping_url": ping_url,
        }
        save_config(cfg)

        return redirect(
            url_for(
                "settings_page",
                hc_ok="1",
                hc_msg="Healthchecks settings saved.",
            )
        )

    @app.route("/settings/healthchecks/test", methods=["POST"])
    def test_healthchecks():
        ok, message = send_heartbeat()

        return redirect(
            url_for(
                "settings_page",
                hc_ok="1" if ok else "0",
                hc_msg=message,
            )
        )
    
    @app.route("/logs")
    def logs_page():
        return render_page("logs.html", logs=get_logs(200), active_page="logs")

    @app.route("/logs/clear", methods=["POST"])
    def clear_log_route():
        clear_logs()
        return redirect("/logs")

    @app.route("/favicon.ico")
    def favicon():
        return ("", 204)
