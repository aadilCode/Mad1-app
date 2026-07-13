from flask import Flask, redirect, url_for
import config
from database import init_db
from helpers import get_current_user


from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.staff_routes import staff_bp
from routes.user_routes import user_bp

app = flask(__name__)
app.secret_key = config.SECRET_KEY

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(user_bp)



@app.context_processor

def inject_user():
    return {"current_user":get_current_user()}


@app_route("/")

def home():
    """sending the visitor to login or correct dashboard"""

    user = get_current_user()

    if user is None :
        return redirect(url_for("auth.login"))

    if user["role"] == "admin":
        return redirect(url_for("admin.dashboard"))

    if user["role"] == "staff":
        if user["status"] == "pending":
            return redirect(url_for("staff.pending"))
        return redirect(url_for("staff.dashboard"))
    return redirect(url_for("user.dashboard"))

    if name == " __main__":
        init_db()
        app.run(debug=True)