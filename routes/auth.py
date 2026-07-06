from flask import Blueprint, request, session, jsonify
from config import get_connection
import hashlib

auth_bp = Blueprint("auth", __name__)

# ── Invite key (admin shares this with new employees) ──────────────────────
INVITE_KEY = "HRMS2024"   # Change this to whatever you like


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ── Registration ────────────────────────────────────────────────────────────
@auth_bp.route("/api/register", methods=["POST"])
def register():
    data       = request.get_json()
    username   = data.get("username",   "").strip().lower()
    password   = data.get("password",   "").strip()
    invite_key = data.get("invite_key", "").strip()
    first_name = data.get("first_name", "").strip()
    last_name  = data.get("last_name",  "").strip()
    dept_id    = data.get("dept_id")
    desig_id   = data.get("desig_id")

    # Validation
    if not all([username, password, invite_key, first_name, last_name, dept_id, desig_id]):
        return jsonify({"success": False, "message": "All fields are required."})
    if invite_key != INVITE_KEY:
        return jsonify({"success": False, "message": "Invalid invite key. Contact your admin."})
    if len(password) < 8:
        return jsonify({"success": False, "message": "Password must be at least 8 characters."})
    if len(username) < 3:
        return jsonify({"success": False, "message": "Username must be at least 3 characters."})

    try:
        conn   = get_connection()
        cursor = conn.cursor()

        # Check username not taken
        cursor.execute("SELECT user_id FROM app_users WHERE username = :1", [username])
        if cursor.fetchone():
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Username already taken."})

        # Check email not taken (username used as email prefix is optional,
        # but we need a unique email for the employees table)
        email = f"{username}@hrms.com"
        cursor.execute("SELECT emp_id FROM employees WHERE email = :1", [email])
        if cursor.fetchone():
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Username already in use as employee email."})

        hashed = hash_password(password)

        # 1. Insert employee record
        cursor.execute(
            "INSERT INTO employees (first_name, last_name, email, dept_id, desig_id, salary) "
            "VALUES (:1, :2, :3, :4, :5, 1) RETURNING emp_id INTO :6",
            [first_name, last_name, email, int(dept_id), int(desig_id),
             cursor.var(__import__('oracledb').NUMBER)]
        )
        # Get the new emp_id
        cursor.execute(
            "SELECT emp_id FROM employees WHERE email = :1", [email]
        )
        emp_id = cursor.fetchone()[0]

        # 2. The trigger trg_create_login will have auto-inserted a login with
        #    username = first.last and password = 'changeme123'.
        #    We need to UPDATE that record to use the chosen username + hashed password,
        #    OR delete it and insert ours.
        cursor.execute(
            "DELETE FROM app_users WHERE emp_id = :1", [emp_id]
        )

        # 3. Insert our proper app_users record
        cursor.execute(
            "INSERT INTO app_users (username, password, emp_id, role, is_active) "
            "VALUES (:1, :2, :3, 'EMPLOYEE', 1)",
            [username, hashed, emp_id]
        )

        conn.commit()
        cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Account created! You can now log in."})

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})
    
@auth_bp.route("/api/register/form-data")
def register_form_data():
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT dept_id, dept_name FROM departments ORDER BY dept_name")
        departments = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]
        cursor.execute("SELECT desig_id, title FROM designations ORDER BY title")
        designations = [{"id": r[0], "title": r[1]} for r in cursor.fetchall()]
        cursor.close(); conn.close()
        return jsonify({"departments": departments, "designations": designations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

# ── Login ───────────────────────────────────────────────────────────────────
@auth_bp.route("/api/login", methods=["POST"])
def login():
    data     = request.get_json()
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT u.user_id, u.username, u.password, u.role, u.emp_id, "
            "       e.first_name, e.last_name "
            "FROM app_users u "
            "LEFT JOIN employees e ON u.emp_id = e.emp_id "
            "WHERE u.username = :1 AND u.is_active = 1",
            [username]
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row is None:
            return jsonify({"success": False, "message": "Username not found."})

        user_id, uname, stored_pass, role, emp_id, fname, lname = row

        # Accept plain (legacy) or hashed password
        if password != stored_pass and hash_password(password) != stored_pass:
            return jsonify({"success": False, "message": "Incorrect password."})

        session["user_id"]  = user_id
        session["username"] = uname
        session["role"]     = role
        session["emp_id"]   = emp_id
        session["name"]     = f"{fname} {lname}" if fname else uname

        if stored_pass == "changeme123":
            return jsonify({"success": True, "redirect": "/change-password"})

        return jsonify({"success": True, "redirect": "/dashboard"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {str(e)}"})


# ── Change password ─────────────────────────────────────────────────────────
@auth_bp.route("/api/change-password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not authenticated."})

    data     = request.get_json()
    current  = data.get("current_password", "")
    new_pass = data.get("new_password",     "")
    confirm  = data.get("confirm_password", "")

    if new_pass != confirm:
        return jsonify({"success": False, "message": "Passwords do not match."})
    if len(new_pass) < 8:
        return jsonify({"success": False, "message": "Password must be at least 8 characters."})

    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password FROM app_users WHERE user_id = :1",
            [session["user_id"]]
        )
        row    = cursor.fetchone()
        stored = row[0]

        if current != stored and hash_password(current) != stored:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Current password is incorrect."})

        cursor.execute(
            "UPDATE app_users SET password = :1 WHERE user_id = :2",
            [hash_password(new_pass), session["user_id"]]
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "redirect": "/dashboard"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})


# ── Logout ──────────────────────────────────────────────────────────────────
@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "redirect": "/login"})


# ── Session info ────────────────────────────────────────────────────────────
@auth_bp.route("/api/session")
def get_session():
    if "user_id" not in session:
        return jsonify({"authenticated": False})
    return jsonify({
        "authenticated": True,
        "user_id":  session["user_id"],
        "username": session["username"],
        "role":     session["role"],
        "emp_id":   session.get("emp_id"),
        "name":     session["name"],
    })

@auth_bp.route("/api/admin/link-user", methods=["POST"])
def link_user():
    if "user_id" not in session or session.get("role") != "ADMIN":
        return jsonify({"error": "Access denied"}), 403
    data     = request.get_json()
    username = data.get("username")
    emp_id   = data.get("emp_id")
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE app_users SET emp_id = :1 WHERE username = :2",
            [int(emp_id), username]
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ── Admin: update invite key ────────────────────────────────────────────────
@auth_bp.route("/api/admin/invite-key", methods=["GET"])
def get_invite_key():
    if "user_id" not in session or session.get("role") != "ADMIN":
        return jsonify({"error": "Access denied"}), 403
    return jsonify({"invite_key": INVITE_KEY})
