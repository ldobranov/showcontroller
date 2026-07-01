import subprocess

from flask import Response, jsonify, redirect, request

import engine
from services import eventbus
from config import load_config
from logger import get_logs, log


def ping_host(host):
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", host],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def config_diagnostics():
    cfg = load_config()
    issues = []
    inputs = cfg.get("inputs", [])

    if not cfg.get("touchdesigner", {}).get("ip"):
        issues.append("Missing UDP target IP")
    if not cfg.get("touchdesigner", {}).get("port"):
        issues.append("Missing UDP target port")

    seen_gpios = {}
    for index, inp in enumerate(inputs, start=1):
        name = inp.get("name", f"Input {index}")
        if not inp.get("enabled", True):
            continue

        gpio = inp.get("gpio")
        if gpio is None or str(gpio).strip() == "":
            issues.append(f"{name}: missing GPIO")
        else:
            gpio_key = str(gpio)
            if gpio_key in seen_gpios:
                issues.append(f"GPIO{gpio_key} is used by both {seen_gpios[gpio_key]} and {name}")
            seen_gpios[gpio_key] = name

        mode = inp.get("mode", "single")
        if mode == "sequence" and not inp.get("sequence"):
            issues.append(f"{name}: sequence mode without sequence")
        if mode == "single" and not inp.get("message"):
            issues.append(f"{name}: single mode without message")

    return issues


def register_diagnostics_routes(app, render_page):
    @app.route("/diagnostics")
    def diagnostics_page():
        cfg = load_config()
        td_ip = cfg.get("touchdesigner", {}).get("ip", "")
        td_online = ping_host(td_ip) if td_ip else False

        return render_page(
            "diagnostics.html",
            active_page="diagnostics",
            inputs=engine.get_inputs_with_state(),
            td_online=td_online,
            issues=config_diagnostics(),
            logs=get_logs(20),
        )

    @app.route("/api/gpio/status")
    def api_gpio_status():
        return jsonify(eventbus.gpio_status_payload())

    @app.route("/events")
    def events_stream():
        return Response(
            eventbus.gpio_event_stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @app.route("/api/routes")
    def api_routes():
        return jsonify(sorted(str(rule) for rule in app.url_map.iter_rules()))

    @app.route("/diagnostics/send_udp", methods=["POST"])
    def diagnostics_send_udp():
        msg = request.form.get("message", "20,1").strip()
        delay = float(request.form.get("delay", "0.2") or 0.2)
        engine.send_press_release(msg, delay)
        log(f"DIAG UDP test message={msg} delay={delay}")
        return redirect("/diagnostics")

    @app.route("/diagnostics/fire_input", methods=["POST"])
    def diagnostics_fire_input():
        input_name = request.form.get("input_name", "").strip()
        if input_name:
            engine.trigger_input_by_name(input_name)
            log(f"DIAG input test {input_name}")
        return redirect("/diagnostics")
