from flask import redirect, request

import engine
from logger import clear_logs, get_logs


def register_main_routes(app, render_page):
    @app.route("/")
    def dashboard():
        first_input = engine.get_first_input()
        return render_page(
            "dashboard.html",
            current=engine.get_current_message(first_input),
            inputs=engine.get_inputs_with_state(),
            logs=get_logs(8),
            active_page="dashboard",
        )

    @app.route("/inputs")
    def inputs_page():
        return render_page(
            "inputs.html",
            inputs=engine.get_inputs_with_state(),
            active_page="inputs",
        )

    @app.route("/settings")
    def settings_page():
        return render_page("settings.html", active_page="settings")

    @app.route("/logs")
    def logs_page():
        return render_page("logs.html", logs=get_logs(200), active_page="logs")

    @app.route("/favicon.ico")
    def favicon():
        return ("", 204)

    @app.route("/settings/save", methods=["POST"])
    def save_settings():
        engine.save_settings_from_form(request.form)
        return redirect("/settings")

    @app.route("/inputs/save", methods=["POST"])
    def save_inputs():
        engine.save_inputs_from_form(request.form)
        return redirect("/inputs")

    @app.route("/next", methods=["POST"])
    def next_msg():
        input_name = request.form.get("input_name", "").strip()
        if input_name:
            engine.trigger_input_by_name(input_name)
        else:
            engine.trigger_first_input()
        return redirect(request.referrer or "/")

    @app.route("/send", methods=["POST"])
    def send_msg():
        msg = request.form.get("message", "").strip()
        engine.send_press_release(msg)
        return redirect(request.referrer or "/")

    @app.route("/reset", methods=["POST"])
    def reset():
        input_name = request.form.get("input_name", "").strip()
        if input_name:
            engine.reset_input_by_name(input_name)
        else:
            engine.reset_first_input()
        return redirect(request.referrer or "/")

    @app.route("/logs/clear", methods=["POST"])
    def clear_log_route():
        clear_logs()
        return redirect("/logs")
