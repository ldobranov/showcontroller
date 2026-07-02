from .manifest import MODULE
from flask import render_template, request, redirect
from logger import log
from services.service_manager import restart_service as system_restart_service
from services.modules import module_required
from config import load_config, save_config

import engine

def register_gpio_routes(app, render_page):

    @app.route("/triggers")
    @module_required(MODULE["key"])
    def triggers_page():
        return render_page(
            "inputs.html",
            inputs=engine.get_inputs_with_state(),
            active_page="triggers",
        )

    @app.route("/inputs")
    @module_required(MODULE["key"])
    def inputs_redirect():
        return redirect("/triggers")

    @app.route("/inputs/save", methods=["POST"])
    @module_required(MODULE["key"])
    def save_inputs():
        engine.save_inputs_from_form(request.form)
        return redirect("/triggers")

    @app.route("/triggers/save-settings", methods=["POST"])
    @module_required(MODULE["key"])
    def save_trigger_settings():
        cfg = load_config()

        cfg.setdefault("touchdesigner", {})
        cfg["touchdesigner"]["ip"] = request.form.get("td_ip", "").strip()
        cfg["touchdesigner"]["port"] = int(request.form.get("td_port", 8891) or 8891)

        save_config(cfg)
        engine.request_gpio_reload("trigger settings updated")
        return redirect("/triggers")

    @app.route("/next", methods=["POST"])
    @module_required(MODULE["key"])
    def next_msg():
        input_name = request.form.get("input_name", "").strip()
        if input_name:
            engine.trigger_input_by_name(input_name)
        else:
            engine.trigger_first_input()
        return redirect(request.referrer or "/")

    @app.route("/send", methods=["POST"])
    @module_required(MODULE["key"])
    def send_msg():
        msg = request.form.get("message", "").strip()
        engine.send_press_release(msg)
        return redirect(request.referrer or "/")

    @app.route("/reset", methods=["POST"])
    @module_required(MODULE["key"])
    def reset():
        input_name = request.form.get("input_name", "").strip()
        if input_name:
            engine.reset_input_by_name(input_name)
        else:
            engine.reset_first_input()
        return redirect(request.referrer or "/")


    @app.route("/diagnostics")
    def gpio_diagnostics():
        import engine

        return render_template(
            "gpio_diagnostics.html",
            inputs=engine.get_inputs_with_state(),
            active_page="gpio_diagnostics",
        )


    @app.route("/gpio/reload-inputs", methods=["POST"])
    @module_required(MODULE["key"])
    def gpio_reload_inputs():
        engine.request_gpio_reload("manual from gpio page")
        return redirect("/triggers")

    @app.route("/gpio/restart", methods=["POST"])
    @module_required(MODULE["key"])
    def gpio_restart_service():
        log("GPIO restart requested from gpio page")
        system_restart_service("showcontroller-gpio")
        return redirect("/triggers")
