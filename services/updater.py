import json
import os
import subprocess


REPO_DIR = "/home/raspberry/showcontroller"
INSTALLED_VERSION_FILE = "/opt/showcontroller/version.json"
UPDATE_STATUS_FILE = "/opt/showcontroller/config/update_status.json"
GIT_USER = "raspberry"


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
    if _last_update_status.get("message"):
        return dict(_last_update_status)

    try:
        with open(UPDATE_STATUS_FILE, "r", encoding="utf-8") as f:
            persisted = json.load(f)
        if isinstance(persisted, dict):
            return {**_last_update_status, **persisted}
    except (OSError, ValueError):
        pass
    return dict(_last_update_status)


def start_safe_update(target):
    return subprocess.run(
        [
            "systemd-run",
            "--unit=showcontroller-update",
            "--collect",
            "--no-block",
            "/bin/bash",
            os.path.join(REPO_DIR, "scripts", "safe_update.sh"),
            target,
        ],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=10,
    )


def run_git(args):
    result = subprocess.run(
        ["sudo", "-u", GIT_USER, "git"] + args,
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

    code_target, target, target_err = run_git(["rev-parse", "origin/main"])
    if code_target != 0:
        message = f"Remote revision failed: {target_err or target}"
        set_last_update_status({**result, "ok": False, "message": message})
        return False, message

    code_head, head, head_err = run_git(["rev-parse", "HEAD"])
    if code_head != 0:
        message = f"Local revision failed: {head_err or head}"
        set_last_update_status({**result, "ok": False, "message": message})
        return False, message

    code_ancestor, _, ancestor_err = run_git(
        ["merge-base", "--is-ancestor", head, target]
    )
    if code_ancestor != 0:
        message = (
            "Update refused: origin/main is not a safe fast-forward update."
            + (f" {ancestor_err}" if ancestor_err else "")
        )
        set_last_update_status({**result, "ok": False, "message": message})
        return False, message

    try:
        os.makedirs(os.path.dirname(UPDATE_STATUS_FILE), exist_ok=True)
        with open(UPDATE_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump({**result, "target": target}, f, indent=2)
    except OSError:
        pass

    try:
        process = start_safe_update(target)
    except (OSError, subprocess.TimeoutExpired) as exc:
        message = f"Could not start update: {exc}"
        set_last_update_status({**result, "ok": False, "message": message})
        return False, message

    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip()
        message = f"Could not start update: {detail or 'systemd-run failed'}"
        set_last_update_status({**result, "ok": False, "message": message})
        return False, message

    return True, result["message"]
