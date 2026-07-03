import subprocess
import time


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


def systemctl(args, timeout=20):
    return subprocess.run(
        ["sudo", "systemctl"] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def start_service(service):
    return systemctl(["start", service])


def stop_service(service):
    result = systemctl(["stop", service], timeout=20)

    for _ in range(20):
        if service_status(service) != "active":
            return result
        time.sleep(0.25)

    return result


def restart_service(service):
    subprocess.run(
        ["sudo", "systemctl", "restart", service],
        capture_output=True,
        text=True,
        timeout=30,
    )

    for _ in range(40):
        if service_status(service) == "active":
            return
        time.sleep(0.25)


def reboot_system():
    subprocess.Popen(["sudo", "reboot"])


def enable_service(service):
    systemctl(["enable", service])
    return start_service(service)


def disable_service(service):
    stop_service(service)
    return systemctl(["disable", service])


def kill_process(pattern):
    subprocess.run(
        ["sudo", "pkill", "-9", "-f", pattern],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
