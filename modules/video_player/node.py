import json
import re
import socket
import subprocess
import time
import os
from pathlib import Path

from gpiozero import DigitalInputDevice
import shutil

CONFIG_PATH = "/opt/showcontroller/config/video.json"
EXAMPLE_PATH = "/opt/showcontroller/config/video.example.json"
if not os.path.exists(CONFIG_PATH) and os.path.exists(EXAMPLE_PATH):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    shutil.copy(EXAMPLE_PATH, CONFIG_PATH)
VLC_HOST = "127.0.0.1"
VLC_PORT = 4212


DEFAULT_CONFIG = {
    "id": "video1",
    "name": "Video 1",

    "gpio": 17,
    "active_low": False,
    "pullup": True,

    "sensor2_enabled": False,
    "sensor2_gpio": 27,
    "sensor2_active_low": False,
    "sensor2_pullup": True,

    "video": "/home/raspberry/videos/example.mp4",
    "idle": "/home/raspberry/videos/idle.mp4",
    "audio_device": "hdmi:CARD=vc4hdmi,DEV=0",

    "active_threshold": 0.3,
    "idle_threshold": 2.0,
    "active_lock_seconds": 10,
}


def load_config():
    try:
        path = Path(CONFIG_PATH)

        if not path.exists() or path.stat().st_size == 0:
            print(
                "[video-node] Config missing or empty, using defaults",
                flush=True,
            )
            return DEFAULT_CONFIG.copy()

        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        final = DEFAULT_CONFIG.copy()
        final.update(cfg)
        return final

    except Exception as e:
        print(
            f"[video-node] Config error: {e}. Using defaults.",
            flush=True,
        )
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
PULL_UP = bool(
    config.get(
        "pullup",
        config.get("pull_up", True),
    )
)

SENSOR2_ENABLED = bool(config.get("sensor2_enabled", False))
SENSOR2_GPIO = int(config.get("sensor2_gpio", 27))
SENSOR2_ACTIVE_LOW = bool(
    config.get("sensor2_active_low", False)
)
SENSOR2_PULL_UP = bool(
    config.get("sensor2_pullup", True)
)

VIDEO_PATH = config["video"]
IDLE_PATH = config.get("idle")

AUDIO_DEVICE = config.get(
    "audio_device",
    "hdmi:CARD=vc4hdmi,DEV=0",
)

ACTIVE_THRESHOLD = max(
    0.0,
    as_float(
        config.get("active_threshold", 0.3),
        0.3,
    ),
)

IDLE_THRESHOLD = max(
    0.0,
    as_float(
        config.get("idle_threshold", 2.0),
        2.0,
    ),
)

ACTIVE_LOCK_SECONDS = max(
    0.0,
    as_float(
        config.get("active_lock_seconds", 10),
        10,
    ),
)


current_mode = None
vlc_process = None

idle_item_id = None
video_item_id = None

last_active_started_at = 0.0

active_since = None
idle_since = None


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
        "--extraintf",
        "rc",
        "--rc-host",
        f"{VLC_HOST}:{VLC_PORT}",
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
        with socket.create_connection(
            (VLC_HOST, VLC_PORT),
            timeout=1,
        ) as sock:

            sock.settimeout(timeout)
            sock.sendall(
                (command + "\n").encode("utf-8")
            )

            chunks = []

            while True:
                try:
                    chunk = sock.recv(4096)

                except socket.timeout:
                    break

                if not chunk:
                    break

                chunks.append(
                    chunk.decode(
                        "utf-8",
                        errors="replace",
                    )
                )

            return "".join(chunks)

    except Exception as e:
        if log_errors:
            log(f"VLC RC error: {e}")

        return None


def vlc_command(command, log_errors=True):
    response = vlc_read(
        command,
        log_errors=log_errors,
        timeout=0.2,
    )

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
        match = re.search(
            r"\|\s*\*?\s*(\d+)\s+-\s+(.+)$",
            line,
        )

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
    global idle_item_id
    global video_item_id

    raw = vlc_read(
        "playlist",
        log_errors=False,
        timeout=0.8,
    )

    items = parse_playlist_items(raw)
    used_ids = set()

    idle_item_id = find_playlist_item(
        items,
        IDLE_PATH,
        used_ids,
    )

    if idle_item_id is not None:
        used_ids.add(idle_item_id)

    video_item_id = find_playlist_item(
        items,
        VIDEO_PATH,
        used_ids,
    )

    if idle_item_id is None and items:
        idle_item_id = items[0][0]

    if video_item_id is None:
        if len(items) >= 2:
            video_item_id = items[1][0]
        else:
            video_item_id = idle_item_id

    log(
        f"VLC playlist: "
        f"idle={idle_item_id}, "
        f"video={video_item_id}"
    )


def select_playlist_item(item_id):
    if item_id is None:
        log(
            "Cannot switch playlist item: "
            "no VLC item id"
        )
        return

    if not vlc_command(f"goto {item_id}"):
        log(
            f"Cannot switch to playlist item "
            f"{item_id}"
        )
        return

    vlc_command(
        "play",
        log_errors=False,
    )


def set_idle():
    global current_mode
    global idle_since

    if current_mode == "idle":
        return

    current_mode = "idle"
    idle_since = None

    log("Mode: IDLE")
    select_playlist_item(idle_item_id)


def set_active():
    global current_mode
    global last_active_started_at
    global active_since

    if current_mode == "active":
        return

    current_mode = "active"
    last_active_started_at = time.monotonic()
    active_since = None

    log("Mode: ACTIVE")
    select_playlist_item(video_item_id)


def sensor_is_active(sensor, active_low):
    value = sensor.value

    if active_low:
        return value == 0

    return value == 1


def any_sensor_active():
    if sensor_is_active(sensor1, ACTIVE_LOW):
        return True

    if SENSOR2_ENABLED and sensor_is_active(
        sensor2,
        SENSOR2_ACTIVE_LOW,
    ):
        return True

    return False


log(f"Starting {NODE_NAME}")

log(f"GPIO: {GPIO_PIN}")
log(f"Active low: {ACTIVE_LOW}")
log(f"Pull up: {PULL_UP}")

log(f"Sensor 2 enabled: {SENSOR2_ENABLED}")

if SENSOR2_ENABLED:
    log(f"Sensor 2 GPIO: {SENSOR2_GPIO}")
    log(
        f"Sensor 2 active low: "
        f"{SENSOR2_ACTIVE_LOW}"
    )
    log(
        f"Sensor 2 pull up: "
        f"{SENSOR2_PULL_UP}"
    )

log(f"Audio device: {AUDIO_DEVICE}")
log(f"Video: {VIDEO_PATH}")
log(f"Idle: {IDLE_PATH}")

log(
    f"Active threshold: "
    f"{ACTIVE_THRESHOLD}s"
)

log(
    f"Idle threshold: "
    f"{IDLE_THRESHOLD}s"
)

log(
    f"Active lock: "
    f"{ACTIVE_LOCK_SECONDS}s"
)


# Create GPIO sensors before starting VLC.
# This prevents VLC from starting if GPIO initialization
# itself fails.
sensor1 = DigitalInputDevice(
    GPIO_PIN,
    pull_up=PULL_UP,
)

sensor2 = None

if SENSOR2_ENABLED:
    sensor2 = DigitalInputDevice(
        SENSOR2_GPIO,
        pull_up=SENSOR2_PULL_UP,
    )


start_vlc()
set_idle()


try:
    while True:
        now = time.monotonic()

        sensor_active = any_sensor_active()

        if sensor_active:
            idle_since = None

            if current_mode != "active":
                if active_since is None:
                    active_since = now

                elif (
                    now - active_since
                    >= ACTIVE_THRESHOLD
                ):
                    set_active()

        else:
            active_since = None

            if current_mode == "active":

                active_age = (
                    now - last_active_started_at
                )

                if (
                    active_age
                    < ACTIVE_LOCK_SECONDS
                ):
                    idle_since = None

                else:
                    if idle_since is None:
                        idle_since = now

                    elif (
                        now - idle_since
                        >= IDLE_THRESHOLD
                    ):
                        set_idle()

            else:
                idle_since = None

        time.sleep(0.05)


finally:
    if sensor1:
        sensor1.close()

    if sensor2:
        sensor2.close()

    stop_vlc()
