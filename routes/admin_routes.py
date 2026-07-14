from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db
from helpers import get_current_user


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

VALID_DIFFICULTIES = ("Easy", "Moderate", "Hard")
VALID_TREK_STATUSES = ("Pending", "Approved", "Open", "Closed", "Completed")

def admin_required():
    
    user = get_current_user()
    if user is None or user["role"] != "admin":
        flash("Admin access only.","danger")
        return redirect(url_for("auth.login"))
    return None


def validate_trek_form(form):
    values = {
        "name":form.get("name","").strip(),
        "location":form.get("location","").strip(),
        "dificulty":form.get("dificulty","").strip(),
        "duration":form.get("duration","").strip(),
        "total_slots":form.get("total_slots","").strip(),
        "start_date":form.get("start_date","").strip(),
        "end_date":form.get("end_date","").strip(),
        "description":form.get("description").strip(),
        "staff_id": form.get("staff_id", "").strip(),
        "status": form.get("status", "").strip(),
    }
    errors = []

    if not values["name"]:
        errors.append("Trek name is required.")
    if not values["locations"]:
        errors.append("Location is required")

    if values["difficulty"] not in VALID_DIFFICULTIES:
        errors.append("please choose a vaild difficulty")

    if not values["duration"].isdigit() or int(values["duration"]) <= 0:
        errors.append("Duration must be a whole number greater than 0.")
    if not values["total_slots"].isdigit() or int(values["total_slots"]) <= 0:
        errors.append("Total slots must be a whole number greater than 0.")

    if not values["start_date"] or not values["end_date"]:
        errors.append("start date and end date both are required") 

    if values["staff_id"] and not values["staff_id"].isdigit():
        errors.append("Invalid staff selection.")

    return values, errors

@admin_bp.route("/dashboard")
def dashboard():
    redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_db()
    total_treks = conn.execute("SELECT COUNT(*) FROM treks").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users WHERE role='trekers'").fetchone()[0]
    total_staff = conn.execute("SELECT COUNT(*) FROM users WHERE role='staff'").fetchone()[0]
    total_booking = conn.execute("SELECT COUNT(*) FROM booking").fetchone()[0]
    pending_staff = conn.execute(
    "SELECT COUNT(*) FROM users WHERE role = 'staff' AND status = 'pending'").fetchone()[0]
    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_treks = total_treks, total_staff = total_staff,total_users= total_users,total_booking= total_booking,pending_staff= pending_staff
    )

# ---------------- Treks ----------------

@admin_bp.route("/treks")
def treks():
    redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_db()
    all_treks = conn.execute("""
        SELECT treks.*, users.name AS staff_name
        FROM treks LEFT JOIN users ON treks.staff_id = users.id
        ORDER BY treks.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin_treks.html", treks=all_treks)


@admin_bp.route("/treks/add", methods=["GET", "POST"])
def add_trek():
    redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_db()
    staff_list = conn.execute(
        "SELECT id, name FROM users WHERE role = 'staff' AND status = 'active'"
    ).fetchall()

    if request.method == "POST":
        values, errors = validate_trek_form(request.form)

        if errors:
            for message in errors:
                flash(message, "danger")
            conn.close()
            # Re-show the form with everything the admin already typed, so
            # they only need to fix the one thing that was wrong.
            return render_template(
                "admin_trek_form.html", trek=values, staff_list=staff_list, is_edit=False
            )

        duration = int(values["duration"])
        total_slots = int(values["total_slots"])
        staff_id = int(values["staff_id"]) if values["staff_id"] else None

        # If a staff member is assigned, mark trek as Approved, otherwise it stays Pending
        status = "Approved" if staff_id else "Pending"

        conn.execute("""
            INSERT INTO treks (name, location, difficulty, duration, total_slots, available_slots, staff_id, status, start_date, end_date, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, 
            (values["name"], values["location"], values["difficulty"], duration, total_slots,total_slots, staff_id, status, values["start_date"], values["end_date"],values["description"]))
        conn.commit()
        conn.close()
        flash("Trek added successfully!", "success")
        return redirect(url_for("admin.treks"))

    conn.close()
    return render_template("admin_trek_form.html", trek=None, staff_list=staff_list, is_edit=False)


@admin_bp.route("/treks/edit/<int:trek_id>", methods=["GET", "POST"])
def edit_trek(trek_id):
    redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_db()
    trek = conn.execute("SELECT * FROM treks WHERE id = ?", (trek_id,)).fetchone()

    if trek is None:
        conn.close()
        flash("That trek no longer exists.", "danger")
        return redirect(url_for("admin.treks"))

    staff_list = conn.execute(
        "SELECT id, name FROM users WHERE role = 'staff' AND status = 'active'"
    ).fetchall()

    if request.method == "POST":
        values, errors = validate_trek_form(request.form)

        if errors:
            for message in errors:
                flash(message, "danger")
            conn.close()
            return render_template(
                "admin_trek_form.html", trek=values, staff_list=staff_list, is_edit=True
            )

        duration = int(values["duration"])
        total_slots = int(values["total_slots"])
        staff_id = int(values["staff_id"]) if values["staff_id"] else None
        status = values["status"] if values["status"] in VALID_TREK_STATUSES else trek["status"]

        # Keep available slots in sync with total slots and existing bookings
        booked = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE trek_id = ? AND status = 'Booked'", (trek_id,)
        ).fetchone()[0]
        available_slots = max(total_slots - booked, 0)

        conn.execute("""
            UPDATE treks SET name=?, location=?, difficulty=?, duration=?, total_slots=?,
                              available_slots=?, staff_id=?, status=?, start_date=?, end_date=?, description=?
            WHERE id=?
        """, (values["name"], values["location"], values["difficulty"], duration, total_slots,
              available_slots, staff_id, status, values["start_date"], values["end_date"],
              values["description"], trek_id))
        conn.commit()
        conn.close()
        flash("Trek updated successfully!", "success")
        return redirect(url_for("admin.treks"))

    conn.close()
    return render_template("admin_trek_form.html", trek=trek, staff_list=staff_list, is_edit=True)


@admin_bp.route("/treks/delete/<int:trek_id>", methods=["POST"])
def delete_trek(trek_id):
    redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_db()
    trek = conn.execute("SELECT id FROM treks WHERE id = ?", (trek_id,)).fetchone()
    if trek is None:
        conn.close()
        flash("That trek no longer exists.", "danger")
        return redirect(url_for("admin.treks"))

    conn.execute("DELETE FROM treks WHERE id = ?", (trek_id,))
    conn.commit()
    conn.close()
    flash("Trek deleted.", "info")
    return redirect(url_for("admin.treks"))


# ---------------- Staff ----------------

@admin_bp.route("/staff")
def staff_list():
    redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_db()
    staff = conn.execute("SELECT * FROM users WHERE role = 'staff' ORDER BY status, name").fetchall()
    conn.close()
    return render_template("admin_staff.html", staff=staff)


@admin_bp.route("/staff/approve/<int:staff_id>", methods=["POST"])
def approve_staff(staff_id):
    redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_db()
    staff_member = conn.execute(
        "SELECT id FROM users WHERE id = ? AND role = 'staff'", (staff_id,)
    ).fetchone()
    if staff_member is None:
        conn.close()
        flash("That staff account no longer exists.", "danger")
        return redirect(url_for("admin.staff_list"))

    conn.execute("UPDATE users SET status = 'active' WHERE id = ?", (staff_id,))
    conn.commit()
    conn.close()
    flash("Staff member approved.", "success")
    return redirect(url_for("admin.staff_list"))


@admin_bp.route("/staff/blacklist/<int:staff_id>", methods=["POST"])
def blacklist_staff(staff_id):
    redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_db()
    staff_member = conn.execute(
        "SELECT id FROM users WHERE id = ? AND role = 'staff'", (staff_id,)
    ).fetchone()
    if staff_member is None:
        conn.close()
        flash("That staff account no longer exists.", "danger")
        return redirect(url_for("admin.staff_list"))

    conn.execute("UPDATE users SET status = 'blacklisted' WHERE id = ?", (staff_id,))
    conn.commit()
    conn.close()
    flash("Staff member blacklisted.", "warning")
    return redirect(url_for("admin.staff_list"))


# ---------------- Users ----------------

@admin_bp.route("/users")
def users_list():
    redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_db()
    users = conn.execute("SELECT * FROM users WHERE role = 'trekker' ORDER BY name").fetchall()
    conn.close()
    return render_template("admin_users.html", users=users)


@admin_bp.route("/users/blacklist/<int:user_id>", methods=["POST"])
def blacklist_user(user_id):
    redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_db()
    target = conn.execute(
        "SELECT id FROM users WHERE id = ? AND role = 'trekker'", (user_id,)
    ).fetchone()
    if target is None:
        conn.close()
        flash("That user no longer exists.", "danger")
        return redirect(url_for("admin.users_list"))

    conn.execute("UPDATE users SET status = 'blacklisted' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash("User blacklisted.", "warning")
    return redirect(url_for("admin.users_list"))


# ---------------- Bookings ----------------

@admin_bp.route("/bookings")
def bookings():
    redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_db()
    all_bookings = conn.execute("""
        SELECT bookings.*, users.name AS user_name, treks.name AS trek_name
        FROM bookings
        JOIN users ON bookings.user_id = users.id
        JOIN treks ON bookings.trek_id = treks.id
        ORDER BY bookings.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin_bookings.html", bookings=all_bookings)


# ---------------- Search ----------------

@admin_bp.route("/search")
def search():
    redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    query = request.args.get("q", "").strip()
    found_treks, found_staff, found_users = [], [], []

    if query:
        conn = get_db()
        like = f"%{query}%"
        id_match = query if query.isdigit() else -1
        found_treks = conn.execute(
            "SELECT * FROM treks WHERE name LIKE ? OR location LIKE ? OR id = ?",
            (like, like, id_match)
        ).fetchall()
        found_staff = conn.execute(
            "SELECT * FROM users WHERE role='staff' AND (name LIKE ? OR email LIKE ? OR id = ?)",
            (like, like, id_match)
        ).fetchall()
        found_users = conn.execute(
            "SELECT * FROM users WHERE role='trekker' AND (name LIKE ? OR email LIKE ? OR id = ?)",
            (like, like, id_match)
        ).fetchall()
        conn.close()

    return render_template("admin_search.html", query=query, treks=found_treks, staff=found_staff, users=found_users)