
from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

app = Flask(__name__)
app.secret_key = "attendance_secret_key"

# ---------------- ADMIN CREDENTIALS ----------------
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin123"

# ---------------- DATABASE CONNECTION ----------------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- CREATE TABLES ----------------
def create_table():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            roll TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            status TEXT
        )
    """)

    conn.commit()
    conn.close()

create_table()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Admin login
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session.clear()
            session["admin"] = True
            return redirect("/admin")

        # Student login
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM students WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_roll"] = user["roll"]
            return redirect("/student")
        else:
            return "Invalid Email or Password"

    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        roll = request.form["roll"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        conn = get_db()
        conn.execute(
            "INSERT INTO students (name, roll, email, password) VALUES (?, ?, ?, ?)",
            (name, roll, email, password)
        )
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("register.html")

# ---------------- STUDENT DASHBOARD ----------------
@app.route("/student")
def student_dashboard():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT date, status FROM attendance WHERE student_id = ? ORDER BY date DESC",
        (session["user_id"],)
    )
    attendance_records = cursor.fetchall()

    conn.close()

    return render_template(
        "student_dashboard.html",
        name=session["user_name"],
        roll=session["user_roll"],
        records=attendance_records
    )

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
def admin_dashboard():
    if "admin" not in session:
        return redirect("/")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    today = str(date.today())

    cursor.execute(
        "SELECT COUNT(DISTINCT student_id) FROM attendance WHERE date = ? AND status = 'Present'",
        (today,)
    )
    present_today = cursor.fetchone()[0]

    absent_today = total_students - present_today

    cursor.execute("""
        SELECT students.name, students.roll, attendance.status
        FROM students
        LEFT JOIN attendance
        ON students.id = attendance.student_id AND attendance.date = ?
    """, (today,))
    records = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        present_today=present_today,
        absent_today=absent_today,
        records=records,
        today=today
    )

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
