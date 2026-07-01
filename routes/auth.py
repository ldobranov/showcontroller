from flask import redirect, render_template, request, session

import auth
from config import load_config
from logger import log


def register_auth_routes(app):
    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if auth.verify_login(username, password):
                auth.login_user(username)
                log(f"AUTH login success: {username}")
                return redirect(request.args.get("next") or "/")
            error = "Invalid username or password."
            log(f"AUTH login failed: {username}")

        return render_template("login.html", error=error, cfg=load_config())

    @app.route("/logout", methods=["POST", "GET"])
    def logout():
        username = session.get("username", "unknown")
        auth.logout_user()
        log(f"AUTH logout: {username}")
        return redirect("/login")

    @app.route("/settings/password", methods=["POST"])
    def change_password():
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if new_password != confirm_password:
            log("AUTH password change failed: confirmation mismatch")
            return redirect("/settings?password_error=confirm")

        ok, message = auth.change_password(current_password, new_password)
        log(f"AUTH password change: {message}")
        if ok:
            return redirect("/settings?password_changed=1")
        return redirect("/settings?password_error=invalid")
