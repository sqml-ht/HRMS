from flask import Blueprint, request, session, jsonify
from config import get_connection
from datetime import date

attendance_bp = Blueprint("attendance", __name__)


def _get_linked_emp_id(cursor):
    """Return the emp_id linked to the current session user, or None."""
    cursor.execute("SELECT emp_id FROM app_users WHERE user_id = :1", [session["user_id"]])
    row = cursor.fetchone()
    return row[0] if row and row[0] else None


@attendance_bp.route("/api/attendance")
def list_attendance():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    month      = request.args.get("month", "").strip()
    emp_filter = request.args.get("emp_id", "").strip()

    try:
        conn   = get_connection()
        cursor = conn.cursor()

        conditions = ["1=1"]
        params     = []

        # ── FIX 1: Employees see ONLY their own attendance ───────────────────
        if session.get("role") == "EMPLOYEE":
            emp_id = _get_linked_emp_id(cursor)
            if not emp_id:
                cursor.close(); conn.close()
                return jsonify({"records": [], "status_counts": {}, "employees": [],
                                "emp_linked": False})
            conditions.append(f"a.emp_id = :{len(params)+1}")
            params.append(emp_id)
        elif emp_filter:
            # Admin filtered by employee
            conditions.append(f"a.emp_id = :{len(params)+1}")
            params.append(int(emp_filter))

        if month:
            conditions.append(f"TO_CHAR(a.att_date, 'YYYY-MM') = :{len(params)+1}")
            params.append(month)

        where = " AND ".join(conditions)
        query = f"""
            SELECT a.att_id,
                   e.first_name || ' ' || e.last_name,
                   TO_CHAR(a.att_date, 'DD Mon YYYY'),
                   a.status,
                   TO_CHAR(a.check_in,  'HH24:MI'),
                   TO_CHAR(a.check_out, 'HH24:MI'),
                   a.overtime_hr,
                   e.emp_id
            FROM attendance a
            JOIN employees e ON a.emp_id = e.emp_id
            WHERE {where}
            ORDER BY a.att_date DESC, e.first_name
        """
        cursor.execute(query, params)

        records = [
            {
                "att_id":    r[0], "emp_name":  r[1],
                "date":      r[2], "status":    r[3],
                "check_in":  r[4] or "—", "check_out": r[5] or "—",
                "overtime":  float(r[6] or 0), "emp_id": r[7],
            }
            for r in cursor.fetchall()
        ]

        # Status counts scoped to the same filter
        if session.get("role") == "EMPLOYEE" and params:
            cursor.execute(
                f"SELECT status, COUNT(*) FROM attendance "
                f"WHERE emp_id = :1 AND TO_CHAR(att_date,'YYYY-MM') = TO_CHAR(SYSDATE,'YYYY-MM') "
                f"GROUP BY status",
                [params[0]]
            )
        else:
            cursor.execute(
                "SELECT status, COUNT(*) FROM attendance "
                "WHERE TO_CHAR(att_date,'YYYY-MM') = TO_CHAR(SYSDATE,'YYYY-MM') "
                "GROUP BY status"
            )
        status_counts = {r[0]: r[1] for r in cursor.fetchall()}

        # Employee dropdown — only for admin/HR
        employees = []
        if session.get("role") in ("ADMIN", "HR"):
            cursor.execute(
                "SELECT emp_id, first_name || ' ' || last_name "
                "FROM employees WHERE status='ACTIVE' ORDER BY first_name"
            )
            employees = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]

        cursor.close(); conn.close()
        return jsonify({"records": records, "status_counts": status_counts,
                        "employees": employees, "emp_linked": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@attendance_bp.route("/api/attendance/checkin", methods=["POST"])
def self_checkin():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        emp_id = _get_linked_emp_id(cursor)
        if not emp_id:
            cursor.close(); conn.close()
            return jsonify({"success": False,
                            "message": "No employee profile linked. Contact admin."})

        today = date.today().strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT att_id, status, TO_CHAR(check_in,'HH24:MI'), TO_CHAR(check_out,'HH24:MI') "
            "FROM attendance WHERE emp_id = :1 AND att_date = TO_DATE(:2,'YYYY-MM-DD')",
            [emp_id, today]
        )
        existing = cursor.fetchone()

        if existing and existing[2]:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": f"Already checked in at {existing[2]}."})

        if existing:
            cursor.execute(
                "UPDATE attendance SET check_in = SYSTIMESTAMP, status = 'PRESENT' "
                "WHERE att_id = :1", [existing[0]]
            )
        else:
            cursor.execute(
                "INSERT INTO attendance (emp_id, att_date, status, check_in) "
                "VALUES (:1, TO_DATE(:2,'YYYY-MM-DD'), 'PRESENT', SYSTIMESTAMP)",
                [emp_id, today]
            )

        conn.commit()
        cursor.execute("SELECT TO_CHAR(SYSTIMESTAMP, 'HH24:MI') FROM dual")
        now = cursor.fetchone()[0]
        cursor.close(); conn.close()
        return jsonify({"success": True, "message": f"Checked in at {now}!", "time": now})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@attendance_bp.route("/api/attendance/checkout", methods=["POST"])
def self_checkout():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        emp_id = _get_linked_emp_id(cursor)
        if not emp_id:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "No employee profile linked. Contact admin."})

        today = date.today().strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT att_id, TO_CHAR(check_in,'HH24:MI'), TO_CHAR(check_out,'HH24:MI') "
            "FROM attendance WHERE emp_id = :1 AND att_date = TO_DATE(:2,'YYYY-MM-DD')",
            [emp_id, today]
        )
        existing = cursor.fetchone()

        if not existing or not existing[1]:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "You haven't checked in yet today."})
        if existing[2]:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": f"Already checked out at {existing[2]}."})

        cursor.execute(
            "SELECT ROUND("
            "  (EXTRACT(DAY    FROM (SYSTIMESTAMP - check_in)) * 24) +"
            "  (EXTRACT(HOUR   FROM (SYSTIMESTAMP - check_in))) +"
            "  (EXTRACT(MINUTE FROM (SYSTIMESTAMP - check_in)) / 60)"
            ", 2) FROM attendance WHERE att_id = :1", [existing[0]]
        )
        hours_worked = float(cursor.fetchone()[0] or 0)
        overtime     = max(0, round(hours_worked - 8, 2))

        cursor.execute(
            "UPDATE attendance SET check_out = SYSTIMESTAMP, overtime_hr = :1 WHERE att_id = :2",
            [overtime, existing[0]]
        )
        conn.commit()
        cursor.execute("SELECT TO_CHAR(SYSTIMESTAMP,'HH24:MI') FROM dual")
        now = cursor.fetchone()[0]
        cursor.close(); conn.close()
        return jsonify({"success": True, "message": f"Checked out at {now}! Overtime: {overtime}h",
                        "time": now, "overtime": overtime})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@attendance_bp.route("/api/attendance/today")
def today_status():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        emp_id = _get_linked_emp_id(cursor)
        if not emp_id:
            cursor.close(); conn.close()
            return jsonify({"emp_linked": False})

        today = date.today().strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT status, TO_CHAR(check_in,'HH24:MI'), TO_CHAR(check_out,'HH24:MI'), overtime_hr "
            "FROM attendance WHERE emp_id = :1 AND att_date = TO_DATE(:2,'YYYY-MM-DD')",
            [emp_id, today]
        )
        rec = cursor.fetchone()
        cursor.close(); conn.close()

        if not rec:
            return jsonify({"emp_linked": True, "checked_in": False, "checked_out": False})
        return jsonify({
            "emp_linked":  True, "status":    rec[0],
            "check_in":    rec[1], "check_out": rec[2],
            "overtime":    float(rec[3] or 0),
            "checked_in":  rec[1] is not None,
            "checked_out": rec[2] is not None,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@attendance_bp.route("/api/attendance/employees")
def get_employees_for_mark():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    if session.get("role") not in ("ADMIN", "HR"):
        return jsonify({"error": "Access denied"}), 403
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT emp_id, first_name || ' ' || last_name "
            "FROM employees WHERE status='ACTIVE' ORDER BY first_name"
        )
        employees = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]
        cursor.close(); conn.close()
        return jsonify({"employees": employees})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@attendance_bp.route("/api/attendance", methods=["POST"])
def mark_attendance():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    if session.get("role") not in ("ADMIN", "HR"):
        return jsonify({"error": "Access denied"}), 403

    data     = request.get_json()
    att_date = data.get("att_date")
    records  = data.get("records", [])

    try:
        conn   = get_connection()
        cursor = conn.cursor()

        for rec in records:
            emp_id    = int(rec["emp_id"])
            status    = rec.get("status", "PRESENT")
            check_in  = rec.get("check_in")  or None
            check_out = rec.get("check_out") or None
            overtime  = float(rec.get("overtime", 0) or 0)

            cursor.execute(
                "SELECT att_id FROM attendance "
                "WHERE emp_id = :1 AND att_date = TO_DATE(:2,'YYYY-MM-DD')",
                [emp_id, att_date]
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    "UPDATE attendance SET status=:1, overtime_hr=:2 WHERE att_id=:3",
                    [status, overtime, existing[0]]
                )
            else:
                if check_in and check_out:
                    cursor.execute(
                        "INSERT INTO attendance (emp_id,att_date,status,check_in,check_out,overtime_hr) "
                        "VALUES (:1,TO_DATE(:2,'YYYY-MM-DD'),:3,"
                        "TO_TIMESTAMP(:4,'YYYY-MM-DD HH24:MI'),"
                        "TO_TIMESTAMP(:5,'YYYY-MM-DD HH24:MI'),:6)",
                        [emp_id, att_date, status,
                         f"{att_date} {check_in}", f"{att_date} {check_out}", overtime]
                    )
                else:
                    cursor.execute(
                        "INSERT INTO attendance (emp_id,att_date,status,overtime_hr) "
                        "VALUES (:1,TO_DATE(:2,'YYYY-MM-DD'),:3,:4)",
                        [emp_id, att_date, status, overtime]
                    )

        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "count": len(records)})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500