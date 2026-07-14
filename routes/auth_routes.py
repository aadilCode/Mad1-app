from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register",methods=["GET","POST"])

def register():
    if request.method == "POST":
        name = request.form["name"]
        email =  request.form["email"].lower().strip()
        phone = request.form["phone"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        role = request.form["role"]

        conn = get_db()

        if password != confirm_password:
            flash("Password do not match.","danger")
        elif len(password) < 6:
            flash("password must be at least 6 character.","danger")
        elif conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone():
            flash("An account with the same email already exists", "danger")

        else:
            status = "Pending" if role == "staff" else "active"

            conn.execute(
                "INSERT INTO users(name, email, phone, password, role, status) VALUES(?,?,?,?,?,?)",
                (name,email,phone,generate_password_hash(password),role,status)
            )
            conn.commit()
            conn.close()

            flash("your registration is successful please login with the same credentials","success")
            return redirect(url_for("auth.login"))
        conn.close()

    return render_template("register.html")



@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].lower().strip()
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user is None or not check_password_hash(user["password"], password):
            flash("Incorrect email or password.", "danger")
        elif user["status"] == "blacklisted":
            flash("Your account has been blacklisted. Contact the admin.", "danger")
        else:
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("home"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


