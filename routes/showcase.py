from flask import Blueprint, request, session, jsonify
from config import get_connection

showcase_bp = Blueprint("showcase", __name__)


def require_admin():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    if session.get("role") not in ("ADMIN", "HR"):
        return jsonify({"error": "Access denied"}), 403
    return None


# ------View: vw_employee_details ---------------------------------------------------------
@showcase_bp.route("/api/showcase/view-employee-details")
def view_employee_details():
    err = require_admin()
    if err: return err
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT emp_id, full_name, email, phone, salary,
                   TO_CHAR(hire_date,'DD Mon YYYY'), status,
                   dept_name, designation, grade, manager_name
            FROM vw_employee_details
            ORDER BY emp_id
        """)
        rows = [
            {
                "emp_id": r[0], "full_name": r[1], "email": r[2],
                "phone": r[3] or "—", "salary": float(r[4] or 0),
                "hire_date": r[5] or "—", "status": r[6],
                "dept_name": r[7] or "—", "designation": r[8] or "—",
                "grade": r[9] or "—", "manager_name": r[10] or "—",
            }
            for r in cursor.fetchall()
        ]
        cursor.close(); conn.close()
        return jsonify({"rows": rows, "count": len(rows)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── View: vw_attendance_summary ──────────────────────────────────────────────
@showcase_bp.route("/api/showcase/view-attendance-summary")
def view_attendance_summary():
    err = require_admin()
    if err: return err
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT emp_id, full_name, dept_name,
                   present_days, absent_days, late_days,
                   total_overtime, attendance_pct
            FROM vw_attendance_summary
            ORDER BY attendance_pct DESC NULLS LAST
        """)
        rows = [
            {
                "emp_id": r[0], "full_name": r[1], "dept_name": r[2] or "—",
                "present_days": r[3] or 0, "absent_days": r[4] or 0,
                "late_days": r[5] or 0, "total_overtime": float(r[6] or 0),
                "attendance_pct": float(r[7] or 0),
            }
            for r in cursor.fetchall()
        ]
        cursor.close(); conn.close()
        return jsonify({"rows": rows, "count": len(rows)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── View: vw_dept_payroll_summary ────────────────────────────────────────────
@showcase_bp.route("/api/showcase/view-dept-payroll")
def view_dept_payroll():
    err = require_admin()
    if err: return err
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT dept_name, pay_month, pay_year,
                   employee_count, total_basic, total_bonus,
                   total_deductions, total_net_pay
            FROM vw_dept_payroll_summary
            ORDER BY pay_year DESC, pay_month, dept_name
        """)
        rows = [
            {
                "dept_name": r[0], "pay_month": r[1], "pay_year": r[2],
                "employee_count": r[3] or 0,
                "total_basic": float(r[4] or 0), "total_bonus": float(r[5] or 0),
                "total_deductions": float(r[6] or 0), "total_net_pay": float(r[7] or 0),
            }
            for r in cursor.fetchall()
        ]
        cursor.close(); conn.close()
        return jsonify({"rows": rows, "count": len(rows)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Stored Procedure: sp_generate_payroll ────────────────────────────────────
@showcase_bp.route("/api/showcase/sp-generate-payroll", methods=["POST"])
def sp_generate_payroll():
    err = require_admin()
    if err: return err
    data      = request.get_json()
    pay_month = data.get("pay_month", "").strip()
    pay_year  = data.get("pay_year")

    if not pay_month or not pay_year:
        return jsonify({"success": False, "message": "pay_month and pay_year required."})

    try:
        conn   = get_connection()
        cursor = conn.cursor()
        # Count before
        cursor.execute(
            "SELECT COUNT(*) FROM payroll WHERE UPPER(pay_month)=UPPER(:1) AND pay_year=:2",
            [pay_month, int(pay_year)]
        )
        before = cursor.fetchone()[0]

        cursor.callproc("sp_generate_payroll", [pay_month, int(pay_year)])
        conn.commit()

        # Count after
        cursor.execute(
            "SELECT COUNT(*) FROM payroll WHERE UPPER(pay_month)=UPPER(:1) AND pay_year=:2",
            [pay_month, int(pay_year)]
        )
        after = cursor.fetchone()[0]

        # Show generated records
        cursor.execute("""
            SELECT e.first_name||' '||e.last_name, p.basic_pay, p.bonus,
                   p.deductions, p.tax, p.net_pay, p.status
            FROM payroll p
            JOIN employees e ON p.emp_id = e.emp_id
            WHERE UPPER(p.pay_month)=UPPER(:1) AND p.pay_year=:2
            ORDER BY p.net_pay DESC
        """, [pay_month, int(pay_year)])
        records = [
            {
                "name": r[0], "basic": float(r[1] or 0), "bonus": float(r[2] or 0),
                "deductions": float(r[3] or 0), "tax": float(r[4] or 0),
                "net_pay": float(r[5] or 0), "status": r[6],
            }
            for r in cursor.fetchall()
        ]

        cursor.close(); conn.close()
        return jsonify({
            "success":    True,
            "new_records": after - before,
            "total":      after,
            "records":    records,
            "message":    f"Procedure executed. {after - before} new payslip(s) created for {pay_month} {pay_year}."
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── Stored Procedure: sp_dept_salary_raise ───────────────────────────────────
@showcase_bp.route("/api/showcase/sp-salary-raise", methods=["POST"])
def sp_salary_raise():
    err = require_admin()
    if err: return err
    data     = request.get_json()
    dept_id  = data.get("dept_id")
    raise_pct = data.get("raise_pct")

    if not dept_id or raise_pct is None:
        return jsonify({"success": False, "message": "dept_id and raise_pct required."})

    try:
        conn   = get_connection()
        cursor = conn.cursor()

        # Before snapshot
        cursor.execute("""
            SELECT e.first_name||' '||e.last_name, e.salary
            FROM employees e WHERE e.dept_id = :1 AND e.status = 'ACTIVE'
            ORDER BY e.first_name
        """, [int(dept_id)])
        before = {r[0]: float(r[1]) for r in cursor.fetchall()}

        cursor.callproc("sp_dept_salary_raise", [int(dept_id), float(raise_pct)])
        conn.commit()

        # After snapshot
        cursor.execute("""
            SELECT e.first_name||' '||e.last_name, e.salary
            FROM employees e WHERE e.dept_id = :1 AND e.status = 'ACTIVE'
            ORDER BY e.first_name
        """, [int(dept_id)])
        after_rows = cursor.fetchall()

        changes = []
        for r in after_rows:
            name      = r[0]
            new_sal   = float(r[1])
            old_sal   = before.get(name, new_sal)
            changes.append({
                "name":    name,
                "old":     old_sal,
                "new":     new_sal,
                "delta":   round(new_sal - old_sal, 2),
            })

        cursor.close(); conn.close()
        return jsonify({
            "success": True,
            "raise_pct": raise_pct,
            "affected": len(changes),
            "changes": changes,
            "message": f"Procedure applied {raise_pct}% raise to {len(changes)} employee(s)."
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── ACID Demonstration ────────────────────────────────────────────────────────
@showcase_bp.route("/api/showcase/acid-demo", methods=["POST"])
def acid_demo():
    err = require_admin()
    if err: return err
    data   = request.get_json()
    action = data.get("action", "rollback")  # "commit" or "rollback"
    emp_id = data.get("emp_id")
    amount = float(data.get("amount", 5000))

    if not emp_id:
        return jsonify({"success": False, "message": "emp_id required."})

    try:
        conn   = get_connection()
        cursor = conn.cursor()

        # Read current salary
        cursor.execute("SELECT first_name||' '||last_name, salary FROM employees WHERE emp_id = :1",
                       [int(emp_id)])
        row = cursor.fetchone()
        if not row:
            cursor.close(); conn.close()
            return jsonify({"success": False, "message": "Employee not found."})

        name        = row[0]
        old_salary  = float(row[1])

        steps = []

        # Step 1: BEGIN (implicit in Oracle  just savepoint)
        cursor.execute("SAVEPOINT acid_demo_sp")
        steps.append({"step": "SAVEPOINT acid_demo_sp", "result": "Savepoint set — changes ahead can be rolled back"})

        # Step 2: Modify salary
        new_salary = old_salary + amount
        cursor.execute("UPDATE employees SET salary = :1 WHERE emp_id = :2",
                       [new_salary, int(emp_id)])
        steps.append({
            "step":   f"UPDATE employees SET salary = {new_salary} WHERE emp_id = {emp_id}",
            "result": f"Salary changed from {old_salary:,.0f} → {new_salary:,.0f} (dirty read visible within session)"
        })

        # Step 3: Read inside transaction (dirty read within same session)
        cursor.execute("SELECT salary FROM employees WHERE emp_id = :1", [int(emp_id)])
        in_txn_salary = float(cursor.fetchone()[0])
        steps.append({
            "step":   "SELECT salary (within transaction)",
            "result": f"Reads {in_txn_salary:,.0f} — change visible inside transaction"
        })

        if action == "commit":
            conn.commit()
            steps.append({"step": "COMMIT", "result": "Change permanently written to disk. ACID: Durability guaranteed."})
            final_salary = new_salary
        else:
            cursor.execute("ROLLBACK TO SAVEPOINT acid_demo_sp")
            conn.commit()
            steps.append({"step": "ROLLBACK TO SAVEPOINT acid_demo_sp", "result": "All changes undone. Database restored to pre-transaction state."})
            # Verify rollback
            cursor.execute("SELECT salary FROM employees WHERE emp_id = :1", [int(emp_id)])
            final_salary = float(cursor.fetchone()[0])
            steps.append({
                "step":   "SELECT salary (after rollback)",
                "result": f"Salary is back to {final_salary:,.0f} — Atomicity confirmed"
            })

        cursor.close(); conn.close()
        return jsonify({
            "success":      True,
            "name":         name,
            "emp_id":       emp_id,
            "old_salary":   old_salary,
            "new_salary":   new_salary,
            "final_salary": final_salary,
            "action":       action,
            "amount":       amount,
            "steps":        steps,
        })
    except Exception as e:
        try: conn.rollback()
        except: pass
        return jsonify({"success": False, "message": str(e)}), 500


# ------------------------------ Complex JOIN queries ------------------------------
@showcase_bp.route("/api/showcase/joins")
def run_joins():
    err = require_admin()
    if err: return err
    query_type = request.args.get("type", "inner")

    try:
        conn   = get_connection()
        cursor = conn.cursor()

        if query_type == "inner":
            sql = """
                SELECT e.first_name||' '||e.last_name AS name,
                       d.dept_name, dg.title, dg.grade, e.salary
                FROM employees e
                INNER JOIN departments  d  ON e.dept_id  = d.dept_id
                INNER JOIN designations dg ON e.desig_id = dg.desig_id
                WHERE e.status = 'ACTIVE'
                ORDER BY e.salary DESC
            """
            label = "INNER JOIN — employees with dept AND designation (must have both)"
        elif query_type == "left":
            sql = """
                SELECT d.dept_name,
                       COUNT(e.emp_id)           AS headcount,
                       NVL(ROUND(AVG(e.salary),0),0) AS avg_salary
                FROM departments d
                LEFT JOIN employees e ON d.dept_id = e.dept_id AND e.status = 'ACTIVE'
                GROUP BY d.dept_id, d.dept_name
                ORDER BY headcount DESC
            """
            label = "LEFT JOIN — all departments, even if they have no active employees"
        elif query_type == "self":
            sql = """
                SELECT e.first_name||' '||e.last_name AS employee,
                       NVL(m.first_name||' '||m.last_name,'(No manager)') AS manager,
                       e.salary AS emp_salary,
                       NVL(m.salary,0) AS mgr_salary
                FROM employees e
                LEFT JOIN employees m ON e.manager_id = m.emp_id
                WHERE e.status = 'ACTIVE'
                ORDER BY mgr_salary DESC NULLS LAST
            """
            label = "SELF JOIN — employees joined to their manager (same table, two aliases)"
        elif query_type == "full":
            sql = """
                SELECT NVL(e.first_name||' '||e.last_name,'(No employee)') AS employee,
                       NVL(d.dept_name,'(No department)') AS dept_name
                FROM employees e
                FULL OUTER JOIN departments d ON e.dept_id = d.dept_id
                ORDER BY d.dept_name NULLS LAST, e.last_name NULLS LAST
            """
            label = "FULL OUTER JOIN — all employees AND all departments, with NULLs on either side"
        elif query_type == "subquery":
            sql = """
                SELECT first_name||' '||last_name AS name,
                       salary,
                       ROUND(salary - (SELECT AVG(salary) FROM employees WHERE status='ACTIVE'), 0) AS above_avg_by
                FROM employees
                WHERE status = 'ACTIVE'
                  AND salary > (SELECT AVG(salary) FROM employees WHERE status='ACTIVE')
                ORDER BY salary DESC
            """
            label = "Nested subquery — employees earning above company average (AVG computed twice as subquery)"
        elif query_type == "groupby":
            sql = """
                SELECT d.dept_name,
                       COUNT(e.emp_id)                 AS headcount,
                       ROUND(AVG(e.salary),0)          AS avg_salary,
                       MAX(e.salary)                   AS max_salary,
                       MIN(e.salary)                   AS min_salary
                FROM employees e
                JOIN departments d ON e.dept_id = d.dept_id
                WHERE e.status = 'ACTIVE'
                GROUP BY d.dept_id, d.dept_name
                HAVING AVG(e.salary) > 0
                ORDER BY avg_salary DESC
            """
            label = "GROUP BY + HAVING — department salary stats, only depts with avg > 0"
        else:
            cursor.close(); conn.close()
            return jsonify({"error": "Unknown query type"}), 400

        cursor.execute(sql)
        cols = [desc[0].lower() for desc in cursor.description]
        rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
        # Convert Decimal/float
        for row in rows:
            for k, v in row.items():
                try:
                    row[k] = float(v) if v is not None and not isinstance(v, (str, int)) else v
                except: pass

        cursor.close(); conn.close()
        return jsonify({"label": label, "sql": sql.strip(), "rows": rows, "count": len(rows)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------ Get departments list for dropdowns ---------------------------
@showcase_bp.route("/api/showcase/departments")
def get_departments():
    err = require_admin()
    if err: return err
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT dept_id, dept_name FROM departments ORDER BY dept_name")
        depts = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]
        cursor.execute(
            "SELECT emp_id, first_name||' '||last_name FROM employees "
            "WHERE status='ACTIVE' ORDER BY first_name"
        )
        employees = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]
        cursor.close(); conn.close()
        return jsonify({"departments": depts, "employees": employees})
    except Exception as e:
        return jsonify({"error": str(e)}), 500