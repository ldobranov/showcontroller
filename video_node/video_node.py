import json
import os
import socket
import subprocess
import time
from pathlib import Path
from gpiozero import DigitalInputDevice

CONFIG_PATH = "/opt/showcontroller/config/video.json"
MPV_SOCKET = "/tmp/showcontroller-mpv.sock"

DEFAULT_CONFIG = {
    "id": "oko1",
    "name": "Око 1",
    "gpio": 17,
    "video": "/home/raspberry/videos/oko1.mp4",
    "idle": "/home/raspberry/videos/idle.jpg",
    "cec_enabled": False
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
VIDEO_PATH = config["video"]
IDLE_PATH = config.get("idle")
CEC_ENABLED = config.get("cec_enabled", False)

current_mode = None
mpv_process = None


def log(message):
    print(f"[{NODE_ID}] {message}", flush=True)


def tv_on():
    if not CEC_ENABLED:
        return

    subprocess.run('echo "on 0" | cec-client -s -d 1', shell=True)
    time.sleep(2)
    subprocess.run('echo "as" | cec-client -s -d 1', shell=True)


def start_mpv():
    global mpv_process

    try:
        os.remove(MPV_SOCKET)
    except FileNotFoundError:
        pass

    first_file = IDLE_PATH if IDLE_PATH and Path(IDLE_PATH).exists() else VIDEO_PATH

    cmd = [
        "mpv",
        "--fs",
        "--no-border",
        "--profile=fast",
        "--hwdec=auto",
        "--keep-open=yes",
        "--idle=yes",
        "--really-quiet",
        "--osd-level=0",
        "--force-window=yes",
        "--loop-file=inf",
        f"--input-ipc-server={MPV_SOCKET}",
        first_file
    ]

    log("Starting persistent mpv")
    mpv_process = subprocess.Popen(cmd)

    for _ in range(50):
        if os.path.exists(MPV_SOCKET):
            return
        time.sleep(0.1)

    log("MPV socket not ready")


def mpv_command(command):
    data = json.dumps(command) + "\n"

    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(MPV_SOCKET)
        client.send(data.encode("utf-8"))
        client.close()
    except Exception as e:
        log(f"MPV IPC error: {e}")


def load_file(path):
    if not path or not Path(path).exists():
        log(f"File not found: {path}")
        return

    mpv_command({
        "command": ["loadfile", path, "replace"]
    })

    mpv_command({
        "command": ["set_property", "loop-file", "inf"]
    })


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
log(f"Video: {VIDEO_PATH}")
log(f"Idle: {IDLE_PATH}")

tv_on()
start_mpv()

sensor = DigitalInputDevice(GPIO_PIN, pull_up=False)

set_idle()

while True:
    if mpv_process and mpv_process.poll() is not None:
        log("MPV crashed/exited, restarting")
        start_mpv()
        current_mode = None

    if sensor.value == 1:
        set_active()
    else:
        set_idle()

    time.sleep(0.1)
