import subprocess


def run(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    return result.returncode == 0, result.stdout, result.stderr

def package_installed(package):
    result = subprocess.run(
        ["dpkg-query", "-W", "-f=${Status}", package],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0 and "install ok installed" in result.stdout


def missing_apt_packages(packages):
    return [
        package for package in packages
        if not package_installed(package)
    ]


def apt_update():
    ok, _, err = run(["apt", "update"])

    if not ok:
        raise RuntimeError(err)

def apt_install(packages):
    missing = missing_apt_packages(packages)

    if not missing:
        return []

    apt_update()

    ok, _, err = run(["apt", "install", "-y", *missing])

    if not ok:
        raise RuntimeError(err)

    return missing
