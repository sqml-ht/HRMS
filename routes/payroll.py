from flask import Blueprint, request, session, jsonify
from config import get_connection

payroll_bp = Blueprint("payroll", __name__)


@payroll_bp.route("/api/payroll")
def list_payroll():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    year_filter  = request.args.get("year",  "").strip()
    month_filter = request.args.get("month", "").strip()

    try:
        conn   = get_connection()
        cursor = conn.cursor()

        conditions = ["1=1"]
        params     = []

        # ── FIX 1: Employees see ONLY their own payslips ─────────────────────
        if session.get("role") == "EMPLOYEE":
            emp_id = session.get("emp_id")
            if not emp_id:
                # Try fetching from DB if session doesn't have it
                cursor.execute("SELECT emp_id FROM app_users WHERE user_id = :1",
                               [session["user_id"]])
                row = cursor.fetchone()
                emp_id = row[0] if row and row[0] else None

            if not emp_id:
                cursor.close(); conn.close()
                return jsonify({"records": [], "total_paid": 0, "total_pending": 0})

            conditions.append(f"e.emp_id = :{len(params)+1}")
            params.append(emp_id)

        if year_filter:
            conditions.append(f"p.pay_year = :{len(params)+1}")
            params.append(int(year_filter))
        if month_filter:
            conditions.append(f"UPPER(p.pay_month) = UPPER(:{len(params)+1})")
            params.append(month_filter)

        where = " AND ".join(conditions)
        query = f"""
            SELECT p.pay_id, e.first_name || ' ' || e.last_name,
                   p.pay_month, p.pay_year, p.basic_pay, p.bonus,
                   p.deductions, p.tax, p.net_pay, p.status,
                   TO_CHAR(p.generated_at, 'DD Mon YYYY'), e.emp_id
            FROM payroll p
            JOIN employees e ON p.emp_id = e.emp_id
            WHERE {where}
            ORDER BY p.pay_year DESC, p.pay_id DESC
        """
        cursor.execute(query, params)

        records = [
            {
                "pay_id":       r[0], "emp_name":     r[1],
                "month":        r[2], "year":         r[3],
                "basic":        float(r[4] or 0), "bonus":  float(r[5] or 0),
                "deductions":   float(r[6] or 0), "tax":    float(r[7] or 0),
                "net":          float(r[8] or 0), "status": r[9],
                "generated_at": r[10] or "—",    "emp_id": r[11],
            }
            for r in cursor.fetchall()
        ]

        # Totals scoped by role
        if session.get("role") == "EMPLOYEE" and params:
            cursor.execute(
                "SELECT NVL(SUM(net_pay),0) FROM payroll "
                "WHERE status='PAID' AND pay_year=EXTRACT(YEAR FROM SYSDATE) "
                "AND emp_id = :1", [params[0]]
            )
            total_paid = float(cursor.fetchone()[0])
            cursor.execute(
                "SELECT NVL(SUM(net_pay),0) FROM payroll "
                "WHERE status='PENDING' AND emp_id = :1", [params[0]]
            )
            total_pending = float(cursor.fetchone()[0])
        else:
            cursor.execute(
                "SELECT NVL(SUM(net_pay),0) FROM payroll "
                "WHERE status='PAID' AND pay_year=EXTRACT(YEAR FROM SYSDATE)"
            )
            total_paid = float(cursor.fetchone()[0])
            cursor.execute("SELECT NVL(SUM(net_pay),0) FROM payroll WHERE status='PENDING'")
            total_pending = float(cursor.fetchone()[0])

        cursor.close(); conn.close()
        return jsonify({"records": records, "total_paid": total_paid,
                        "total_pending": total_pending})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@payroll_bp.route("/api/payroll/employees")
def get_employees():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    if session.get("role") not in ("ADMIN", "HR"):
        return jsonify({"error": "Access denied"}), 403
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT emp_id, first_name || ' ' || last_name, salary "
            "FROM employees WHERE status='ACTIVE' ORDER BY first_name"
        )
        employees = [{"id": r[0], "name": r[1], "salary": float(r[2])} for r in cursor.fetchall()]
        cursor.close(); conn.close()
        return jsonify({"employees": employees})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@payroll_bp.route("/api/payroll/generate", methods=["POST"])
def generate_payroll():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    if session.get("role") not in ("ADMIN", "HR"):
        return jsonify({"error": "Access denied"}), 403

    data      = request.get_json()
    pay_month = data.get("pay_month", "").strip()
    pay_year  = int(data.get("pay_year"))
    emp_ids   = data.get("emp_ids", [])
    month_abbr = pay_month[:3].upper()
    year_str   = str(pay_year)

    try:
        conn   = get_connection()
        cursor = conn.cursor()
        generated = 0

        for emp_id in emp_ids:
            cursor.execute(
                "SELECT pay_id FROM payroll "
                "WHERE emp_id = :1 AND UPPER(pay_month) = UPPER(:2) AND pay_year = :3",
                [emp_id, pay_month, pay_year]
            )
            if cursor.fetchone():
                continue

            cursor.execute("SELECT salary FROM employees WHERE emp_id = :1", [emp_id])
            row = cursor.fetchone()
            if not row:
                continue
            basic = float(row[0])

            cursor.execute(
                "SELECT NVL(SUM(overtime_hr), 0) FROM attendance "
                "WHERE emp_id = :1 "
                "AND TO_CHAR(att_date, 'MON')  = :2 "
                "AND TO_CHAR(att_date, 'YYYY') = :3",
                [emp_id, month_abbr, year_str]
            )
            overtime   = float(cursor.fetchone()[0])
            bonus      = overtime * 500
            deductions = basic * 0.05
            tax        = basic * 0.10
            net_pay    = basic + bonus - deductions - tax

            cursor.execute(
                "INSERT INTO payroll "
                "(emp_id, pay_month, pay_year, basic_pay, bonus, deductions, tax, net_pay, status) "
                "VALUES (:1, :2, :3, :4, :5, :6, :7, :8, 'PENDING')",
                [emp_id, pay_month, pay_year, basic, bonus, deductions, tax, net_pay]
            )
            generated += 1

        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "generated": generated})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@payroll_bp.route("/api/payroll/<int:pay_id>/approve", methods=["POST"])
def approve_payroll(pay_id):
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    if session.get("role") not in ("ADMIN", "HR"):
        return jsonify({"error": "Access denied"}), 403
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE payroll SET status='PAID' WHERE pay_id = :1", [pay_id])
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@payroll_bp.route("/api/payroll/<int:pay_id>/reject", methods=["POST"])
def reject_payroll(pay_id):
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    if session.get("role") not in ("ADMIN", "HR"):
        return jsonify({"error": "Access denied"}), 403
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE payroll SET status='REJECTED' WHERE pay_id = :1", [pay_id])
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500