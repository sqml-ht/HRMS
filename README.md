# HRMS | HR Management System

A full-stack **Human Resource Management System** built with **Flask** and **Oracle XE**, designed primarily as a deep-dive into advanced relational database concepts. The application itself (employee records, departments, payroll, leave management, etc.) is the vehicle; the real focus is demonstrating strong, production-style SQL and database design.

## Project Focus

This project was built to practice and demonstrate the following database engineering concepts in a real application context:

- **Query fundamentals** / `WHERE`, `ORDER BY`, `GROUP BY`
- **JOINs** / INNER, LEFT, RIGHT, FULL
- **Subqueries / nested queries**
- **Normalization** / 1NF, 2NF, 3NF
- **ER Diagram + Relational Schema**
- **Stored Procedures**
- **Triggers**
- **Views** (virtual tables)
- **Transactions** / `COMMIT`, `ROLLBACK`, `SAVEPOINT`
- **Indexing** for performance optimization
- **Constraints** / `PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE`, `NOT NULL`, `CHECK`
- **ACID properties** demonstration

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Database | Oracle Database Express Edition (XE) |
| DB Driver | `python-oracledb` (or `cx_Oracle`) |
| Frontend | HTML, CSS, Jinja2 templates |
| IDE | VS Code |

## Project Structure

```
Project/
├── .venv/
├── __pycache__/
├── projectdv/
├── routes/
│   ├── __pycache__
│   ├── attendance.py
│   ├── auth.py
│   ├── dashboard.py
│   ├── payroll.py
│   ├── employees.py
│   ├── reports.py
│   └── showcase.py
│
├── static/
│   ├── base.js           
│   ├── script.js
│   ├── sidebar.js         
│   └── style.css        
│
├── templates/
│   ├── attendance/
│   ├── employees/
│   ├── payroll/
│   ├── reports/
│   ├── base.html
│   ├── change_password.html
│   ├── dashboard.html
│   ├── showcase.html
│   └── login.html
│
├── app.py
├── config.py
├── .gitignore
├── ProjectDB.sql
└── README.md
```

> Adjust this tree to match your actual folder layout.

## Connecting Oracle XE to the Project in VS Code

This section walks through setting up Oracle XE locally and connecting it to both **VS Code** (for browsing/querying the DB) and the **Flask app** (for the actual application connection).

### Step 1 / Install Oracle XE

1. Download **Oracle Database XE** from the [official Oracle site](https://www.oracle.com/database/technologies/xe-downloads.html).
2. Install it (on Linux, follow the `.deb`/`.rpm` instructions for your distro; on Windows/Mac use the installer).
3. During install, you'll set a password for the `SYS` and `SYSTEM` admin accounts; remember it.
4. By default, Oracle XE runs on port **1521**, with the default service name **`XEPDB1`** (pluggable database) or **`XE`** (container database), depending on version.

Verify it's running:

```bash
lsnrctl status
```

### Step 2 / Create a dedicated app user/schema

Connect as SYSTEM using SQL*Plus or SQLcl:

```bash
sqlplus system/your_password@localhost:1521/XEPDB1
```

Then create a user for the HRMS app:

```sql
CREATE USER hrms_user IDENTIFIED BY hrms_password;
GRANT CONNECT, RESOURCE, DBA TO hrms_user;
ALTER USER hrms_user QUOTA UNLIMITED ON USERS;
```

Log in as the new user to confirm it works:

```bash
sqlplus hrms_user/hrms_password@localhost:1521/XEPDB1
```

### Step 3 / Install VS Code extensions for Oracle

In VS Code, install:

- **Oracle Developer Tools for VS Code** (by Oracle) lets you browse schemas, tables, and run SQL directly from the editor.
- **SQLTools** (optional alternative) with the Oracle driver.

Once installed:
1. Open the Oracle extension panel (elephant/database icon in the sidebar).
2. Click **Create Connection**.
3. Fill in:
   - **Hostname:** `localhost`
   - **Port:** `1521`
   - **Service Name:** `XEPDB1` (or `XE`)
   - **Username:** `hrms_user`
   - **Password:** `hrms_password`
4. Test the connection, then save it.

You can now browse tables, run queries, and execute your `.sql` scripts directly from VS Code.

### Step 4 / Connect Oracle XE to the Flask app

Install the Python driver:

```bash
pip install python-oracledb
```

Create a `.env` file in your project root (and make sure it's in `.gitignore`):

```
DB_USER=hrms_user
DB_PASSWORD=hrms_password
DB_DSN=localhost:1521/XEPDB1
```

In your Flask app's database config (e.g. `app/db.py`):

```python
import os
import oracledb
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    connection = oracledb.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dsn=os.getenv("DB_DSN")
    )
    return connection
```

Test the connection:

```python
if __name__ == "__main__":
    conn = get_connection()
    print("Connected to Oracle XE:", conn.version)
    conn.close()
```

### Step 5 / Run the schema scripts

From SQL*Plus, VS Code's Oracle extension, or SQLcl, run your setup scripts in order:

```sql
@database/schema.sql
@database/procedures.sql
@database/triggers.sql
@database/views.sql
@database/seed_data.sql
```

## Running the Project

```bash
# clone the repo
git clone https://github.com/yourusername/hrms-flask-oraclexe.git
cd hrms-flask-oraclexe

# create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# install dependencies
pip install -r requirements.txt

# set up your .env file (see Step 4 above)

# run the app
python run.py
```

The app should now be running at `http://127.0.0.1:5000`.

## Database Design Highlights

- **ER Diagram & Relational Schema** available in `/database/` (add your diagram image/PDF here).
- Tables are normalized to **3NF** to eliminate redundancy while keeping query complexity meaningful for JOIN practice.
- **Views** are used to simplify complex reporting queries (e.g. employee-department-salary summaries).
- **Stored procedures** handle multi-step operations like processing payroll or onboarding an employee.
- **Triggers** enforce business rules (e.g. auto-logging salary changes, preventing invalid updates).
- **Transactions** are demonstrated in operations that must be atomic (e.g. transferring an employee between departments), using `SAVEPOINT` and `ROLLBACK` for partial failure handling.
- **Indexes** are added on frequently queried/joined columns (e.g. `employee_id`, `department_id`) to demonstrate performance optimization.

## Notes

- This project is for educational purposes, focused on demonstrating relational database design and advanced SQL skills within a working full-stack application.
- Contributions, suggestions, and forks are welcome.
