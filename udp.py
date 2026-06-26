import socket
from config import load_config
from logger import log

def send_udp(message):
    cfg = load_config()
    ip = cfg["touchdesigner"]["ip"]
    port = int(cfg["touchdesigner"]["port"])

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message.encode("ascii"), (ip, port))
    sock.close()

    log(f"SEND {ip}:{port} -> {message}")
