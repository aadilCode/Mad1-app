from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db
from helpers import get_current_user

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")


@staff_bp.route("/pending")
def pending():
    return render_template("staff_pending.html")


@staff_bp.route("/dashboard")
def dashboard():
    user = get_current_user()
    if user is None or user["role"] != "staff":
        flash("Staff access only.", "danger")
        return redirect(url_for("auth.login"))
    if user["status"] == "pending":
        return redirect(url_for("staff.pending"))

    conn = get_db()
    treks = conn.execute("SELECT * FROM treks WHERE staff_id = ? ORDER BY start_date", (user["id"],)).fetchall()
    conn.close()
    return render_template("staff_dashboard.html", treks=treks)


@staff_bp.route("/trek/<int:trek_id>", methods=["GET", "POST"])
def trek_detail(trek_id):
    user = get_current_user()
    if user is None or user["role"] != "staff":
        flash("Staff access only.", "danger")
        return redirect(url_for("auth.login"))

    conn = get_db()
    trek = conn.execute("SELECT * FROM treks WHERE id = ?", (trek_id,)).fetchone()

    # Make sure this staff member is actually assigned to this trek
    if trek is None or trek["staff_id"] != user["id"]:
        conn.close()
        flash("You are not assigned to this trek.", "danger")
        return redirect(url_for("staff.dashboard"))

    if request.method == "POST":
        new_status = request.form["status"]
        available_slots = int(request.form["available_slots"])
        conn.execute(
            "UPDATE treks SET status = ?, available_slots = ? WHERE id = ?",
            (new_status, available_slots, trek_id)
        )
        conn.commit()
        flash("Trek updated.", "success")
        trek = conn.execute("SELECT * FROM treks WHERE id = ?", (trek_id,)).fetchone()

    participants = conn.execute("""
        SELECT bookings.*, users.name AS user_name, users.email AS user_email
        FROM bookings JOIN users ON bookings.user_id = users.id
        WHERE bookings.trek_id = ?
    """, (trek_id,)).fetchall()
    conn.close()

    return render_template("staff_trek_detail.html", trek=trek, participants=participants)
