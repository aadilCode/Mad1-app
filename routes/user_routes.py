from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db
from helpers import get_current_user

user_bp = Blueprint("user", __name__, url_prefix="/user")


@user_bp.route("/dashboard")
def dashboard():
    user = get_current_user()
    if user is None or user["role"] != "trekker":
        flash("Please log in as a trekker.", "danger")
        return redirect(url_for("auth.login"))

    conn = get_db()
    available_treks = conn.execute(
        "SELECT * FROM treks WHERE status = 'Open' AND available_slots > 0 LIMIT 5"
    ).fetchall()
    my_bookings = conn.execute("""
        SELECT bookings.*, treks.name AS trek_name, treks.location, treks.start_date, treks.end_date
        FROM bookings JOIN treks ON bookings.trek_id = treks.id
        WHERE bookings.user_id = ? ORDER BY bookings.id DESC LIMIT 5
    """, (user["id"],)).fetchall()
    conn.close()

    return render_template("user_dashboard.html", available_treks=available_treks, my_bookings=my_bookings)


@user_bp.route("/treks")
def treks():
    user = get_current_user()
    if user is None or user["role"] != "trekker":
        flash("Please log in as a trekker.", "danger")
        return redirect(url_for("auth.login"))

    location = request.args.get("location", "")
    difficulty = request.args.get("difficulty", "")

    conn = get_db()
    query = "SELECT * FROM treks WHERE status = 'Open'"
    params = []
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if difficulty:
        query += " AND difficulty = ?"
        params.append(difficulty)

    all_treks = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("user_trek.html", treks=all_treks, location=location, difficulty=difficulty)


@user_bp.route("/trek/<int:trek_id>")
def trek_detail(trek_id):
    user = get_current_user()
    if user is None or user["role"] != "trekker":
        flash("Please log in as a trekker.", "danger")
        return redirect(url_for("auth.login"))

    conn = get_db()
    trek = conn.execute("SELECT * FROM treks WHERE id = ?", (trek_id,)).fetchone()
    already_booked = conn.execute(
        "SELECT * FROM bookings WHERE user_id = ? AND trek_id = ? AND status = 'Booked'",
        (user["id"], trek_id)
    ).fetchone()
    conn.close()

    return render_template("user_trek_detail.html", trek=trek, already_booked=already_booked)


@user_bp.route("/book/<int:trek_id>", methods=["POST"])
def book_trek(trek_id):
    user = get_current_user()
    if user is None or user["role"] != "trekker":
        flash("Please log in as a trekker.", "danger")
        return redirect(url_for("auth.login"))

    conn = get_db()
    trek = conn.execute("SELECT * FROM treks WHERE id = ?", (trek_id,)).fetchone()

    if trek is None or trek["status"] != "Open":
        flash("This trek is not open for booking.", "danger")
    elif trek["available_slots"] <= 0:
        flash("Sorry, this trek is fully booked.", "danger")
    else:
        already_booked = conn.execute(
            "SELECT * FROM bookings WHERE user_id = ? AND trek_id = ? AND status = 'Booked'",
            (user["id"], trek_id)
        ).fetchone()
        if already_booked:
            flash("You already booked this trek.", "info")
        else:
            # Reduce available slots by 1 and create the booking
            conn.execute("UPDATE treks SET available_slots = available_slots - 1 WHERE id = ?", (trek_id,))
            conn.execute(
                "INSERT INTO bookings (user_id, trek_id, booking_date, status) VALUES (?, ?, ?, 'Booked')",
                (user["id"], trek_id, datetime.now().strftime("%Y-%m-%d %H:%M"))
            )
            conn.commit()
            flash("Trek booked successfully!", "success")

    conn.close()
    return redirect(url_for("user.trek_detail", trek_id=trek_id))


@user_bp.route("/bookings")
def bookings():
    user = get_current_user()
    if user is None or user["role"] != "trekker":
        flash("Please log in as a trekker.", "danger")
        return redirect(url_for("auth.login"))

    conn = get_db()
    all_bookings = conn.execute("""
        SELECT bookings.*, treks.name AS trek_name, treks.location, treks.start_date, treks.end_date
        FROM bookings JOIN treks ON bookings.trek_id = treks.id
        WHERE bookings.user_id = ? ORDER BY bookings.id DESC
    """, (user["id"],)).fetchall()
    conn.close()

    return render_template("user_booking.html", bookings=all_bookings)


@user_bp.route("/cancel/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):
    user = get_current_user()
    if user is None or user["role"] != "trekker":
        flash("Please log in as a trekker.", "danger")
        return redirect(url_for("auth.login"))

    conn = get_db()
    booking = conn.execute("SELECT * FROM bookings WHERE id = ? AND user_id = ?", (booking_id, user["id"])).fetchone()

    if booking and booking["status"] == "Booked":
        conn.execute("UPDATE bookings SET status = 'Cancelled' WHERE id = ?", (booking_id,))
        conn.execute("UPDATE treks SET available_slots = available_slots + 1 WHERE id = ?", (booking["trek_id"],))
        conn.commit()
        flash("Booking cancelled.", "info")

    conn.close()
    return redirect(url_for("user.bookings"))


@user_bp.route("/profile", methods=["GET", "POST"])
def profile():
    user = get_current_user()
    if user is None or user["role"] != "trekker":
        flash("Please log in as a trekker.", "danger")
        return redirect(url_for("auth.login"))

    conn = get_db()
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        conn.execute("UPDATE users SET name = ?, phone = ? WHERE id = ?", (name, phone, user["id"]))
        conn.commit()
        flash("Profile updated.", "success")
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()

    conn.close()
    return render_template("user_profile.html", user=user)
