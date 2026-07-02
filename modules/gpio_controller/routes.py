from flask import render_template, request, redirect
from logger import log
from services.service_manager import restart_service as system_restart_service
from services.modules import module_required

import engine

def register_gpio_routes(app, render_page):
    @app.route("/triggers")
    @module_required("gpio")
    def triggers_page():
        return render_page(
            "inputs.html",
            inputs=engine.get_inputs_with_state(),
            active_page="triggers",
        )

    @app.route("/inputs")
    @module_required("gpio")
    def inputs_redirect():
        return redirect("/triggers")

    @app.route("/inputs/save", methods=["POST"])
    @module_required("gpio")
    def save_inputs():
        engine.save_inputs_from_form(request.form)
        return redirect("/triggers")

    @app.route("/next", methods=["POST"])
    @module_required("gpio")
    def next_msg():
        input_name = request.form.get("input_name", "").strip()
        if input_name:
            engine.trigger_input_by_name(input_name)
        else:
            engine.trigger_first_input()
        return redirect(request.referrer or "/")

    @app.route("/send", methods=["POST"])
    @module_required("gpio")
    def send_msg():
        msg = request.form.get("message", "").strip()
        engine.send_press_release(msg)
        return redirect(request.referrer or "/")

    @app.route("/reset", methods=["POST"])
    @module_required("gpio")
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
    @module_required("gpio")
    def gpio_reload_inputs():
        engine.request_gpio_reload("manual from gpio page")
        return redirect("/triggers")

    @app.route("/gpio/restart", methods=["POST"])
    @module_required("gpio")
    def gpio_restart_service():
        log("GPIO restart requested from gpio page")
        system_restart_service("showcontroller-gpio")
        return redirect("/triggers")
