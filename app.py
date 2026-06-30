import json
import os
import subprocess
import time
import socket
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename

import auth
import engine
import eventbus
from config import load_config
from logger import clear_logs, get_logs, log

app = Flask(__name__)
app.secret_key = auth.get_secret_key()

VIDEO_CONFIG = "/opt/showcontroller/config/video.json"
VIDEO_MEDIA_DIR = "/home/raspberry/videos"
VIDEO_MPV_SOCKET = "/tmp/showcontroller-mpv.sock"
ALLOWED_VIDEO_EXT = {".mp4", ".jpg", ".jpeg"}


@app.before_request
def require_login():
    public_endpoints = {"login", "favicon", "static"}
    if request.endpoint in public_endpoints:
        return None
    if auth.is_logged_in():
        return None
    return redirect(url_for("login", next=request.path))


def video_default_config():
    return {
        "id": "oko1",
        "name": "Око 1",
        "gpio": 17,
        "video": "/home/raspberry/videos/oko1.mp4",
        "idle": "/home/raspberry/videos/idle.jpg",
        "cec_enabled": False,
    }


def video_load_config():
    if not os.path.exists(VIDEO_CONFIG):
        return video_default_config()

    with open(VIDEO_CONFIG, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    default = video_default_config()
    default.update(cfg)
    return default


def video_save_config(cfg):
    os.makedirs(os.path.dirname(VIDEO_CONFIG), exist_ok=True)
    with open(VIDEO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def video_media_files():
    os.makedirs(VIDEO_MEDIA_DIR, exist_ok=True)
    files = []

    for p in sorted(Path(VIDEO_MEDIA_DIR).iterdir()):
        if p.is_file() and p.suffix.lower() in ALLOWED_VIDEO_EXT:
            files.append(str(p))

    return files


def restart_video_service():
    subprocess.Popen(["sudo", "systemctl", "restart", "showcontroller-video-node.service"])

def video_mpv_command(command):
    try:
        data = json.dumps(command) + "\n"
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(VIDEO_MPV_SOCKET)
        client.send(data.encode("utf-8"))
        client.close()
        return True
    except Exception as e:
        log(f"VIDEOS mpv IPC error: {e}")
        return False


def video_load_file(path):
    if not path or not os.path.exists(path):
        log(f"VIDEOS file not found: {path}")
        return False

    return video_mpv_command({
        "command": ["loadfile", path, "replace"]
    })


@app.route("/videos")
def videos_page():
    return render_page(
        "videos.html",
        active_page="videos",
        video_cfg=video_load_config(),
        video_files=video_media_files(),
    )


@app.route("/videos/upload", methods=["POST"])
def videos_upload():
    file = request.files.get("media_file")

    if not file or not file.filename:
        return redirect("/videos")

    filename = secure_filename(file.filename)
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_VIDEO_EXT:
        log(f"VIDEOS upload rejected: {filename}")
        return redirect("/videos")

    os.makedirs(VIDEO_MEDIA_DIR, exist_ok=True)
    save_path = os.path.join(VIDEO_MEDIA_DIR, filename)
    file.save(save_path)

    log(f"VIDEOS uploaded: {save_path}")
    return redirect("/videos")


@app.route("/videos/save", methods=["POST"])
def videos_save():
    cfg = video_load_config()

    cfg["id"] = request.form.get("id", cfg.get("id", "oko1")).strip()
    cfg["name"] = request.form.get("name", cfg.get("name", "Око 1")).strip()
    cfg["gpio"] = int(request.form.get("gpio", "17") or 17)
    cfg["video"] = request.form.get("video", "").strip()
    cfg["idle"] = request.form.get("idle", "").strip()
    cfg["cec_enabled"] = request.form.get("cec_enabled") == "on"

    video_save_config(cfg)
    log("VIDEOS config saved")
    restart_video_service()

    return redirect("/videos")


@app.route("/videos/restart", methods=["POST"])
def videos_restart():
    log("VIDEOS restart requested")
    restart_video_service()
    return redirect("/videos")


@app.route("/videos/delete", methods=["POST"])
def videos_delete():
    path = request.form.get("path", "").strip()

    if not path.startswith(VIDEO_MEDIA_DIR + "/"):
        log(f"VIDEOS delete rejected: {path}")
        return redirect("/videos")

    try:
        if os.path.exists(path):
            os.remove(path)
            log(f"VIDEOS deleted: {path}")
    except Exception as e:
        log(f"VIDEOS delete error: {e}")

    return redirect("/videos")

@app.route("/videos/play", methods=["POST"])
def videos_play():
    cfg = video_load_config()
    video_load_file(cfg.get("video"))
    return redirect("/videos")


@app.route("/videos/idle", methods=["POST"])
def videos_idle():
    cfg = video_load_config()
    video_load_file(cfg.get("idle"))
    return redirect("/videos")


@app.route("/videos/tv-on", methods=["POST"])
def videos_tv_on():
    log("VIDEOS TV ON requested")
    subprocess.Popen('echo "on 0" | cec-client -s -d 1', shell=True)
    return redirect("/videos")


@app.route("/videos/tv-hdmi", methods=["POST"])
def videos_tv_hdmi():
    log("VIDEOS TV HDMI requested")
    subprocess.Popen('echo "as" | cec-client -s -d 1', shell=True)
    return redirect("/videos")

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
        "video": service_status("showcontroller-video-node"),
        "logging": cfg.get("logging_enabled", True),
        "ip": get_ip(),
        "node_mode": "video"
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

@app.route("/system/mode/video", methods=["POST"])
def system_mode_video():
    log("SYSTEM mode -> VIDEO")

    subprocess.run(["sudo", "systemctl", "disable", "--now", "showcontroller-gpio.service"])
    subprocess.run(["sudo", "systemctl", "enable", "--now", "showcontroller-video-node.service"])

    return redirect("/system")


@app.route("/system/mode/gpio", methods=["POST"])
def system_mode_gpio():
    log("SYSTEM mode -> GPIO")

    subprocess.run(["sudo", "systemctl", "disable", "--now", "showcontroller-video-node.service"])
    subprocess.run(["sudo", "systemctl", "enable", "--now", "showcontroller-gpio.service"])

    return redirect("/system")

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
    if name not in ["web", "gpio", "video-node"]:
        return redirect("/system")

    if name == "video-node":
        service = "showcontroller-video-node"
    else:
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
