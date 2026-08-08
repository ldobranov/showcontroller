from .manifest import MODULE
from services import eventbus
from flask import request, redirect, Response
from logger import log
from services.service_manager import restart_service as system_restart_service
from services.modules import module_required
from config import load_config, save_config
from services.node_mode import get_current_node_mode

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

    @app.route("/events")
    @module_required(MODULE["key"])
    def gpio_events():
        return Response(
            eventbus.gpio_event_stream(),
            mimetype="text/event-stream",
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
        cfg["touchdesigner"]["port"] = engine.safe_int(
            request.form.get("td_port"),
            cfg["touchdesigner"].get("port", 8891),
            1,
            65535,
        )

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
        # Manual test-send of a raw message. This is a diagnostic tool and
        # deliberately does not go through input enable/sequence handling.
        msg = request.form.get("message", "").strip()
        if not msg:
            return redirect(request.referrer or "/")

        log(f"MANUAL SEND -> {msg}")
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


    @app.route("/gpio/diagnostics")
    @module_required(MODULE["key"])
    def gpio_diagnostics():
        return render_page(
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
    def restart_gpio():
        current_mode = get_current_node_mode()

        if current_mode != "gpio":
            log(
                f"GPIO restart skipped: "
                f"current node mode is {current_mode}, not gpio"
            )
            return redirect("/triggers")

        system_restart_service("showcontroller-gpio")
        log("GPIO restart requested")
        return redirect("/triggers")
