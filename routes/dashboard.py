from flask import Blueprint, session, jsonify
from config import get_connection
from datetime import date

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/api/dashboard")
def dashboard():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    role = session.get("role")

    try:
        conn   = get_connection()
        cursor = conn.cursor()

        # ── EMPLOYEE dashboard: only their own data ───────────────────────────
        if role == "EMPLOYEE":
            emp_id = session.get("emp_id")

            # Try fetching emp_id from DB if not in session
            if not emp_id:
                cursor.execute("SELECT emp_id FROM app_users WHERE user_id = :1",
                               [session["user_id"]])
                row = cursor.fetchone()
                emp_id = row[0] if row and row[0] else None

            if not emp_id:
                cursor.close(); conn.close()
                return jsonify({
                    "role": "EMPLOYEE",
                    "emp_linked": False,
                    "name": session.get("name", ""),
                    "message": "Your account is not yet linked to an employee profile. Contact your admin."
                })

            today = date.today().strftime("%Y-%m-%d")

            # Today's attendance
            cursor.execute(
                "SELECT status, TO_CHAR(check_in,'HH24:MI'), TO_CHAR(check_out,'HH24:MI'), overtime_hr "
                "FROM attendance WHERE emp_id = :1 AND att_date = TO_DATE(:2,'YYYY-MM-DD')",
                [emp_id, today]
            )
            att_today = cursor.fetchone()

            # Attendance stats this month
            cursor.execute("""
                SELECT
                    COUNT(CASE WHEN status='PRESENT'  THEN 1 END),
                    COUNT(CASE WHEN status='ABSENT'   THEN 1 END),
                    COUNT(CASE WHEN status='LATE'     THEN 1 END),
                    NVL(SUM(overtime_hr),0)
                FROM attendance
                WHERE emp_id = :1
                AND TO_CHAR(att_date,'YYYY-MM') = TO_CHAR(SYSDATE,'YYYY-MM')
            """, [emp_id])
            att_stats = cursor.fetchone()

            # Last 5 payslips
            cursor.execute("""
                SELECT pay_month, pay_year, net_pay, status, TO_CHAR(generated_at,'DD Mon YYYY')
                FROM payroll WHERE emp_id = :1
                ORDER BY pay_year DESC, pay_id DESC FETCH FIRST 5 ROWS ONLY
            """, [emp_id])
            payslips = [
                {"month": r[0], "year": r[1], "net": float(r[2] or 0),
                 "status": r[3], "date": r[4] or "—"}
                for r in cursor.fetchall()
            ]

            # Employee profile summary
            cursor.execute("""
                SELECT e.first_name||' '||e.last_name, d.dept_name, dg.title, e.salary,
                       TO_CHAR(e.hire_date,'DD Mon YYYY'), e.status
                FROM employees e
                LEFT JOIN departments  d  ON e.dept_id  = d.dept_id
                LEFT JOIN designations dg ON e.desig_id = dg.desig_id
                WHERE e.emp_id = :1
            """, [emp_id])
            prof = cursor.fetchone()

            # YTD total paid
            cursor.execute(
                "SELECT NVL(SUM(net_pay),0) FROM payroll "
                "WHERE emp_id = :1 AND status='PAID' AND pay_year=EXTRACT(YEAR FROM SYSDATE)",
                [emp_id]
            )
            ytd_pay = float(cursor.fetchone()[0])

            cursor.close(); conn.close()
            return jsonify({
                "role":        "EMPLOYEE",
                "emp_linked":  True,
                "emp_id":      emp_id,
                "name":        session.get("name", ""),
                "today_att": {
                    "status":      att_today[0] if att_today else None,
                    "check_in":    att_today[1] if att_today else None,
                    "check_out":   att_today[2] if att_today else None,
                    "overtime":    float(att_today[3] or 0) if att_today else 0,
                } if att_today else None,
                "att_stats": {
                    "present":  att_stats[0] or 0,
                    "absent":   att_stats[1] or 0,
                    "late":     att_stats[2] or 0,
                    "overtime": float(att_stats[3] or 0),
                },
                "payslips":    payslips,
                "ytd_pay":     ytd_pay,
                "profile": {
                    "name":      prof[0], "dept":      prof[1] or "—",
                    "title":     prof[2] or "—", "salary": float(prof[3] or 0),
                    "hire_date": prof[4] or "—", "status": prof[5],
                } if prof else None,
            })

        # ── ADMIN / HR dashboard: full organisational KPIs ────────────────────
        cursor.execute("SELECT COUNT(*) FROM employees WHERE status='ACTIVE'")
        total_employees = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM attendance WHERE att_date = TRUNC(SYSDATE) AND status='PRESENT'"
        )
        present_today = cursor.fetchone()[0]

        cursor.execute(
            "SELECT NVL(SUM(net_pay),0) FROM payroll "
            "WHERE status='PAID' AND pay_year=EXTRACT(YEAR FROM SYSDATE)"
        )
        total_payroll = float(cursor.fetchone()[0])

        cursor.execute("SELECT COUNT(*) FROM departments")
        departments = cursor.fetchone()[0]

        cursor.execute(
            "SELECT NVL(COUNT(*),0) FROM attendance WHERE att_date=TRUNC(SYSDATE) AND status='ABSENT'"
        )
        absent_today = cursor.fetchone()[0]

        cursor.execute("SELECT NVL(COUNT(*),0) FROM payroll WHERE status='PENDING'")
        pending_payroll = cursor.fetchone()[0]

        # Recent 5 employees
        cursor.execute("""
            SELECT e.first_name||' '||e.last_name, NVL(d.dept_name,'—'), e.salary,
                   TO_CHAR(e.hire_date,'DD Mon YYYY')
            FROM employees e
            LEFT JOIN departments d ON e.dept_id = d.dept_id
            ORDER BY e.emp_id DESC FETCH FIRST 5 ROWS ONLY
        """)
        recent_employees = [
            {"name": r[0], "dept": r[1], "salary": float(r[2]), "hire_date": r[3] or "—"}
            for r in cursor.fetchall()
        ]

        # Department headcount
        cursor.execute("""
            SELECT d.dept_name, COUNT(e.emp_id)
            FROM departments d
            LEFT JOIN employees e ON d.dept_id = e.dept_id AND e.status = 'ACTIVE'
            GROUP BY d.dept_id, d.dept_name
            ORDER BY COUNT(e.emp_id) DESC
        """)
        dept_counts = [{"dept": r[0], "count": r[1]} for r in cursor.fetchall()]

        # Today's attendance breakdown (all depts)
        cursor.execute("""
            SELECT d.dept_name,
                   COUNT(CASE WHEN a.status='PRESENT' THEN 1 END),
                   COUNT(e.emp_id)
            FROM departments d
            LEFT JOIN employees e ON d.dept_id = e.dept_id AND e.status='ACTIVE'
            LEFT JOIN attendance a ON e.emp_id = a.emp_id AND a.att_date = TRUNC(SYSDATE)
            GROUP BY d.dept_id, d.dept_name
            ORDER BY d.dept_name
        """)
        dept_attendance = [
            {"dept": r[0], "present": r[1] or 0, "total": r[2] or 0}
            for r in cursor.fetchall()
        ]

        cursor.close(); conn.close()
        return jsonify({
            "role":             "ADMIN",
            "total_employees":  total_employees,
            "present_today":    present_today,
            "absent_today":     absent_today,
            "total_payroll":    total_payroll,
            "departments":      departments,
            "pending_payroll":  pending_payroll,
            "recent_employees": recent_employees,
            "dept_counts":      dept_counts,
            "dept_attendance":  dept_attendance,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500