import datetime
import fcntl
import os

LOG_FILE = "/opt/showcontroller/events.log"
ROTATED_LOG_FILE = LOG_FILE + ".1"
LOG_LOCK_FILE = LOG_FILE + ".lock"
MAX_LOG_BYTES = 100_000


def _lock_log():
    lock = open(LOG_LOCK_FILE, "a", encoding="utf-8")
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
    return lock


def _rotate_if_needed(next_line):
    current_size = os.path.getsize(LOG_FILE) if os.path.exists(LOG_FILE) else 0
    next_size = len(next_line.encode("utf-8"))

    if current_size and current_size + next_size > MAX_LOG_BYTES:
        os.replace(LOG_FILE, ROTATED_LOG_FILE)

def log(message):
    try:
        from config import load_config
        cfg = load_config()
        if cfg.get("logging_enabled", True) is False:
            return
    except Exception:
        pass

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {message}\n"
    lock = _lock_log()

    try:
        _rotate_if_needed(line)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    finally:
        lock.close()

def get_logs(limit=30):
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return f.read().splitlines()[-limit:]

def clear_logs():
    lock = _lock_log()

    try:
        open(LOG_FILE, "w", encoding="utf-8").close()
        try:
            os.remove(ROTATED_LOG_FILE)
        except FileNotFoundError:
            pass
    finally:
        lock.close()

    log("LOG cleared")
