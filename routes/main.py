from flask import redirect, request

from logger import clear_logs, get_logs
from services.modules import enabled_modules_info, enabled_module_services
from services.service_manager import service_status


def register_main_routes(app, render_page):
    def get_dashboard_modules():
        services_by_module = {}

        for item in enabled_module_services():
            services_by_module.setdefault(item["module_key"], []).append({
                "name": item["service"],
                "status": service_status(item["service"]),
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
