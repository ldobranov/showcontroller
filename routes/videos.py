import json
import os
import subprocess
from pathlib import Path

from flask import redirect, request
from werkzeug.utils import secure_filename

from logger import log


VIDEO_CONFIG = "/opt/showcontroller/config/video.json"
VIDEO_MEDIA_DIR = "/home/raspberry/videos"
ALLOWED_VIDEO_EXT = {".mp4", ".jpg", ".jpeg"}


def video_default_config():
    return {
        "id": "video1",
        "name": "Video 1",
        "gpio": 17,
        "video": "/home/raspberry/videos/video1.mp4",
        "idle": "/home/raspberry/videos/idle.jpg",
        "cec_enabled": True,
        "active_low": False,
        "audio_device": "hdmi:CARD=vc4hdmi,DEV=0"
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


def register_video_routes(app, render_page):
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

        cfg["id"] = request.form.get("id", cfg.get("id", "video1")).strip()
        cfg["name"] = request.form.get("name", cfg.get("name", "Video 1")).strip()
        cfg["gpio"] = int(request.form.get("gpio", "17") or 17)
        cfg["video"] = request.form.get("video", "").strip()
        cfg["idle"] = request.form.get("idle", "").strip()
        cfg["active_low"] = request.form.get("active_low") == "on"
        cfg["cec_enabled"] = request.form.get("cec_enabled") == "on"
        cfg["audio_device"] = request.form.get("audio_device",cfg.get("audio_device", "hdmi:CARD=vc4hdmi,DEV=0")).strip()

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
        except Exception as exc:
            log(f"VIDEOS delete error: {exc}")

        return redirect("/videos")

    @app.route("/videos/play", methods=["POST"])
    def videos_play():
        log("VIDEOS play main requested")
        restart_video_service()
        return redirect("/videos")

    @app.route("/videos/idle", methods=["POST"])
    def videos_idle():
        log("VIDEOS show idle requested")
        restart_video_service()
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
