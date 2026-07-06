from flask import Blueprint, request, session, jsonify
from config import get_connection

employees_bp = Blueprint("employees", __name__)


def require_admin():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    if session.get("role") not in ("ADMIN", "HR"):
        return jsonify({"error": "Access denied"}), 403
    return None


@employees_bp.route("/api/employees")
def list_employees():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    role = session.get("role")

    # ── FIX 1: Employees can only see their own profile ──────────────────────
    if role == "EMPLOYEE":
        emp_id = session.get("emp_id")
        if not emp_id:
            return jsonify({"employees": [], "departments": []})
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.emp_id,
                       e.first_name || ' ' || e.last_name,
                       e.email,
                       NVL(d.dept_name, '—'),
                       NVL(dg.title, '—'),
                       e.salary,
                       NVL(m.first_name || ' ' || m.last_name, '—'),
                       e.status
                FROM employees e
                LEFT JOIN departments  d  ON e.dept_id    = d.dept_id
                LEFT JOIN designations dg ON e.desig_id   = dg.desig_id
                LEFT JOIN employees    m  ON e.manager_id = m.emp_id
                WHERE e.emp_id = :1
            """, [emp_id])
            row = cursor.fetchone()
            employees = []
            if row:
                employees = [{
                    "emp_id":      row[0], "name":        row[1],
                    "email":       row[2], "dept":        row[3],
                    "designation": row[4], "salary":      float(row[5]),
                    "manager":     row[6], "status":      row[7],
                }]
            cursor.close(); conn.close()
            return jsonify({"employees": employees, "departments": []})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ── Admin / HR: full list with filters ───────────────────────────────────
    search     = request.args.get("search", "").strip()
    dept       = request.args.get("dept",   "").strip()
    status_flt = request.args.get("status", "").strip()

    try:
        conn   = get_connection()
        cursor = conn.cursor()

        conditions = ["1=1"]
        params     = []

        if search:
            conditions.append(
                f"(LOWER(e.first_name || ' ' || e.last_name) LIKE LOWER(:{len(params)+1}) "
                f"OR LOWER(e.email) LIKE LOWER(:{len(params)+2}))"
            )
            params.append(f"%{search}%")
            params.append(f"%{search}%")

        if dept:
            conditions.append(f"e.dept_id = :{len(params)+1}")
            params.append(int(dept))

        if status_flt:
            conditions.append(f"e.status = :{len(params)+1}")
            params.append(status_flt)

        where = " AND ".join(conditions)
        query = f"""
            SELECT e.emp_id,
                   e.first_name || ' ' || e.last_name,
                   e.email,
                   NVL(d.dept_name, '—'),
                   NVL(dg.title, '—'),
                   e.salary,
                   NVL(m.first_name || ' ' || m.last_name, '—'),
                   e.status
            FROM employees e
            LEFT JOIN departments  d  ON e.dept_id    = d.dept_id
            LEFT JOIN designations dg ON e.desig_id   = dg.desig_id
            LEFT JOIN employees    m  ON e.manager_id = m.emp_id
            WHERE {where}
            ORDER BY e.emp_id
        """
        cursor.execute(query, params)

        employees = [
            {
                "emp_id":      r[0], "name":        r[1],
                "email":       r[2], "dept":        r[3],
                "designation": r[4], "salary":      float(r[5]),
                "manager":     r[6], "status":      r[7],
            }
            for r in cursor.fetchall()
        ]

        cursor.execute("SELECT dept_id, dept_name FROM departments ORDER BY dept_name")
        departments = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]

        cursor.close(); conn.close()
        return jsonify({"employees": employees, "departments": departments})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@employees_bp.route("/api/employees/form-data")
def form_data():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT dept_id, dept_name FROM departments ORDER BY dept_name")
        departments = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]
        cursor.execute("SELECT desig_id, title FROM designations ORDER BY title")
        designations = [{"id": r[0], "title": r[1]} for r in cursor.fetchall()]
        cursor.execute(
            "SELECT emp_id, first_name || ' ' || last_name "
            "FROM employees WHERE status='ACTIVE' ORDER BY first_name"
        )
        managers = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]
        cursor.close(); conn.close()
        return jsonify({"departments": departments, "designations": designations, "managers": managers})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@employees_bp.route("/api/employees/<int:emp_id>")
def get_employee(emp_id):
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    # ── FIX 1: Employees can only fetch their own profile ────────────────────
    if session.get("role") == "EMPLOYEE":
        if session.get("emp_id") != emp_id:
            return jsonify({"error": "Access denied"}), 403

    try:
        conn   = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT e.emp_id, e.first_name, e.last_name, e.email, e.phone,
                   e.salary, TO_CHAR(e.hire_date,'YYYY-MM-DD'),
                   e.dept_id, e.desig_id, e.manager_id, e.status,
                   NVL(d.dept_name,'—'), NVL(dg.title,'—'), NVL(dg.grade,'—'),
                   NVL(m.first_name||' '||m.last_name,'—')
            FROM employees e
            LEFT JOIN departments  d  ON e.dept_id   = d.dept_id
            LEFT JOIN designations dg ON e.desig_id  = dg.desig_id
            LEFT JOIN employees    m  ON e.manager_id = m.emp_id
            WHERE e.emp_id = :1
        """, [emp_id])
        row = cursor.fetchone()
        if not row:
            cursor.close(); conn.close()
            return jsonify({"error": "Employee not found"}), 404

        employee = {
            "emp_id": row[0], "first_name": row[1], "last_name": row[2],
            "email": row[3], "phone": row[4] or "",
            "salary": float(row[5]),
            "hire_date": row[6] or "", "dept_id": row[7],
            "desig_id": row[8], "manager_id": row[9] or "",
            "status": row[10], "dept_name": row[11],
            "designation": row[12], "grade": row[13], "manager": row[14],
        }

        cursor.execute("""
            SELECT TO_CHAR(att_date,'DD Mon YYYY'), status,
            TO_CHAR(check_in,'HH24:MI'), TO_CHAR(check_out,'HH24:MI'), NVL(overtime_hr,0)
            FROM attendance WHERE emp_id = :1
            ORDER BY att_date DESC FETCH FIRST 10 ROWS ONLY
        """, [emp_id])
        attendance = [
            {"date": r[0], "status": r[1], "check_in": r[2] or "—",
             "check_out": r[3] or "—", "overtime": float(r[4])}
            for r in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT pay_month, pay_year, basic_pay, bonus, deductions, tax, net_pay, status
            FROM payroll WHERE emp_id = :1
            ORDER BY pay_year DESC, pay_id DESC FETCH FIRST 12 ROWS ONLY
        """, [emp_id])
        payroll = [
            {"month": r[0], "year": r[1], "basic": float(r[2] or 0),
             "bonus": float(r[3] or 0), "deductions": float(r[4] or 0),
             "tax": float(r[5] or 0), "net": float(r[6] or 0), "status": r[7]}
            for r in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT old_salary, new_salary, TO_CHAR(changed_at,'DD Mon YYYY'), changed_by
            FROM salary_history WHERE emp_id = :1 ORDER BY changed_at DESC
        """, [emp_id])
        salary_history = [
            {"old": float(r[0] or 0), "new": float(r[1] or 0), "date": r[2], "by": r[3] or "—"}
            for r in cursor.fetchall()
        ]

        cursor.execute("SELECT dept_id, dept_name FROM departments ORDER BY dept_name")
        departments = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]
        cursor.execute("SELECT desig_id, title FROM designations ORDER BY title")
        designations = [{"id": r[0], "title": r[1]} for r in cursor.fetchall()]
        cursor.execute(
            "SELECT emp_id, first_name||' '||last_name FROM employees "
            "WHERE status='ACTIVE' AND emp_id != :1 ORDER BY first_name", [emp_id]
        )
        managers = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]

        cursor.close(); conn.close()
        return jsonify({
            "employee": employee, "attendance": attendance,
            "payroll": payroll, "salary_history": salary_history,
            "departments": departments, "designations": designations, "managers": managers,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@employees_bp.route("/api/employees", methods=["POST"])
def add_employee():
    err = require_admin()
    if err: return err
    data = request.get_json()
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        mgr = data.get("manager_id")
        cursor.execute(
            "INSERT INTO employees "
            "(first_name,last_name,email,phone,salary,hire_date,dept_id,desig_id,manager_id) "
            "VALUES (:1,:2,:3,:4,:5,TO_DATE(:6,'YYYY-MM-DD'),:7,:8,:9)",
            [
                data.get("first_name","").strip(),
                data.get("last_name","").strip(),
                data.get("email","").strip(),
                data.get("phone","").strip() or None,
                float(data.get("salary", 0)),
                data.get("hire_date") or None,
                int(data.get("dept_id")),
                int(data.get("desig_id")),
                int(mgr) if mgr else None,
            ]
        )
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@employees_bp.route("/api/employees/<int:emp_id>", methods=["PUT"])
def update_employee(emp_id):
    err = require_admin()
    if err: return err
    data = request.get_json()
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        mgr = data.get("manager_id")
        cursor.execute(
            "UPDATE employees SET "
            "first_name=:1, last_name=:2, email=:3, phone=:4, salary=:5, "
            "hire_date=TO_DATE(:6,'YYYY-MM-DD'), dept_id=:7, desig_id=:8, manager_id=:9 "
            "WHERE emp_id=:10",
            [
                data.get("first_name","").strip(),
                data.get("last_name","").strip(),
                data.get("email","").strip(),
                data.get("phone","").strip() or None,
                float(data.get("salary", 0)),
                data.get("hire_date") or None,
                int(data.get("dept_id")),
                int(data.get("desig_id")),
                int(mgr) if mgr else None,
                emp_id,
            ]
        )
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@employees_bp.route("/api/employees/<int:emp_id>/salary", methods=["PATCH"])
def update_salary(emp_id):
    err = require_admin()
    if err: return err
    data   = request.get_json()
    salary = data.get("salary")
    if not salary or float(salary) <= 0:
        return jsonify({"success": False, "message": "Invalid salary."})
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE employees SET salary = :1 WHERE emp_id = :2", [float(salary), emp_id])
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@employees_bp.route("/api/employees/<int:emp_id>/status", methods=["PATCH"])
def update_status(emp_id):
    err = require_admin()
    if err: return err
    data       = request.get_json()
    new_status = data.get("status", "").upper()
    if new_status not in ("ACTIVE", "INACTIVE"):
        return jsonify({"success": False, "message": "Invalid status."})
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE employees SET status = :1 WHERE emp_id = :2", [new_status, emp_id])
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@employees_bp.route("/api/employees/<int:emp_id>", methods=["DELETE"])
def deactivate_employee(emp_id):
    err = require_admin()
    if err: return err
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE employees SET status='INACTIVE' WHERE emp_id = :1", [emp_id])
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500