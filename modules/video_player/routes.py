from .manifest import MODULE
from pathlib import Path
from flask import redirect, request
from werkzeug.utils import secure_filename
from services.modules import module_required
from logger import log

import json
import os
import re
import socket
import subprocess


VIDEO_CONFIG = "/opt/showcontroller/config/video.json"
VIDEO_MEDIA_DIR = "/home/raspberry/videos"
ALLOWED_VIDEO_EXT = {".mp4", ".jpg", ".jpeg"}
VLC_HOST = "127.0.0.1"
VLC_PORT = 4212


def video_default_config():
    return {
        "id": "video1",
        "name": "Video 1",
        "gpio": 17,
        "video": "/home/raspberry/videos/video1.mp4",
        "idle": "/home/raspberry/videos/idle.mp4",
        "active_low": False,
        "pullup": True,
        "sensor2_enabled": False,
        "sensor2_gpio_pin": 27,
        "sensor2_active_low": False,
        "sensor2_pull_up": True,
        "active_threshold": 0.3,
        "idle_threshold": 2.0,
        "audio_device": "hdmi:CARD=vc4hdmi,DEV=0",
        "active_lock_seconds": 10,
        "cec_enabled": False,
        "cec_boot_enabled": True,
        "cec_boot_delay": 60,
        "cec_boot_select_source": False,
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


def safe_int(value, default, min_value=None, max_value=None):
    try:
        result = int(value)
    except Exception:
        result = default

    if min_value is not None:
        result = max(min_value, result)
    if max_value is not None:
        result = min(max_value, result)

    return result


def restart_video_service():
    subprocess.Popen(["sudo", "systemctl", "restart", "showcontroller-video-node.service"])


def vlc_read(command, timeout=0.8):
    try:
        with socket.create_connection((VLC_HOST, VLC_PORT), timeout=1) as sock:
            sock.settimeout(timeout)
            sock.sendall((command + "\n").encode("utf-8"))

            chunks = []
            while True:
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    break

                if not chunk:
                    break

                chunks.append(chunk.decode("utf-8", errors="replace"))

            return "".join(chunks)
    except Exception as exc:
        log(f"VIDEOS VLC RC error: {exc}")
        return None


def vlc_command(command):
    return vlc_read(command, timeout=0.2) is not None


def clean_playlist_title(title):
    title = title.strip()
    title = title.split(" (", 1)[0]
    title = title.split(" [", 1)[0]
    return title.strip()


def parse_playlist_items(raw):
    items = []

    if not raw:
        return items

    for line in raw.splitlines():
        match = re.search(r"\|\s*\*?\s*(\d+)\s+-\s+(.+)$", line)
        if not match:
            continue

        item_id = int(match.group(1))
        title = clean_playlist_title(match.group(2))

        if title in {"Playlist", "Media Library"}:
            continue

        items.append((item_id, title))

    return items


def find_playlist_item(items, path, used_ids):
    if not path:
        return None

    target = Path(path).name

    for item_id, title in items:
        if item_id in used_ids:
            continue
        if title == target:
            return item_id

    return None


def goto_config_media(kind):
    cfg = video_load_config()
    raw = vlc_read("playlist")
    items = parse_playlist_items(raw)
    used_ids = set()

    idle_id = find_playlist_item(items, cfg.get("idle"), used_ids)
    if idle_id is not None:
        used_ids.add(idle_id)

    video_id = find_playlist_item(items, cfg.get("video"), used_ids)

    if idle_id is None and items:
        idle_id = items[0][0]

    if video_id is None:
        if len(items) >= 2:
            video_id = items[1][0]
        else:
            video_id = idle_id

    item_id = video_id if kind == "video" else idle_id

    if item_id is None:
        log(f"VIDEOS cannot switch to {kind}: no VLC playlist item")
        return False

    ok = vlc_command(f"goto {item_id}")
    if ok:
        vlc_command("play")
        log(f"VIDEOS switched to {kind} item {item_id}")
    return ok


def register_video_routes(app, render_page):

    @app.route("/videos")
    @module_required(MODULE["key"])
    def videos_page():
        return render_page(
            "videos.html",
            active_page="videos",
            video_cfg=video_load_config(),
            video_files=video_media_files(),
        )

    @app.route("/videos/upload", methods=["POST"])
    @module_required(MODULE["key"])
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
    @module_required(MODULE["key"])
    def videos_save():
        cfg = video_load_config()

        cfg["id"] = request.form.get("id", cfg.get("id", "video1")).strip()
        cfg["name"] = request.form.get("name", cfg.get("name", "Video 1")).strip()
        cfg["gpio"] = safe_int(request.form.get("gpio", cfg.get("gpio", 17)), 17, 0, 40)
        cfg["video"] = request.form.get("video", "").strip()
        cfg["idle"] = request.form.get("idle", "").strip()
        cfg["active_low"] = request.form.get("active_low") == "on"
        cfg["pullup"] = request.form.get("pullup") == "on"
        cfg["sensor2_enabled"] = request.form.get("sensor2_enabled") == "on"
        cfg["sensor2_gpio_pin"] = int(request.form.get("sensor2_gpio_pin", 27))
        cfg["sensor2_active_low"] = request.form.get("sensor2_active_low") == "on"
        cfg["sensor2_pull_up"] = request.form.get("sensor2_pull_up") == "on"
        cfg["active_threshold"] = float(request.form.get("active_threshold", 0.3))
        cfg["idle_threshold"] = float(request.form.get("idle_threshold", 2.0))
        cfg["audio_device"] = request.form.get(
            "audio_device",
            cfg.get("audio_device", "hdmi:CARD=vc4hdmi,DEV=0"),
        ).strip()
        cfg["active_lock_seconds"] = safe_int(
            request.form.get("active_lock_seconds", cfg.get("active_lock_seconds", 10)),
            10,
            0,
            300,
        )
        cfg["cec_enabled"] = request.form.get("cec_enabled") == "on"
        cfg["cec_boot_enabled"] = request.form.get("cec_boot_enabled") == "on"
        cfg["cec_boot_delay"] = safe_int(
            request.form.get("cec_boot_delay", cfg.get("cec_boot_delay", 60)),
            60,
            0,
            300,
        )
        cfg["cec_boot_select_source"] = request.form.get("cec_boot_select_source") == "on"

        video_save_config(cfg)
        log("VIDEOS config saved")
        restart_video_service()

        return redirect("/videos")

    @app.route("/videos/restart", methods=["POST"])
    @module_required(MODULE["key"])
    def videos_restart():
        log("VIDEOS restart requested")
        restart_video_service()
        return redirect("/videos")

    @app.route("/videos/delete", methods=["POST"])
    @module_required(MODULE["key"])
    def videos_delete():
        path = request.form.get("path", "").strip()

        real_path = os.path.realpath(path)
        real_media_dir = os.path.realpath(VIDEO_MEDIA_DIR)

        if not real_path.startswith(real_media_dir + os.sep) and real_path != real_media_dir:
            log(f"VIDEOS delete rejected: {path}")
            return redirect("/videos")

        try:
            if os.path.isfile(real_path):
                os.remove(real_path)
                log(f"VIDEOS deleted: {real_path}")
        except Exception as exc:
            log(f"VIDEOS delete error: {exc}")

        return redirect("/videos")

    @app.route("/videos/play", methods=["POST"])
    @module_required(MODULE["key"])
    def videos_play():
        log("VIDEOS play main requested")
        if not goto_config_media("video"):
            restart_video_service()
        return redirect("/videos")

    @app.route("/videos/idle", methods=["POST"])
    @module_required(MODULE["key"])
    def videos_idle():
        log("VIDEOS show idle requested")
        if not goto_config_media("idle"):
            restart_video_service()
        return redirect("/videos")

    @app.route("/videos/tv-on", methods=["POST"])
    @module_required(MODULE["key"])
    def videos_tv_on():
        log("VIDEOS TV ON requested but HDMI CEC is disabled in this build")
        return redirect("/videos")

    @app.route("/videos/tv-hdmi", methods=["POST"])
    @module_required(MODULE["key"])
    def videos_tv_hdmi():
        log("VIDEOS TV HDMI requested but HDMI CEC is disabled in this build")
        return redirect("/videos")
