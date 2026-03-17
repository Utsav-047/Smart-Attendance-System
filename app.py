
from flask import Flask, render_template, request, redirect, session, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email_config import EMAIL_ADDRESS, EMAIL_PASSWORD
import subprocess
import sys
import os

app = Flask(__name__)
app.secret_key = "attendance_secret_key"

ADMIN_EMAIL    = "admin@gmail.com"
ADMIN_PASSWORD = "admin123"

def get_db():
    return mysql.connector.connect(
        host="localhost", user="root", password="", database="attendance_db"
    )

def create_tables():
    conn = mysql.connector.connect(host="localhost", user="root", password="")
    c = conn.cursor()
    c.execute("CREATE DATABASE IF NOT EXISTS attendance_db")
    c.execute("USE attendance_db")
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id       INT AUTO_INCREMENT PRIMARY KEY,
            name     VARCHAR(100),
            roll     VARCHAR(50) UNIQUE,
            email    VARCHAR(100) UNIQUE,
            password VARCHAR(255)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            date       DATE,
            status     VARCHAR(20) DEFAULT 'Pending',
            UNIQUE KEY unique_att (student_id, date)
        )
    """)
    conn.commit()
    c.close()
    conn.close()

create_tables()

# ── LOGIN ──
@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email    = request.form["email"]
        password = request.form["password"]
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session.clear()
            session["admin"] = True
            return redirect("/admin")
        conn = get_db()
        c = conn.cursor(dictionary=True)
        c.execute("SELECT * FROM students WHERE email = %s", (email,))
        user = c.fetchone()
        c.close(); conn.close()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"]   = user["id"]
            session["user_name"] = user["name"]
            session["user_roll"] = user["roll"]
            return redirect("/student")
        else:
            error = "Invalid email or password"
    return render_template("login.html", error=error)

# ── REGISTER ──
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        name     = request.form["name"]
        roll     = request.form["roll"]
        email    = request.form["email"]
        password = generate_password_hash(request.form["password"])
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO students (name, roll, email, password) VALUES (%s,%s,%s,%s)",
                      (name, roll, email, password))
            conn.commit()
            c.close(); conn.close()
            return redirect("/")
        except mysql.connector.IntegrityError:
            error = "Roll number or email already registered"
    return render_template("register.html", error=error)

# ── STUDENT DASHBOARD ──
@app.route("/student")
def student_dashboard():
    if "user_id" not in session:
        return redirect("/")
    conn = get_db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT date, status FROM attendance WHERE student_id = %s ORDER BY date DESC",
              (session["user_id"],))
    records = c.fetchall()
    c.close(); conn.close()
    total   = len(records)
    present = sum(1 for r in records if r["status"] == "Present")
    pct     = round((present / total * 100) if total else 0, 1)
    return render_template("student_dashboard.html",
                           name=session["user_name"],
                           roll=session["user_roll"],
                           records=records,
                           total=total, present=present, pct=pct)

# ── ADMIN DASHBOARD ──
@app.route("/admin")
def admin_dashboard():
    if "admin" not in session:
        return redirect("/")
    today = str(date.today())
    conn  = get_db()
    c     = conn.cursor(dictionary=True)

    c.execute("SELECT COUNT(*) AS cnt FROM students")
    total_students = c.fetchone()["cnt"]

    c.execute("SELECT COUNT(DISTINCT student_id) AS cnt FROM attendance WHERE date=%s AND status='Present'", (today,))
    present_today = c.fetchone()["cnt"]

    c.execute("SELECT COUNT(DISTINCT student_id) AS cnt FROM attendance WHERE date=%s AND status='Absent'", (today,))
    absent_today = c.fetchone()["cnt"]

    pending_today = total_students - present_today - absent_today

    c.execute("""
        SELECT s.name, s.roll, s.email,
               COALESCE(a.status, 'Pending') AS status
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id AND a.date = %s
        ORDER BY s.name
    """, (today,))
    records = c.fetchall()
    c.close(); conn.close()

    return render_template("admin_dashboard.html",
                           total_students=total_students,
                           present_today=present_today,
                           absent_today=absent_today,
                           pending_today=pending_today,
                           records=records,
                           today=today)

# ── CLOSE ATTENDANCE (Pending → Absent) ──
@app.route("/admin/close-attendance", methods=["POST"])
def close_attendance():
    if "admin" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    today = str(date.today())
    conn  = get_db()
    c     = conn.cursor(dictionary=True)
    c.execute("SELECT id FROM students")
    all_students = c.fetchall()
    c.execute("SELECT student_id FROM attendance WHERE date=%s", (today,))
    already_marked = {r["student_id"] for r in c.fetchall()}
    pending = [s for s in all_students if s["id"] not in already_marked]
    count = 0
    for student in pending:
        try:
            c.execute("INSERT INTO attendance (student_id, date, status) VALUES (%s, %s, 'Absent')",
                      (student["id"], today))
            count += 1
        except mysql.connector.IntegrityError:
            pass
    conn.commit()
    c.close(); conn.close()
    return jsonify({"message": f"Attendance closed! {count} students marked Absent.", "count": count})

# ── SEND ABSENT EMAILS ──
@app.route("/admin/send-emails", methods=["POST"])
def send_emails():
    if "admin" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    today = str(date.today())
    conn  = get_db()
    c     = conn.cursor(dictionary=True)
    c.execute("SELECT id, name, email FROM students")
    all_students = c.fetchall()
    c.execute("SELECT student_id FROM attendance WHERE date=%s AND status='Present'", (today,))
    present_ids = {r["student_id"] for r in c.fetchall()}
    c.close(); conn.close()
    absentees = [s for s in all_students if s["id"] not in present_ids]
    if not absentees:
        return jsonify({"sent": 0, "message": "All students are present today!"})
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        sent = 0
        for student in absentees:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Attendance Alert - Absent on {today}"
            msg["From"]    = EMAIL_ADDRESS
            msg["To"]      = student["email"]
            html_body = f"""
<html><body style="font-family:Arial,sans-serif;background:#f4f6f9;padding:20px">
  <div style="max-width:500px;margin:auto;background:white;border-radius:12px;padding:30px">
    <h2 style="color:#dc3545">Attendance Alert</h2>
    <p>Dear <strong>{student['name']}</strong>,</p>
    <p>You were marked <strong style="color:#dc3545">ABSENT</strong> on <strong>{today}</strong>.</p>
    <p>If this is a mistake, please contact your administrator.</p>
    <p style="color:#888;font-size:12px">Smart Attendance System - CSPIT AIML</p>
  </div>
</body></html>"""
            msg.attach(MIMEText(html_body, "html"))
            server.sendmail(EMAIL_ADDRESS, student["email"], msg.as_string())
            sent += 1
        server.quit()
        return jsonify({"sent": sent, "message": f"Emails sent to {sent} absent students."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── START FACE RECOGNITION ──
@app.route("/admin/start-recognition", methods=["POST"])
def start_recognition():
    if "admin" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        subprocess.Popen([sys.executable, "recognize_attendance.py"],
                         cwd=os.path.dirname(os.path.abspath(__file__)))
        return jsonify({"message": "Camera window opened! Press Q to stop when done."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── ATTENDANCE HISTORY ──
@app.route("/admin/attendance")
def admin_attendance():
    if "admin" not in session:
        return redirect("/")
    filter_date = request.args.get("date", str(date.today()))
    conn = get_db()
    c = conn.cursor(dictionary=True)
    c.execute("""
        SELECT s.name, s.roll,
               COALESCE(a.status, 'Pending') AS status
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id AND a.date = %s
        ORDER BY s.name
    """, (filter_date,))
    records = c.fetchall()
    c.close(); conn.close()
    return render_template("admin_attendance.html", records=records, filter_date=filter_date)

# ── ALL STUDENTS ──
@app.route("/admin/students")
def admin_students():
    if "admin" not in session:
        return redirect("/")
    conn = get_db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT * FROM students ORDER BY name")
    students = c.fetchall()
    c.close(); conn.close()
    return render_template("admin_students.html", students=students)

# ── DELETE STUDENT ──
@app.route("/admin/delete/<int:sid>", methods=["POST"])
def delete_student(sid):
    if "admin" not in session:
        return redirect("/")
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM attendance WHERE student_id = %s", (sid,))
    c.execute("DELETE FROM students WHERE id = %s", (sid,))
    conn.commit()
    c.close(); conn.close()
    return redirect("/admin/students")

# ── LOGOUT ──
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
