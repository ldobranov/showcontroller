import subprocess


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


def restart_service(service):
    subprocess.Popen(["sudo", "systemctl", "restart", service])


def reboot_system():
    subprocess.Popen(["sudo", "reboot"])


def enable_service(service):
    subprocess.run(["sudo", "systemctl", "enable", "--now", service])


def disable_service(service):
    subprocess.run(["sudo", "systemctl", "disable", "--now", service])
