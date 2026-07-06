from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from config import get_connection

reports_bp = Blueprint("reports", __name__)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        if session.get("role") not in ("ADMIN", "HR"):
            flash("Access denied.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated

@reports_bp.after_request
def add_no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@reports_bp.route("/reports")
@admin_required
def reports_home():
    return render_template("reports/index.html", user=session)

@reports_bp.route("/api/reports/department-summary")
def api_dept_summary():
    if "user_id" not in session or session.get("role") not in ("ADMIN", "HR"):
        return jsonify({"error": "Access denied"}), 403
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.dept_name,
                   COUNT(e.emp_id) AS headcount,
                   ROUND(AVG(e.salary), 2) AS avg_salary,
                   MAX(e.salary) AS max_salary,
                   MIN(e.salary) AS min_salary,
                   SUM(e.salary) AS total_salary,
                   (SELECT COUNT(*) FROM attendance a
                    JOIN employees ea ON a.emp_id = ea.emp_id
                    WHERE ea.dept_id = d.dept_id
                    AND a.status = 'PRESENT'
                    AND a.att_date >= TRUNC(SYSDATE,'MM')) AS present_this_month
            FROM departments d
            LEFT JOIN employees e ON d.dept_id = e.dept_id AND e.status = 'ACTIVE'
            GROUP BY d.dept_id, d.dept_name
            ORDER BY total_salary DESC NULLS LAST
        """)
        dept_rows = cursor.fetchall()

        cursor.execute("""
            SELECT e.first_name || ' ' || e.last_name,
                   d.dept_name, e.salary,
                   ROUND(e.salary - (SELECT AVG(salary) FROM employees WHERE status='ACTIVE'), 2)
            FROM employees e
            LEFT JOIN departments d ON e.dept_id = d.dept_id
            WHERE e.status = 'ACTIVE'
            AND e.salary > (SELECT AVG(salary) FROM employees WHERE status='ACTIVE')
            ORDER BY e.salary DESC
        """)
        above_rows = cursor.fetchall()

        cursor.close(); conn.close()

        dept_data = [
            {
                "dept": r[0], "headcount": r[1] or 0,
                "avg_salary": float(r[2] or 0), "max_salary": float(r[3] or 0),
                "min_salary": float(r[4] or 0), "total_salary": float(r[5] or 0),
                "present_month": r[6] or 0,
            }
            for r in dept_rows
        ]
        above_avg = [
            {"name": r[0], "dept": r[1] or "—", "salary": float(r[2] or 0), "diff": float(r[3] or 0)}
            for r in above_rows
        ]
        return jsonify({"dept_data": dept_data, "above_avg": above_avg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@reports_bp.route("/api/reports/attendance-summary")
def api_attendance_summary():
    if "user_id" not in session or session.get("role") not in ("ADMIN", "HR"):
        return jsonify({"error": "Access denied"}), 403
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.first_name || ' ' || e.last_name AS emp_name,
                   NVL(d.dept_name, '—'),
                   COUNT(CASE WHEN a.status='PRESENT'  THEN 1 END),
                   COUNT(CASE WHEN a.status='ABSENT'   THEN 1 END),
                   COUNT(CASE WHEN a.status='LATE'     THEN 1 END),
                   COUNT(CASE WHEN a.status='HALF_DAY' THEN 1 END),
                   NVL(SUM(a.overtime_hr), 0),
                   COUNT(a.att_id),
                   ROUND(COUNT(CASE WHEN a.status='PRESENT' THEN 1 END) * 100.0
                         / NULLIF(COUNT(a.att_id), 0), 1)
            FROM employees e
            LEFT JOIN attendance  a ON e.emp_id  = a.emp_id
            LEFT JOIN departments d ON e.dept_id = d.dept_id
            WHERE e.status = 'ACTIVE'
            GROUP BY e.emp_id, e.first_name, e.last_name, d.dept_name
            ORDER BY 9 DESC NULLS LAST
        """)
        rows = cursor.fetchall()
        cursor.close(); conn.close()

        att_data = [
            {
                "name": r[0], "dept": r[1], "present": r[2] or 0,
                "absent": r[3] or 0, "late": r[4] or 0, "half_day": r[5] or 0,
                "overtime": float(r[6] or 0), "total": r[7] or 0,
                "pct": float(r[8] or 0),
            }
            for r in rows
        ]
        return jsonify({"att_data": att_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@reports_bp.route("/api/reports/payroll-summary")
def api_payroll_summary():
    if "user_id" not in session or session.get("role") not in ("ADMIN", "HR"):
        return jsonify({"error": "Access denied"}), 403
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.pay_month, p.pay_year,
                   COUNT(p.pay_id),
                   SUM(p.basic_pay), SUM(p.bonus),
                   SUM(p.deductions), SUM(p.tax), SUM(p.net_pay),
                   COUNT(CASE WHEN p.status='PAID'    THEN 1 END),
                   COUNT(CASE WHEN p.status='PENDING' THEN 1 END)
            FROM payroll p
            GROUP BY p.pay_month, p.pay_year
            ORDER BY p.pay_year DESC, p.pay_month
        """)
        payroll_rows = cursor.fetchall()

        cursor.execute("""
            SELECT e.first_name || ' ' || e.last_name,
                   NVL(d.dept_name, '—'),
                   SUM(p.net_pay) AS ytd_pay
            FROM payroll p
            INNER JOIN employees    e ON p.emp_id  = e.emp_id
            LEFT  JOIN departments  d ON e.dept_id = d.dept_id
            WHERE p.pay_year = EXTRACT(YEAR FROM SYSDATE)
              AND p.status = 'PAID'
            GROUP BY e.emp_id, e.first_name, e.last_name, d.dept_name
            ORDER BY ytd_pay DESC FETCH FIRST 10 ROWS ONLY
        """)
        earner_rows = cursor.fetchall()
        cursor.close(); conn.close()

        payroll_data = [
            {
                "month": r[0], "year": r[1], "count": r[2] or 0,
                "total_basic": float(r[3] or 0), "total_bonus": float(r[4] or 0),
                "total_deductions": float(r[5] or 0), "total_tax": float(r[6] or 0),
                "total_net": float(r[7] or 0), "paid": r[8] or 0, "pending": r[9] or 0,
            }
            for r in payroll_rows
        ]
        top_earners = [
            {"name": r[0], "dept": r[1], "ytd": float(r[2] or 0)}
            for r in earner_rows
        ]
        return jsonify({"payroll_data": payroll_data, "top_earners": top_earners})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@reports_bp.route("/api/reports/audit-log")
def api_audit_log():
    if "user_id" not in session or session.get("role") not in ("ADMIN", "HR"):
        return jsonify({"error": "Access denied"}), 403
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT audit_id, table_name, operation, record_id,
                   NVL(old_value, '—'), NVL(new_value, '—'),
                   changed_by, TO_CHAR(changed_at, 'DD Mon YYYY HH24:MI')
            FROM audit_log
            ORDER BY changed_at DESC
            FETCH FIRST 100 ROWS ONLY
        """)
        rows = cursor.fetchall()
        cursor.close(); conn.close()

        logs = [
            {
                "id": r[0], "table": r[1], "op": r[2], "record_id": r[3],
                "old": r[4], "new": r[5], "by": r[6], "at": r[7],
            }
            for r in rows
        ]
        return jsonify({"logs": logs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500