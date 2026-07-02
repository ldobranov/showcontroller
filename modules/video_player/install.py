from services.installer import apt_install, missing_apt_packages


APT_PACKAGES = [
    "vlc",
]


def status():
    missing = missing_apt_packages(APT_PACKAGES)

    return {
        "packages": APT_PACKAGES,
        "missing": missing,
        "ok": len(missing) == 0,
    }


def install():
    installed = apt_install(APT_PACKAGES)

    return {
        "installed": installed,
        "message": "Video dependencies installed.",
    }
