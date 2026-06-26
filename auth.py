import json
import os
import secrets
from functools import wraps

from flask import redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

AUTH_FILE = "/opt/showcontroller/auth.json"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "showcontroller"


def _default_auth_data():
    return {
        "enabled": True,
        "username": DEFAULT_USERNAME,
        "password_hash": generate_password_hash(DEFAULT_PASSWORD),
        "default_password_active": True,
        "secret_key": secrets.token_hex(32),
    }


def load_auth():
    if not os.path.exists(AUTH_FILE):
        save_auth(_default_auth_data())

    with open(AUTH_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    changed = False
    if "enabled" not in data:
        data["enabled"] = True
        changed = True
    if "username" not in data:
        data["username"] = DEFAULT_USERNAME
        changed = True
    if "password_hash" not in data:
        data["password_hash"] = generate_password_hash(DEFAULT_PASSWORD)
        data["default_password_active"] = True
        changed = True
    if "secret_key" not in data:
        data["secret_key"] = secrets.token_hex(32)
        changed = True

    if changed:
        save_auth(data)

    return data


def save_auth(data):
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        os.chmod(AUTH_FILE, 0o600)
    except Exception:
        pass


def get_secret_key():
    return load_auth().get("secret_key")


def auth_enabled():
    return bool(load_auth().get("enabled", True))


def is_logged_in():
    if not auth_enabled():
        return True
    return bool(session.get("authenticated"))


def current_username():
    if not is_logged_in():
        return None
    return load_auth().get("username", DEFAULT_USERNAME)


def verify_login(username, password):
    data = load_auth()
    return (
        username == data.get("username", DEFAULT_USERNAME)
        and check_password_hash(data.get("password_hash", ""), password or "")
    )


def login_user(username):
    session.clear()
    session["authenticated"] = True
    session["username"] = username


def logout_user():
    session.clear()


def change_password(current_password, new_password):
    data = load_auth()

    if not check_password_hash(data.get("password_hash", ""), current_password or ""):
        return False, "Current password is incorrect."

    if not new_password or len(new_password) < 8:
        return False, "New password must be at least 8 characters."

    data["password_hash"] = generate_password_hash(new_password)
    data["default_password_active"] = False
    save_auth(data)
    return True, "Password changed."


def default_password_active():
    return bool(load_auth().get("default_password_active", False))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if is_logged_in():
            return view(*args, **kwargs)
        return redirect(url_for("login", next=request.path))

    return wrapped
