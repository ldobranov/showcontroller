import json
import subprocess

REPO_DIR = "/home/raspberry/showcontroller"
INSTALLED_VERSION_FILE = "/opt/showcontroller/version.json"

_last_update_status = {
    "message": "",
    "version": "",
    "installed": "",
    "remote": "",
    "update_available": False,
}


def set_last_update_status(status):
    global _last_update_status
    _last_update_status = dict(status)


def get_last_update_status():
    return dict(_last_update_status)


def run_git(args):
    result = subprocess.run(
        ["git"] + args,
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_installed_version():
    try:
        with open(INSTALLED_VERSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {
            "version": data.get("version", "unknown"),
            "commit": data.get("commit", ""),
            "installed_at": data.get("installed_at", ""),
        }
    except Exception:
        return {
            "version": "unknown",
            "commit": "",
            "installed_at": "",
        }


def check_for_updates():
    installed = get_installed_version()

    code_fetch, fetch_out, fetch_err = run_git(["fetch", "origin"])
    if code_fetch != 0:
        result = {
            "ok": False,
            "message": f"Fetch failed: {fetch_err or fetch_out}",
            "version": installed.get("version", "unknown"),
            "installed": installed.get("commit", ""),
            "remote": "",
            "update_available": False,
        }
        set_last_update_status(result)
        return result

    code_remote, remote, remote_err = run_git(["rev-parse", "--short", "origin/main"])
    if code_remote != 0:
        result = {
            "ok": False,
            "message": f"Remote revision failed: {remote_err or remote}",
            "version": installed.get("version", "unknown"),
            "installed": installed.get("commit", ""),
            "remote": "",
            "update_available": False,
        }
        set_last_update_status(result)
        return result

    installed_commit = installed.get("commit", "")
    update_available = installed_commit != remote

    result = {
        "ok": True,
        "version": installed.get("version", "unknown"),
        "installed": installed_commit,
        "remote": remote,
        "update_available": update_available,
        "message": "Update available" if update_available else "Already up to date",
    }

    set_last_update_status(result)
    return result


def install_update():
    result = {
        "ok": True,
        "message": "Update started. The web interface will restart shortly.",
        "version": "",
        "installed": "",
        "remote": "",
        "update_available": False,
    }
    set_last_update_status(result)

    code_fetch, fetch_out, fetch_err = run_git(["fetch", "origin"])
    if code_fetch != 0:
        message = f"Fetch failed: {fetch_err or fetch_out}"
        set_last_update_status({**result, "ok": False, "message": message})
        return False, message

    code_reset, reset_out, reset_err = run_git(["reset", "--hard", "origin/main"])
    if code_reset != 0:
        message = f"Reset failed: {reset_err or reset_out}"
        set_last_update_status({**result, "ok": False, "message": message})
        return False, message

    subprocess.Popen(
        ["sudo", "./update.sh"],
        cwd=REPO_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return True, result["message"]
