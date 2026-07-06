-- ============================================================
-- HRMS SCHEMA for Oracle 21c (XEPDB1)
-- Run this entire file in SQL Developer as SYSTEM
-- ============================================================

-- ==========================================
-- DROP VIEWS
-- ==========================================

BEGIN EXECUTE IMMEDIATE 'DROP VIEW vw_attendance_summary'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP VIEW vw_dept_payroll_summary'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP VIEW vw_employee_details'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

-- ==========================================
-- DROP TABLES
-- ==========================================

BEGIN EXECUTE IMMEDIATE 'DROP TABLE employee_archive CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP TABLE audit_log CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP TABLE app_users CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP TABLE salary_history CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP TABLE payroll CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP TABLE attendance CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP TABLE employees CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP TABLE designations CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP TABLE departments CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

-- ==========================================
-- DROP TRIGGERS
-- ==========================================

BEGIN EXECUTE IMMEDIATE 'DROP TRIGGER trg_validate_salary'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP TRIGGER trg_salary_history'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP TRIGGER trg_create_login'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP TRIGGER trg_archive_employee'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP TRIGGER trg_audit_employees'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

-- ==========================================
-- DROP PROCEDURES
-- ==========================================

BEGIN EXECUTE IMMEDIATE 'DROP PROCEDURE sp_generate_payroll'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP PROCEDURE sp_dept_salary_raise'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

-- ==========================================
-- DROP INDEXES
-- ==========================================

BEGIN EXECUTE IMMEDIATE 'DROP INDEX idx_emp_dept'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP INDEX idx_emp_status'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP INDEX idx_att_emp_date'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP INDEX idx_pay_emp_year'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP INDEX idx_audit_date'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

-- ==========================================
-- DROP SEQUENCES
-- ==========================================

BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE emp_seq'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE dept_seq'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE pay_seq'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE att_seq'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE audit_seq'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE user_seq'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

-- ==========================================
-- DROP SYNONYMS
-- ==========================================

BEGIN EXECUTE IMMEDIATE 'DROP SYNONYM emp'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP SYNONYM dept'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP SYNONYM pay'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP PUBLIC SYNONYM hrms_employees'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

-- ==========================================
-- DROP ROLES
-- ==========================================

BEGIN EXECUTE IMMEDIATE 'DROP ROLE hr_manager_role'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP ROLE dept_manager_role'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

BEGIN EXECUTE IMMEDIATE 'DROP ROLE employee_role'; EXCEPTION WHEN OTHERS THEN NULL; END;
/


-- ============================================================
-- 1. SEQUENCES
-- ============================================================
CREATE SEQUENCE emp_seq    START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE dept_seq   START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE pay_seq    START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE att_seq    START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE audit_seq  START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE user_seq   START WITH 1 INCREMENT BY 1 NOCACHE;

-- ============================================================
-- 2. TABLES
-- ============================================================

CREATE TABLE departments (
    dept_id     NUMBER DEFAULT dept_seq.NEXTVAL PRIMARY KEY,
    dept_name   VARCHAR2(100) NOT NULL,
    location    VARCHAR2(100),
    created_at  DATE DEFAULT SYSDATE
);

CREATE TABLE designations (
    desig_id    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title       VARCHAR2(100) NOT NULL,
    grade       VARCHAR2(10)
);

CREATE TABLE employees (
    emp_id      NUMBER DEFAULT emp_seq.NEXTVAL PRIMARY KEY,
    first_name  VARCHAR2(50)  NOT NULL,
    last_name   VARCHAR2(50)  NOT NULL,
    email       VARCHAR2(100) UNIQUE NOT NULL,
    phone       VARCHAR2(20),
    hire_date   DATE DEFAULT SYSDATE,
    salary      NUMBER(10,2)  NOT NULL,
    dept_id     NUMBER REFERENCES departments(dept_id),
    desig_id    NUMBER REFERENCES designations(desig_id),
    manager_id  NUMBER REFERENCES employees(emp_id),  -- SELF JOIN
    status      VARCHAR2(20) DEFAULT 'ACTIVE'
);

CREATE TABLE attendance (
    att_id      NUMBER DEFAULT att_seq.NEXTVAL PRIMARY KEY,
    emp_id      NUMBER REFERENCES employees(emp_id),
    att_date    DATE DEFAULT SYSDATE,
    status      VARCHAR2(20) DEFAULT 'PRESENT',
    check_in    TIMESTAMP,
    check_out   TIMESTAMP,
    overtime_hr NUMBER(4,2) DEFAULT 0
);

CREATE TABLE payroll (
    pay_id      NUMBER DEFAULT pay_seq.NEXTVAL PRIMARY KEY,
    emp_id      NUMBER REFERENCES employees(emp_id),
    pay_month   VARCHAR2(20) NOT NULL,
    pay_year    NUMBER(4)    NOT NULL,
    basic_pay   NUMBER(10,2),
    bonus       NUMBER(10,2) DEFAULT 0,
    deductions  NUMBER(10,2) DEFAULT 0,
    tax         NUMBER(10,2) DEFAULT 0,
    net_pay     NUMBER(10,2),
    generated_at DATE DEFAULT SYSDATE,
    status      VARCHAR2(20) DEFAULT 'PENDING'
);

CREATE TABLE salary_history (
    history_id  NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    emp_id      NUMBER REFERENCES employees(emp_id),
    old_salary  NUMBER(10,2),
    new_salary  NUMBER(10,2),
    changed_at  DATE DEFAULT SYSDATE,
    changed_by  VARCHAR2(100)
);

CREATE TABLE app_users (
    user_id     NUMBER DEFAULT user_seq.NEXTVAL PRIMARY KEY,
    username    VARCHAR2(50) UNIQUE NOT NULL,
    password    VARCHAR2(255) NOT NULL,
    emp_id      NUMBER REFERENCES employees(emp_id),
    role        VARCHAR2(30) DEFAULT 'EMPLOYEE',
    is_active   NUMBER(1) DEFAULT 1,
    created_at  DATE DEFAULT SYSDATE
);

CREATE TABLE audit_log (
    audit_id    NUMBER DEFAULT audit_seq.NEXTVAL PRIMARY KEY,
    table_name  VARCHAR2(50),
    operation   VARCHAR2(10),
    record_id   NUMBER,
    old_value   VARCHAR2(500),
    new_value   VARCHAR2(500),
    changed_by  VARCHAR2(100) DEFAULT USER,
    changed_at  DATE DEFAULT SYSDATE
);

CREATE TABLE employee_archive (
    archive_id  NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    emp_id      NUMBER,
    first_name  VARCHAR2(50),
    last_name   VARCHAR2(50),
    email       VARCHAR2(100),
    salary      NUMBER(10,2),
    dept_id     NUMBER,
    deleted_at  DATE DEFAULT SYSDATE,
    deleted_by  VARCHAR2(100) DEFAULT USER
);

ALTER TABLE employees
ADD CONSTRAINT chk_employee_salary
CHECK (salary > 0);

ALTER TABLE employees
ADD CONSTRAINT chk_employee_status
CHECK (status IN ('ACTIVE','INACTIVE'));

ALTER TABLE attendance
ADD CONSTRAINT chk_attendance_status
CHECK (status IN ('PRESENT','ABSENT','LATE'));

ALTER TABLE app_users
ADD CONSTRAINT chk_user_active
CHECK (is_active IN (0,1));


-- ============================================================
-- 3. SYNONYMS
-- ============================================================
-- Private synonyms (current user)
CREATE SYNONYM EMP  FOR employees;
CREATE SYNONYM DEPT FOR departments;
CREATE SYNONYM PAY  FOR payroll;

-- Public synonym (all users can use)
CREATE PUBLIC SYNONYM HRMS_EMPLOYEES FOR SYSTEM.employees;

-- ============================================================
-- 4. TRIGGERS
-- ============================================================

-- BEFORE INSERT: Validate salary > 0
CREATE OR REPLACE TRIGGER trg_validate_salary
BEFORE INSERT OR UPDATE ON employees
FOR EACH ROW
BEGIN
    IF :NEW.salary <= 0 THEN
        RAISE_APPLICATION_ERROR(-20001, 'Salary must be greater than zero.');
    END IF;
    IF :NEW.email NOT LIKE '%@%.%' THEN
        RAISE_APPLICATION_ERROR(-20002, 'Invalid email format.');
    END IF;
END;
/

-- AFTER UPDATE salary: Log to salary_history
CREATE OR REPLACE TRIGGER trg_salary_history
AFTER UPDATE OF salary ON employees
FOR EACH ROW
BEGIN
    INSERT INTO salary_history (emp_id, old_salary, new_salary, changed_by)
    VALUES (:OLD.emp_id, :OLD.salary, :NEW.salary, USER);
END;
/

-- AFTER INSERT employee: Create login account automatically
CREATE OR REPLACE TRIGGER trg_create_login
AFTER INSERT ON employees
FOR EACH ROW
DECLARE
    v_username VARCHAR2(50);
BEGIN
    v_username := LOWER(:NEW.first_name) || '.' || LOWER(:NEW.last_name);
    INSERT INTO app_users (username, password, emp_id, role)
    VALUES (v_username, 'changeme123', :NEW.emp_id, 'EMPLOYEE');
END;
/

-- AFTER DELETE employee: Archive before deleting
CREATE OR REPLACE TRIGGER trg_archive_employee
BEFORE DELETE ON employees
FOR EACH ROW
BEGIN
    INSERT INTO employee_archive
        (emp_id, first_name, last_name, email, salary, dept_id)
    VALUES
        (:OLD.emp_id, :OLD.first_name, :OLD.last_name,
         :OLD.email, :OLD.salary, :OLD.dept_id);
END;
/

-- AFTER INSERT/UPDATE/DELETE audit trigger on employees
CREATE OR REPLACE TRIGGER trg_audit_employees
AFTER INSERT OR UPDATE OR DELETE ON employees
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        INSERT INTO audit_log (table_name, operation, record_id, new_value)
        VALUES ('EMPLOYEES', 'INSERT', :NEW.emp_id,
                :NEW.first_name || ' ' || :NEW.last_name || ' sal:' || :NEW.salary);
    ELSIF UPDATING THEN
        INSERT INTO audit_log (table_name, operation, record_id, old_value, new_value)
        VALUES ('EMPLOYEES', 'UPDATE', :NEW.emp_id,
                :OLD.first_name || ' sal:' || :OLD.salary,
                :NEW.first_name || ' sal:' || :NEW.salary);
    ELSIF DELETING THEN
        INSERT INTO audit_log (table_name, operation, record_id, old_value)
        VALUES ('EMPLOYEES', 'DELETE', :OLD.emp_id,
                :OLD.first_name || ' ' || :OLD.last_name);
    END IF;
END;
/

-- ============================================================
-- 5. ORACLE ROLES & PRIVILEGES
-- ============================================================
CREATE ROLE hr_manager_role;
CREATE ROLE dept_manager_role;
CREATE ROLE employee_role;

GRANT SELECT, INSERT, UPDATE, DELETE ON employees   TO hr_manager_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON payroll     TO hr_manager_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON attendance  TO hr_manager_role;
GRANT SELECT ON audit_log                           TO hr_manager_role;

GRANT SELECT, UPDATE ON employees  TO dept_manager_role;
GRANT SELECT, INSERT ON attendance TO dept_manager_role;
GRANT SELECT ON payroll            TO dept_manager_role;

GRANT SELECT ON employees  TO employee_role;
GRANT SELECT ON attendance TO employee_role;
GRANT SELECT ON payroll    TO employee_role;

-- ============================================================
-- 6. SEED DATA
-- ============================================================
INSERT INTO departments (dept_name, location) VALUES ('Human Resources', 'Floor 1');
INSERT INTO departments (dept_name, location) VALUES ('Engineering',     'Floor 2');
INSERT INTO departments (dept_name, location) VALUES ('Finance',         'Floor 3');
INSERT INTO departments (dept_name, location) VALUES ('Marketing',       'Floor 4');

INSERT INTO designations (title, grade) VALUES ('CEO',               'G1');
INSERT INTO designations (title, grade) VALUES ('HR Manager',        'G2');
INSERT INTO designations (title, grade) VALUES ('Senior Engineer',   'G3');
INSERT INTO designations (title, grade) VALUES ('Junior Engineer',   'G4');
INSERT INTO designations (title, grade) VALUES ('Accountant',        'G3');

-- Insert employees (triggers will auto-create logins)
INSERT INTO employees (first_name, last_name, email, phone, salary, dept_id, desig_id)
VALUES ('Alice', 'Johnson', 'alice@hrms.com', '0300-1111111', 150000, 1, 1);

INSERT INTO employees (first_name, last_name, email, phone, salary, dept_id, desig_id, manager_id)
VALUES ('Bob', 'Smith', 'bob@hrms.com', '0300-2222222', 90000, 2, 2, 1);

INSERT INTO employees (first_name, last_name, email, phone, salary, dept_id, desig_id, manager_id)
VALUES ('Carol', 'White', 'carol@hrms.com', '0300-3333333', 75000, 2, 3, 2);

INSERT INTO employees (first_name, last_name, email, phone, salary, dept_id, desig_id, manager_id)
VALUES ('David', 'Brown', 'david@hrms.com', '0300-4444444', 60000, 3, 5, 1);

INSERT INTO employees (first_name, last_name, email, phone, salary, dept_id, desig_id, manager_id)
VALUES ('Eva', 'Green', 'eva@hrms.com', '0300-5555555', 55000, 4, 4, 2);

-- Add attendance records
INSERT INTO attendance (emp_id, att_date, status, check_in, check_out)
VALUES (1, SYSDATE-1, 'PRESENT', SYSTIMESTAMP-1/24, SYSTIMESTAMP);
INSERT INTO attendance (emp_id, att_date, status, check_in, check_out)
VALUES (2, SYSDATE-1, 'PRESENT', SYSTIMESTAMP-1/24, SYSTIMESTAMP);
INSERT INTO attendance (emp_id, att_date, status)
VALUES (3, SYSDATE-1, 'ABSENT');

COMMIT;

INSERT INTO app_users (username, password, role, is_active)
VALUES ('admin', 'Admin1234', 'ADMIN', 1);
COMMIT;
-- ============================================================
-- HRMS ADDITIONAL SQL — Views, Indexes, Stored Procedures
-- Run in SQL Developer after the main schema
-- ============================================================

-- ============================================================
-- 1. VIEWS (Virtual Tables)
-- ============================================================

-- View: Active employee full info (JOIN across 4 tables)
CREATE OR REPLACE VIEW vw_employee_details AS
SELECT
    e.emp_id,
    e.first_name || ' ' || e.last_name   AS full_name,
    e.email,
    e.phone,
    e.salary,
    e.hire_date,
    e.status,
    d.dept_name,
    dg.title                              AS designation,
    dg.grade,
    m.first_name || ' ' || m.last_name   AS manager_name
FROM employees e
LEFT JOIN departments  d   ON e.dept_id   = d.dept_id
LEFT JOIN designations dg  ON e.desig_id  = dg.desig_id
LEFT JOIN employees    m   ON e.manager_id = m.emp_id
WHERE e.status = 'ACTIVE';

-- View: Monthly payroll summary per department
CREATE OR REPLACE VIEW vw_dept_payroll_summary AS
SELECT
    d.dept_name,
    p.pay_month,
    p.pay_year,
    COUNT(p.pay_id)      AS employee_count,
    SUM(p.basic_pay)     AS total_basic,
    SUM(p.bonus)         AS total_bonus,
    SUM(p.deductions)    AS total_deductions,
    SUM(p.net_pay)       AS total_net_pay
FROM payroll p
JOIN employees   e ON p.emp_id  = e.emp_id
JOIN departments d ON e.dept_id = d.dept_id
GROUP BY d.dept_name, p.pay_month, p.pay_year;

-- View: Attendance summary per employee this month
CREATE OR REPLACE VIEW vw_attendance_summary AS
SELECT
    e.emp_id,
    e.first_name || ' ' || e.last_name AS full_name,
    d.dept_name,
    COUNT(CASE WHEN a.status = 'PRESENT'  THEN 1 END) AS present_days,
    COUNT(CASE WHEN a.status = 'ABSENT'   THEN 1 END) AS absent_days,
    COUNT(CASE WHEN a.status = 'LATE'     THEN 1 END) AS late_days,
    NVL(SUM(a.overtime_hr), 0)                        AS total_overtime,
    ROUND(
        COUNT(CASE WHEN a.status = 'PRESENT' THEN 1 END) * 100.0
        / NULLIF(COUNT(a.att_id), 0), 1
    ) AS attendance_pct
FROM employees e
LEFT JOIN attendance  a ON e.emp_id  = a.emp_id
LEFT JOIN departments d ON e.dept_id = d.dept_id
WHERE e.status = 'ACTIVE'
GROUP BY e.emp_id, e.first_name, e.last_name, d.dept_name;

-- ============================================================
-- 2. INDEXES for Performance Optimization
-- ============================================================

-- Index on employees.dept_id (used in JOINs heavily)
CREATE INDEX idx_emp_dept    ON employees(dept_id);

-- Index on employees.status (filtered in almost every query)
CREATE INDEX idx_emp_status  ON employees(status);

-- Index on attendance.emp_id + att_date (most common filter)
CREATE INDEX idx_att_emp_date ON attendance(emp_id, att_date);

-- Index on payroll.emp_id + pay_year (payroll lookups)
CREATE INDEX idx_pay_emp_year ON payroll(emp_id, pay_year);

-- Index on audit_log.changed_at (ORDER BY in audit report)
CREATE INDEX idx_audit_date  ON audit_log(changed_at);

-- Unique index on app_users.username (already UNIQUE constraint)
-- (already enforced by constraint, shown here for clarity)

-- ============================================================
-- 3. STORED PROCEDURES
-- ============================================================

-- Procedure: Generate payroll for all active employees in a month
CREATE OR REPLACE PROCEDURE sp_generate_payroll (
    p_month IN VARCHAR2,
    p_year  IN NUMBER
) AS
    v_basic      employees.salary%TYPE;
    v_overtime   NUMBER;
    v_bonus      NUMBER;
    v_deductions NUMBER;
    v_tax        NUMBER;
    v_net        NUMBER;
    v_exists     NUMBER;
BEGIN
    FOR emp IN (SELECT emp_id, salary FROM employees WHERE status = 'ACTIVE') LOOP
        -- Skip if already generated
        SELECT COUNT(*) INTO v_exists
        FROM payroll
        WHERE emp_id = emp.emp_id
          AND UPPER(pay_month) = UPPER(p_month)
          AND pay_year = p_year;

        IF v_exists = 0 THEN
            v_basic := emp.salary;

            SELECT NVL(SUM(overtime_hr), 0) INTO v_overtime
            FROM attendance
            WHERE emp_id = emp.emp_id
              AND TO_CHAR(att_date, 'MON') = UPPER(SUBSTR(p_month, 1, 3))
              AND TO_CHAR(att_date, 'YYYY') = TO_CHAR(p_year);

            v_bonus      := v_overtime * 500;
            v_deductions := v_basic * 0.05;
            v_tax        := v_basic * 0.10;
            v_net        := v_basic + v_bonus - v_deductions - v_tax;

            INSERT INTO payroll (emp_id, pay_month, pay_year, basic_pay,
                                 bonus, deductions, tax, net_pay, status)
            VALUES (emp.emp_id, p_month, p_year, v_basic,
                    v_bonus, v_deductions, v_tax, v_net, 'PENDING');
        END IF;
    END LOOP;
    COMMIT;
    DBMS_OUTPUT.PUT_LINE('Payroll generated for ' || p_month || ' ' || p_year);
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        DBMS_OUTPUT.PUT_LINE('Error: ' || SQLERRM);
END sp_generate_payroll;
/

-- Procedure: Give salary raise to a department
CREATE OR REPLACE PROCEDURE sp_dept_salary_raise (
    p_dept_id      IN NUMBER,
    p_raise_pct    IN NUMBER   -- e.g. 10 means 10%
) AS
BEGIN
    SAVEPOINT before_raise;
    UPDATE employees
    SET salary = salary * (1 + p_raise_pct / 100)
    WHERE dept_id = p_dept_id AND status = 'ACTIVE';
    COMMIT;
    DBMS_OUTPUT.PUT_LINE('Raise of ' || p_raise_pct || '% applied to dept ' || p_dept_id);
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK TO before_raise;
        DBMS_OUTPUT.PUT_LINE('Error in raise: ' || SQLERRM);
END sp_dept_salary_raise;
/

-- ============================================================
-- 4. DEMONSTRATION QUERIES (ADBMS features shown)
-- ============================================================

-- 1. INNER JOIN: Employees with their departments and designations
SELECT e.first_name || ' ' || e.last_name AS name,
       d.dept_name, dg.title, dg.grade
FROM employees e
INNER JOIN departments  d  ON e.dept_id  = d.dept_id
INNER JOIN designations dg ON e.desig_id = dg.desig_id
WHERE e.status = 'ACTIVE';

-- 2. LEFT JOIN: Departments including those with no employees
SELECT d.dept_name, COUNT(e.emp_id) AS headcount
FROM departments d
LEFT JOIN employees e ON d.dept_id = e.dept_id AND e.status = 'ACTIVE'
GROUP BY d.dept_id, d.dept_name
ORDER BY headcount DESC;

-- 3. SELF JOIN: Employee and their manager
SELECT e.first_name || ' ' || e.last_name AS employee,
       m.first_name || ' ' || m.last_name AS manager
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.emp_id
WHERE e.status = 'ACTIVE';

-- FULL OUTER JOIN
SELECT
    e.first_name || ' ' || e.last_name AS employee_name,
    d.dept_name
FROM employees e
FULL OUTER JOIN departments d
ON e.dept_id = d.dept_id;

-- RIGHT JOIN
SELECT
    e.first_name || ' ' || e.last_name AS employee_name,
    d.dept_name
FROM employees e
RIGHT JOIN departments d
ON e.dept_id = d.dept_id;

-- 4. Subquery: Employees earning above company average
SELECT first_name, last_name, salary
FROM employees
WHERE status = 'ACTIVE'
  AND salary > (SELECT AVG(salary) FROM employees WHERE status = 'ACTIVE')
ORDER BY salary DESC;

-- 5. GROUP BY + HAVING: Departments with avg salary > 70000
SELECT d.dept_name, ROUND(AVG(e.salary), 2) AS avg_sal
FROM employees e JOIN departments d ON e.dept_id = d.dept_id
WHERE e.status = 'ACTIVE'
GROUP BY d.dept_name
HAVING AVG(e.salary) > 70000
ORDER BY avg_sal DESC;

-- 6. Use the views
SELECT * FROM vw_employee_details;
SELECT * FROM vw_dept_payroll_summary;
SELECT * FROM vw_attendance_summary ORDER BY attendance_pct DESC;

-- 7. Call stored procedures
EXEC sp_generate_payroll('January', 2025);
EXEC sp_dept_salary_raise(2, 10);  -- 10% raise for Engineering dept

-- 8. TRANSACTION demonstration
BEGIN
    SAVEPOINT sp_test;
    UPDATE employees SET salary = 999999 WHERE emp_id = 1;
    -- Simulate error condition → rollback
    ROLLBACK TO SAVEPOINT sp_test;
    COMMIT;
END;
/

UPDATE app_users SET password = 'Admin1234' WHERE username = 'alice.johnson';
COMMIT;


-- ==========================================
-- ACID DEMONSTRATION
-- ==========================================

BEGIN
    SAVEPOINT salary_test;

    UPDATE employees
    SET salary = salary + 5000
    WHERE emp_id = 1;

    UPDATE employees
    SET salary = salary - 5000
    WHERE emp_id = 2;

    ROLLBACK TO salary_test;

    COMMIT;
END;
/


