import os
import subprocess

from services.installer import apt_install, missing_apt_packages


APT_PACKAGES = [
    "vlc",
    "cec-utils",
]

BOOT_CEC_SERVICE = "showcontroller-tv-boot-cec.service"
BOOT_CEC_MARKER = "/opt/showcontroller/config/video_deps_installed"


def status():
    missing = missing_apt_packages(APT_PACKAGES)

    return {
        "packages": APT_PACKAGES,
        "missing": missing,
        "ok": len(missing) == 0,
    }


def enable_boot_cec_service():
    os.makedirs(os.path.dirname(BOOT_CEC_MARKER), exist_ok=True)

    with open(BOOT_CEC_MARKER, "w", encoding="utf-8") as f:
        f.write("installed via /system module dependencies\n")

    subprocess.run(
        ["systemctl", "daemon-reload"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    result = subprocess.run(
        ["systemctl", "enable", BOOT_CEC_SERVICE],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Failed to enable TV boot CEC service")


def install():
    installed = apt_install(APT_PACKAGES)
    enable_boot_cec_service()

    return {
        "installed": installed,
        "message": "Video dependencies installed. TV boot CEC enabled for next Raspberry boot.",
    }
