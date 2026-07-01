import auth
from flask import Flask, render_template, request, redirect, url_for
from config import load_config, get_version
from logger import log
from routes.auth import register_auth_routes
from routes.diagnostics import register_diagnostics_routes
from routes.main import register_main_routes
from routes.system import get_ip, get_status, register_system_routes
from routes.videos import register_video_routes


app = Flask(__name__)
app.secret_key = auth.get_secret_key()


def render_page(template_name, **context):
    cfg = load_config()
    return render_template(
        template_name,
        cfg=cfg,
        status=get_status(),
        ip=get_ip(),
        auth_user=auth.current_username(),
        auth_enabled=auth.auth_enabled(),
        default_password_active=auth.default_password_active(),
        password_changed=request.args.get("password_changed"),
        password_error=request.args.get("password_error"),
        **context,
        version=get_version(),
    )


register_auth_routes(app)
register_main_routes(app, render_page)
register_video_routes(app, render_page)
register_system_routes(app, render_page)
register_diagnostics_routes(app, render_page)

if __name__ == "__main__":
    log("WEB STARTED")

    cfg = load_config()
    app.run(host="0.0.0.0", port=80, threaded=True)

    log("WEB STOPPED")
