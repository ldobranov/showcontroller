import json
import subprocess
import time

from flask import Flask, Response, jsonify, redirect, render_template, request, send_file, session, url_for

import auth
import engine
import eventbus
from config import load_config
from logger import clear_logs, get_logs, log

app = Flask(__name__)
app.secret_key = auth.get_secret_key()


@app.before_request
def require_login():
    public_endpoints = {"login", "favicon", "static"}
    if request.endpoint in public_endpoints:
        return None
    if auth.is_logged_in():
        return None
    return redirect(url_for("login", next=request.path))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if auth.verify_login(username, password):
            auth.login_user(username)
            log(f"AUTH login success: {username}")
            return redirect(request.args.get("next") or "/")
        error = "Invalid username or password."
        log(f"AUTH login failed: {username}")

    return render_template("login.html", error=error, cfg=load_config())


@app.route("/logout", methods=["POST", "GET"])
def logout():
    username = session.get("username", "unknown")
    auth.logout_user()
    log(f"AUTH logout: {username}")
    return redirect("/login")


@app.route("/settings/password", methods=["POST"])
def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if new_password != confirm_password:
        log("AUTH password change failed: confirmation mismatch")
        return redirect("/settings?password_error=confirm")

    ok, message = auth.change_password(current_password, new_password)
    log(f"AUTH password change: {message}")
    if ok:
        return redirect("/settings?password_changed=1")
    return redirect("/settings?password_error=invalid")


def get_ip():
    try:
        return subprocess.check_output("hostname -I", shell=True).decode().strip()
    except Exception:
        return "unknown"


def service_status(name):
    try:
        result = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def get_status():
    cfg = load_config()
    return {
        "web": service_status("showcontroller-web"),
        "gpio": service_status("showcontroller-gpio"),
        "logging": cfg.get("logging_enabled", True),
        "ip": get_ip(),
    }



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


def render_page(template_name, **context):
    cfg = load_config()
    return render_template(
        template_name,
        cfg=cfg,
        status=get_status(),
        ip=get_ip(),
        auth_user=auth.current_username(),
        auth_enabled=auth.auth_enabled(),
        default_password_active=auth.default_password_active(),
        password_changed=request.args.get("password_changed"),
        password_error=request.args.get("password_error"),
        **context,
    )


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
def settings():
    return render_page("settings.html", active_page="settings")


@app.route("/logs")
def logs_page():
    return render_page("logs.html", logs=get_logs(200), active_page="logs")


@app.route("/system")
def system_page():
    return render_page("system.html", active_page="system")



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



@app.route("/favicon.ico")
def favicon():
    return ("", 204)

@app.route("/api/routes")
def api_routes():
    return jsonify(sorted(str(rule) for rule in app.url_map.iter_rules()))

@app.route("/settings/save", methods=["POST"])
def save_settings():
    engine.save_settings_from_form(request.form)
    return redirect("/settings")


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


@app.route("/inputs/save", methods=["POST"])
def save_inputs():
    engine.save_inputs_from_form(request.form)
    return redirect("/inputs")


@app.route("/logs/clear", methods=["POST"])
def clear_log_route():
    clear_logs()
    return redirect("/logs")


@app.route("/backup/config")
def backup_config():
    return send_file(
        "/opt/showcontroller/config.json",
        as_attachment=True,
        download_name="showcontroller-config.json",
    )


@app.route("/restore/config", methods=["POST"])
def restore_config():
    file = request.files.get("config_file")
    if file:
        file.save("/opt/showcontroller/config.json")
        log("CONFIG restored from web")
        engine.request_gpio_reload("config restored")
    return redirect("/system")


@app.route("/system/reload-inputs", methods=["POST"])
def reload_inputs():
    engine.request_gpio_reload("manual from system page")
    return redirect("/system")


@app.route("/services/restart/<name>", methods=["POST"])
def restart_service(name):
    if name not in ["web", "gpio"]:
        return redirect("/system")

    service = f"showcontroller-{name}"
    log(f"SERVICE restart requested: {service}")
    subprocess.Popen(["sudo", "systemctl", "restart", service])
    return redirect("/system")


@app.route("/system/reboot", methods=["POST"])
def reboot_system():
    log("SYSTEM reboot requested")
    subprocess.Popen(["sudo", "reboot"])
    return redirect("/system")




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


if __name__ == "__main__":
    log("WEB STARTED")
    app.run(host="0.0.0.0", port=8080, threaded=True)
    log("WEB STOPPED")
