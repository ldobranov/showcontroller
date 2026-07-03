import json
import re
import socket
import subprocess
import time
from pathlib import Path

from gpiozero import DigitalInputDevice


CONFIG_PATH = "/opt/showcontroller/config/video.json"
VLC_HOST = "127.0.0.1"
VLC_PORT = 4212

DEFAULT_CONFIG = {
    "id": "video1",
    "name": "Video 1",
    "gpio": 17,
    "active_low": False,
    "pullup": True,
    "video": "/home/raspberry/videos/example.mp4",
    "idle": "/home/raspberry/videos/idle.mp4",
    "audio_device": "hdmi:CARD=vc4hdmi,DEV=0",
    "active_lock_seconds": 10,
}


def load_config():
    try:
        path = Path(CONFIG_PATH)
        if not path.exists() or path.stat().st_size == 0:
            print("[video-node] Config missing or empty, using defaults", flush=True)
            return DEFAULT_CONFIG.copy()

        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        final = DEFAULT_CONFIG.copy()
        final.update(cfg)
        return final

    except Exception as e:
        print(f"[video-node] Config error: {e}. Using defaults.", flush=True)
        return DEFAULT_CONFIG.copy()


def as_float(value, default):
    try:
        return float(value)
    except Exception:
        return float(default)


config = load_config()

NODE_ID = config["id"]
NODE_NAME = config["name"]
GPIO_PIN = int(config["gpio"])
ACTIVE_LOW = bool(config.get("active_low", False))
# Accept both "pullup" (app-wide convention) and legacy "pull_up".
PULL_UP = bool(config.get("pullup", config.get("pull_up", True)))
VIDEO_PATH = config["video"]
IDLE_PATH = config.get("idle")
AUDIO_DEVICE = config.get("audio_device", "hdmi:CARD=vc4hdmi,DEV=0")
ACTIVE_LOCK_SECONDS = max(0.0, as_float(config.get("active_lock_seconds", 10), 10))

current_mode = None
vlc_process = None
idle_item_id = None
video_item_id = None
last_active_started_at = 0.0


def log(message):
    print(f"[{NODE_ID}] {message}", flush=True)


def build_playlist():
    playlist = []

    if IDLE_PATH and Path(IDLE_PATH).exists():
        playlist.append(IDLE_PATH)
    else:
        log("Idle media missing; using main video as idle fallback")
        playlist.append(VIDEO_PATH)

    if VIDEO_PATH and Path(VIDEO_PATH).exists():
        playlist.append(VIDEO_PATH)
    else:
        log("Main video missing")

    return playlist


def start_vlc():
    global vlc_process

    playlist = build_playlist()

    cmd = [
        "cvlc",
        "--fullscreen",
        "--no-video-title-show",
        "--quiet",
        "--repeat",
        "--aout=alsa",
        f"--alsa-audio-device={AUDIO_DEVICE}",
        "--extraintf", "rc",
        "--rc-host", f"{VLC_HOST}:{VLC_PORT}",
        *playlist,
    ]

    log("Starting persistent VLC")
    vlc_process = subprocess.Popen(cmd)

    for _ in range(50):
        if vlc_command("status", log_errors=False):
            log("VLC RC ready")
            break
        time.sleep(0.1)
    else:
        log("VLC RC not ready")

    refresh_playlist_ids()


def stop_vlc():
    global vlc_process

    if vlc_process and vlc_process.poll() is None:
        try:
            vlc_command("shutdown", log_errors=False)
            vlc_process.wait(timeout=2)
        except Exception:
            try:
                vlc_process.terminate()
                vlc_process.wait(timeout=2)
            except Exception:
                try:
                    vlc_process.kill()
                except Exception:
                    pass

    vlc_process = None


def vlc_read(command, log_errors=True, timeout=1.0):
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

    except Exception as e:
        if log_errors:
            log(f"VLC RC error: {e}")
        return None


def vlc_command(command, log_errors=True):
    response = vlc_read(command, log_errors=log_errors, timeout=0.2)
    return response is not None


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


def refresh_playlist_ids():
    global idle_item_id, video_item_id

    raw = vlc_read("playlist", log_errors=False, timeout=0.8)
    items = parse_playlist_items(raw)
    used_ids = set()

    idle_item_id = find_playlist_item(items, IDLE_PATH, used_ids)
    if idle_item_id is not None:
        used_ids.add(idle_item_id)

    video_item_id = find_playlist_item(items, VIDEO_PATH, used_ids)

    if idle_item_id is None and items:
        idle_item_id = items[0][0]

    if video_item_id is None:
        if len(items) >= 2:
            video_item_id = items[1][0]
        else:
            video_item_id = idle_item_id

    log(f"VLC playlist: idle={idle_item_id}, video={video_item_id}")


def select_playlist_item(item_id):
    if item_id is None:
        log("Cannot switch playlist item: no VLC item id")
        return

    if not vlc_command(f"goto {item_id}"):
        log(f"Cannot switch to playlist item {item_id}")
        return

    vlc_command("play", log_errors=False)


def set_idle():
    global current_mode

    if current_mode == "idle":
        return

    current_mode = "idle"
    log("Mode: IDLE")
    select_playlist_item(idle_item_id)


def set_active():
    global current_mode, last_active_started_at

    if current_mode == "active":
        return

    current_mode = "active"
    last_active_started_at = time.monotonic()
    log("Mode: ACTIVE")
    select_playlist_item(video_item_id)


log(f"Starting {NODE_NAME}")
log(f"GPIO: {GPIO_PIN}")
log(f"Active low: {ACTIVE_LOW}")
log(f"Pull up: {PULL_UP}")
log(f"Audio device: {AUDIO_DEVICE}")
log(f"Video: {VIDEO_PATH}")
log(f"Idle: {IDLE_PATH}")
log(f"Active lock: {ACTIVE_LOCK_SECONDS}s")

start_vlc()

sensor = DigitalInputDevice(GPIO_PIN, pull_up=PULL_UP)

set_idle()

try:
    while True:
        if vlc_process and vlc_process.poll() is not None:
            log("VLC crashed/exited, restarting")
            start_vlc()
            current_mode = None
            set_idle()

        sensor_active = (sensor.value == 0) if ACTIVE_LOW else (sensor.value == 1)

        if sensor_active:
            set_active()
        else:
            active_age = time.monotonic() - last_active_started_at

            if current_mode == "active" and active_age < ACTIVE_LOCK_SECONDS:
                pass
            else:
                set_idle()

        time.sleep(0.05)

finally:
    stop_vlc()
