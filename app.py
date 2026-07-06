from flask import Flask, send_from_directory, session, redirect
from routes.auth import auth_bp
from routes.employees import employees_bp
from routes.attendance import attendance_bp
from routes.payroll import payroll_bp
from routes.reports import reports_bp
from routes.dashboard import dashboard_bp
from routes.showcase import showcase_bp
import os

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = "hrms_secret_key_2024"

app.register_blueprint(auth_bp)
app.register_blueprint(employees_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(payroll_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(showcase_bp)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')


def serve(subfolder, filename):
    if subfolder:
        return send_from_directory(os.path.join(TEMPLATES_DIR, subfolder), filename)
    return send_from_directory(TEMPLATES_DIR, filename)


@app.route("/")
def index():
    return redirect("/dashboard" if "user_id" in session else "/login")


@app.route("/login")
def login_page():
    return serve(None, "login.html")

@app.route("/change-password")
def change_password_page():
    if "user_id" not in session:
        return redirect("/login")
    return serve(None, "change_password.html")

@app.route("/dashboard")
def dashboard_page():
    if "user_id" not in session:
        return redirect("/login")
    return serve(None, "dashboard.html")

@app.route("/employees")
def employees_list_page():
    if "user_id" not in session:
        return redirect("/login")
    return serve("employees", "list.html")

@app.route("/employees/add")
def add_employee_page():
    if "user_id" not in session:
        return redirect("/login")
    return serve("employees", "form.html")

@app.route("/employees/edit/<int:emp_id>")
def edit_employee_page(emp_id):
    if "user_id" not in session:
        return redirect("/login")
    return serve("employees", "form.html")

@app.route("/employees/view/<int:emp_id>")
def view_employee_page(emp_id):
    if "user_id" not in session:
        return redirect("/login")
    return serve("employees", "view.html")

@app.route("/attendance")
def attendance_page():
    if "user_id" not in session:
        return redirect("/login")
    return serve("attendance", "list.html")

@app.route("/attendance/mark")
def mark_attendance_page():
    if "user_id" not in session:
        return redirect("/login")
    return serve("attendance", "mark.html")

@app.route("/payroll")
def payroll_page():
    if "user_id" not in session:
        return redirect("/login")
    return serve("payroll", "list.html")

@app.route("/payroll/generate")
def generate_payroll_page():
    if "user_id" not in session:
        return redirect("/login")
    return serve("payroll", "generate.html")

@app.route("/reports")
def reports_page():
    if "user_id" not in session:
        return redirect("/login")
    return serve("reports", "index.html")

@app.route("/reports/department-summary")
def dept_summary_page():
    if "user_id" not in session:
        return redirect("/login")
    return serve("reports", "dept_summary.html")

@app.route("/reports/attendance-summary")
def attendance_summary_page():
    if "user_id" not in session:
        return redirect("/login")
    return serve("reports", "attendance_summary.html")

@app.route("/reports/payroll-summary")
def payroll_summary_page():
    if "user_id" not in session:
        return redirect("/login")
    return serve("reports", "payroll_summary.html")

@app.route("/reports/audit-log")
def audit_log_page():
    if "user_id" not in session:
        return redirect("/login")
    return serve("reports", "audit_log.html")

@app.route("/showcase")
def showcase_page():
    if "user_id" not in session:
        return redirect("/login")
    return serve(None, "showcase.html")


if __name__ == "__main__":
    app.run(debug=True)