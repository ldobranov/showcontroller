import json
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
    "video": "/home/raspberry/videos/example.mp4",
    "idle": "/home/raspberry/videos/idle.jpg",
    "cec_enabled": False,
    "audio_device": "hdmi:CARD=vc4hdmi,DEV=0",
}


def load_config():
    try:
        if not Path(CONFIG_PATH).exists() or Path(CONFIG_PATH).stat().st_size == 0:
            print("[video-node] Config missing or empty, using defaults", flush=True)
            return DEFAULT_CONFIG.copy()

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        final = DEFAULT_CONFIG.copy()
        final.update(cfg)
        return final

    except Exception as e:
        print(f"[video-node] Config error: {e}. Using defaults.", flush=True)
        return DEFAULT_CONFIG.copy()


config = load_config()

NODE_ID = config["id"]
NODE_NAME = config["name"]
GPIO_PIN = config["gpio"]
ACTIVE_LOW = config.get("active_low", False)
VIDEO_PATH = config["video"]
IDLE_PATH = config.get("idle")
CEC_ENABLED = config.get("cec_enabled", False)
AUDIO_DEVICE = config.get("audio_device", "hdmi:CARD=vc4hdmi,DEV=0")

current_mode = None
vlc_process = None


def log(message):
    print(f"[{NODE_ID}] {message}", flush=True)


def tv_on():
    if not CEC_ENABLED:
        return

    subprocess.run('echo "on 0" | cec-client -s -d 1', shell=True)
    time.sleep(2)
    subprocess.run('echo "as" | cec-client -s -d 1', shell=True)


def start_vlc():
    global vlc_process

    first_file = IDLE_PATH if IDLE_PATH and Path(IDLE_PATH).exists() else VIDEO_PATH

    cmd = [
        "cvlc",
        "--fullscreen",
        "--no-video-title-show",
        "--loop",
        "--quiet",
        "--aout=alsa",
        f"--alsa-audio-device={AUDIO_DEVICE}",
        "--extraintf", "rc",
        "--rc-host", f"{VLC_HOST}:{VLC_PORT}",
        first_file,
    ]

    log("Starting persistent VLC")
    vlc_process = subprocess.Popen(cmd)

    for _ in range(50):
        if vlc_command("status", log_errors=False):
            log("VLC RC ready")
            return
        time.sleep(0.1)

    log("VLC RC not ready")


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


def vlc_command(command, log_errors=True):
    try:
        with socket.create_connection((VLC_HOST, VLC_PORT), timeout=1) as sock:
            sock.sendall((command + "\n").encode("utf-8"))
        return True
    except Exception as e:
        if log_errors:
            log(f"VLC RC error: {e}")
        return False


def load_file(path):
    if not path or not Path(path).exists():
        log(f"File not found: {path}")
        return

    safe_path = str(Path(path))

    vlc_command("stop")
    vlc_command("clear")
    vlc_command(f"add {safe_path}")
    vlc_command("play")


def set_idle():
    global current_mode

    if current_mode == "idle":
        return

    current_mode = "idle"
    log("Mode: IDLE")
    load_file(IDLE_PATH)


def set_active():
    global current_mode

    if current_mode == "active":
        return

    current_mode = "active"
    log("Mode: ACTIVE")
    load_file(VIDEO_PATH)


log(f"Starting {NODE_NAME}")
log(f"GPIO: {GPIO_PIN}")
log(f"Active low: {ACTIVE_LOW}")
log(f"Audio device: {AUDIO_DEVICE}")
log(f"Video: {VIDEO_PATH}")
log(f"Idle: {IDLE_PATH}")

tv_on()
start_vlc()

sensor = DigitalInputDevice(GPIO_PIN, pull_up=False)

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
            set_idle()

        time.sleep(0.05)

finally:
    stop_vlc()
