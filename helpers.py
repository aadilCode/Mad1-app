from flask import session
from database import get_db

def get_current_user():
    if "user_id" not in session:
        return None

    conn = get_db()

    user = conn.execute("SELECT * FROM  users WHERE id = ?",(session ["user_id"],)).fetchone()

    conn.close()
    return user