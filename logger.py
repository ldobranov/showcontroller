import datetime
import os

LOG_FILE = "/opt/showcontroller/events.log"

def log(message):
    try:
        from config import load_config
        cfg = load_config()
        if cfg.get("logging_enabled", True) is False:
            return
    except:
        pass

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ts} {message}\n")

def get_logs(limit=30):
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return f.read().splitlines()[-limit:]

def clear_logs():
    open(LOG_FILE, "w", encoding="utf-8").close()
    log("LOG cleared")
