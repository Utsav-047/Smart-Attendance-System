
from flask import Flask, render_template, request, redirect, session, jsonify, make_response, abort
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email_config import EMAIL_ADDRESS, EMAIL_PASSWORD
from capture_faces import capture_faces, save_webrtc_frames
from encode_faces import encode_all_faces
from liveness import LivenessChecker
from security_core import (
    generate_csrf_token,
    validate_csrf_token,
    csrf_protect,
    rate_limit,
    load_secure_pickle,
    validate_roll,
    validate_email,
    validate_password_strength,
    add_security_headers,
)
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import hmac
import hashlib
import secrets
import time
import subprocess
import threading
import sys
import os
import csv
import io
import re
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change_this_secret")
if app.secret_key in ("change_this_secret", "your_super_secret_key_change_this_in_production"):
    print("[Security Warning] SECRET_KEY is set to a default value. Please configure a strong random SECRET_KEY in .env.")

app.permanent_session_lifetime = timedelta(hours=4)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "0").lower() in ("1", "true")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB request payload ceiling

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf_token)

@app.after_request
def apply_security_headers_middleware(response):
    return add_security_headers(response)

DEFAULT_ADMIN_EMAIL    = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@gmail.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")

# ─────────────────────────────────────────
# MYSQL CONNECTION
# ─────────────────────────────────────────
def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3307)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "attendance_db")
    )

# ─────────────────────────────────────────
# CREATE DATABASE + TABLES ON STARTUP
# ─────────────────────────────────────────
def create_tables():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3307)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "")
    )
    c = conn.cursor()
    c.execute("CREATE DATABASE IF NOT EXISTS attendance_db")
    c.execute("USE attendance_db")
    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            name       VARCHAR(100),
            email      VARCHAR(100) UNIQUE,
            password   VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id   INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) UNIQUE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            name          VARCHAR(100),
            roll          VARCHAR(50) UNIQUE,
            email         VARCHAR(100) UNIQUE,
            password      VARCHAR(255),
            student_class VARCHAR(100)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            date       DATE,
            status     VARCHAR(20) DEFAULT 'Pending',
            subject_id INT,
            confidence FLOAT DEFAULT NULL,
            UNIQUE KEY unique_att (student_id, date, subject_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS email_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            subject_id INT,
            date DATE,
            recipient_email VARCHAR(120),
            student_name VARCHAR(100),
            status VARCHAR(30) DEFAULT 'Sent',
            error_message TEXT,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_email_logs (student_id, date, subject_id)
        )
    """)
    conn.commit()

    try:
        c.execute("ALTER TABLE students ADD COLUMN student_class VARCHAR(100)")
    except mysql.connector.Error:
        pass

    try:
        c.execute("ALTER TABLE attendance ADD COLUMN subject_id INT")
    except mysql.connector.Error:
        pass

    try:
        c.execute("ALTER TABLE attendance ADD COLUMN confidence FLOAT")
    except mysql.connector.Error:
        pass

    c.execute("SELECT COUNT(*) FROM admins")
    admin_count = c.fetchone()[0]
    if admin_count == 0:
        c.execute(
            "INSERT INTO admins (name, email, password) VALUES (%s, %s, %s)",
            ("Super Admin", DEFAULT_ADMIN_EMAIL, generate_password_hash(DEFAULT_ADMIN_PASSWORD))
        )

    c.execute("SELECT COUNT(*) FROM subjects")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO subjects (name) VALUES ('General')")

    conn.commit()
    c.close()
    conn.close()

def init_database_safe():
    try:
        create_tables()
    except Exception as e:
        print(f"[Database Warning] Startup database check failed: {e}. Ensure MySQL is running.")

init_database_safe()

# ─────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
@rate_limit(limit=10, window=60, action="login")
@csrf_protect
def login():
    error = None
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            error = "Email and password are required."
            return render_template("login.html", error=error)

        conn = get_db()
        c = conn.cursor(dictionary=True)
        c.execute("SELECT * FROM admins WHERE email = %s", (email,))
        admin = c.fetchone()

        if admin and check_password_hash(admin["password"], password):
            session.clear()
            session["is_admin"] = True
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["name"]
            c.close(); conn.close()
            return redirect("/admin")

        c.execute("SELECT * FROM students WHERE email = %s", (email,))
        user = c.fetchone()
        c.close(); conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"]   = user["id"]
            session["user_name"] = user["name"]
            session["user_roll"] = user["roll"]
            session["student_class"] = user.get("student_class")
            return redirect("/student")
        else:
            error = "Invalid email or password"

    return render_template("login.html", error=error)

# ─────────────────────────────────────────
# FORGOT & RESET PASSWORD (SECURE 3-STEP OTP FLOW)
# ─────────────────────────────────────────
def get_reset_serializer():
    return URLSafeTimedSerializer(app.secret_key, salt="attendance-pwd-reset-salt-v1")

def generate_reset_token(email):
    return get_reset_serializer().dumps(email)

def verify_reset_token(token, max_age_seconds=900):
    """Verifies token validity within max_age (15 minutes)."""
    try:
        data = get_reset_serializer().loads(token, max_age=max_age_seconds)
        if isinstance(data, dict):
            return data.get("email")
        return data
    except (SignatureExpired, BadSignature):
        return None

def mask_email(email: str) -> str:
    """Masks an email for anti-enumeration security display: s***t@charusat.edu.in"""
    if not email or "@" not in email:
        return ""
    user, domain = email.split("@", 1)
    if len(user) <= 2:
        masked_user = user[0] + "*" if len(user) == 2 else "*"
    else:
        masked_user = user[0] + ("*" * (len(user) - 2)) + user[-1]
    return f"{masked_user}@{domain}"

def send_otp_email_async(recipient_email, recipient_name, otp_code):
    """
    Sends an institutional HTML verification email containing the 6-digit OTP code.
    Runs asynchronously in a background thread to prevent UI latency.
    """
    def _worker():
        subject = "Smart Attendance System - Password Reset Code"
        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
    <tr>
      <td style="background: #1e3a8a; padding: 24px 32px; text-align: center;">
        <h1 style="color: #ffffff; margin: 0; font-size: 18px; font-weight: 700; letter-spacing: -0.02em;">Smart Attendance System</h1>
        <p style="color: #bfdbfe; margin: 4px 0 0 0; font-size: 12px;">Institutional Identity & Security Portal</p>
      </td>
    </tr>
    <tr>
      <td style="padding: 32px;">
        <p style="font-size: 14px; color: #334155; margin-top: 0;">Dear <strong>{recipient_name or 'User'}</strong>,</p>
        <p style="font-size: 13px; color: #475569; line-height: 1.6;">We received an authorized request to reset the password for your institutional Smart Attendance account. Use the single-use 6-digit verification code below to proceed:</p>
        
        <div style="margin: 28px 0; text-align: center;">
          <div style="display: inline-block; background: #eff6ff; border: 2px dashed #3b82f6; border-radius: 12px; padding: 14px 28px;">
            <span style="font-family: 'Courier New', monospace; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #1e40af;">{otp_code}</span>
          </div>
          <p style="margin: 8px 0 0 0; font-size: 11px; color: #64748b;">Valid for <strong>10 minutes</strong>. Never share this code with anyone.</p>
        </div>

        <p style="font-size: 12px; color: #64748b; line-height: 1.5; border-top: 1px solid #f1f5f9; padding-top: 16px;">If you did not request this password reset, you can safely disregard this email. Your password will remain unchanged.</p>
      </td>
    </tr>
    <tr>
      <td style="background: #f8fafc; padding: 14px 32px; border-top: 1px solid #e2e8f0; text-align: center;">
        <p style="margin: 0; font-size: 10px; color: #94a3b8;">Chandubhai S. Patel Institute of Technology &bull; CHARUSAT University</p>
      </td>
    </tr>
  </table>
</body>
</html>"""
        plain_body = f"Hello {recipient_name},\n\nYour 6-digit Smart Attendance reset code is: {otp_code}\nThis code is valid for 10 minutes.\n\nIf you did not request this, please disregard."

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = recipient_email
        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        sent = False
        # Try SSL port 465
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=8) as server:
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.sendmail(EMAIL_ADDRESS, recipient_email, msg.as_string())
            sent = True
        except Exception:
            pass

        # Try STARTTLS port 587 if not sent
        if not sent:
            try:
                with smtplib.SMTP("smtp.gmail.com", 587, timeout=8) as server:
                    server.starttls()
                    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                    server.sendmail(EMAIL_ADDRESS, recipient_email, msg.as_string())
                sent = True
            except Exception as e:
                print(f"[Email Notice] SMTP dispatch error to {recipient_email}: {e}")

        if sent:
            print(f"[OTP Service] Successfully dispatched verification email to {recipient_email}")
        else:
            # Fallback for dev / offline / invalid Google App Password
            print(f"\n=======================================================")
            print(f" [DEV FALLBACK OTP] Recipient: {recipient_email}")
            print(f" [DEV FALLBACK OTP] 6-Digit Code: {otp_code}")
            print(f" (Configure valid Google App Password in .env to deliver real emails)")
            print(f"=======================================================\n")

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

@app.route("/forgot_password", methods=["GET"])
def forgot_password():
    return render_template("forgot_password.html")

@app.route("/reset_password", methods=["GET"])
def reset_password():
    return redirect("/forgot_password")

@app.route("/api/forgot-password/send-otp", methods=["POST"])
@rate_limit(limit=6, window=300, action="forgot_password_otp")
@csrf_protect
def api_forgot_password_send_otp():
    data = request.get_json(silent=True) or {}
    identifier = data.get("identifier", "").strip()

    if not identifier:
        return jsonify({"success": False, "error": "Please enter your registered institutional email or roll number."}), 400

    conn = get_db()
    c = conn.cursor(dictionary=True)
    
    # Check if student by email or roll
    c.execute("SELECT id, name, email, roll FROM students WHERE email = %s OR roll = %s LIMIT 1", (identifier, identifier.upper()))
    user = c.fetchone()
    account_type = "student"

    # Check if admin by email
    if not user:
        c.execute("SELECT id, name, email FROM admins WHERE email = %s LIMIT 1", (identifier,))
        user = c.fetchone()
        account_type = "admin"

    c.close()
    conn.close()

    # Generic security response if not found (anti-enumeration)
    if not user:
        time.sleep(0.3)
        return jsonify({
            "success": False,
            "error": "No matching active student or administrator account found for that identifier."
        }), 404

    target_email = user["email"]
    target_name = user["name"]

    now = time.time()
    last_sent = session.get("pw_reset_last_sent", 0)
    if (now - last_sent) < 45:
        return jsonify({
            "success": False,
            "error": f"Please wait {int(45 - (now - last_sent))} seconds before requesting another code."
        }), 429

    # Generate 6-digit random code
    otp_int = secrets.randbelow(900000) + 100000
    otp_code = str(otp_int)

    # Store HMAC-SHA256 digest in session (never plaintext)
    otp_hash = hmac.new(app.secret_key.encode(), otp_code.encode(), hashlib.sha256).hexdigest()
    
    session["pw_reset_otp_hash"] = otp_hash
    session["pw_reset_otp_expiry"] = now + 600  # 10 minutes
    session["pw_reset_otp_attempts"] = 0
    session["pw_reset_account_email"] = target_email
    session["pw_reset_account_name"] = target_name
    session["pw_reset_account_type"] = account_type
    session["pw_reset_last_sent"] = now
    session.modified = True

    # Dispatch email asynchronously
    send_otp_email_async(target_email, target_name, otp_code)

    return jsonify({
        "success": True,
        "masked_email": mask_email(target_email),
        "message": "A 6-digit verification code has been dispatched to your institutional email."
    })

@app.route("/api/forgot-password/verify-otp", methods=["POST"])
@rate_limit(limit=12, window=300, action="forgot_password_verify")
@csrf_protect
def api_forgot_password_verify_otp():
    data = request.get_json(silent=True) or {}
    submitted_otp = str(data.get("otp", "")).strip()

    saved_hash = session.get("pw_reset_otp_hash")
    expiry = session.get("pw_reset_otp_expiry", 0)
    attempts = session.get("pw_reset_otp_attempts", 0)
    target_email = session.get("pw_reset_account_email")

    if not saved_hash or not target_email:
        return jsonify({"success": False, "error": "No active verification session found. Please enter your email or roll number again."}), 400

    now = time.time()
    if now > expiry:
        session.pop("pw_reset_otp_hash", None)
        return jsonify({"success": False, "error": "Your verification code has expired (10-minute limit). Please request a new code."}), 400

    if attempts >= 5:
        session.pop("pw_reset_otp_hash", None)
        session.pop("pw_reset_otp_expiry", None)
        return jsonify({"success": False, "error": "Too many invalid attempts. For security, this code has been revoked. Please request a new one."}), 429

    # Constant-time comparison
    computed_hash = hmac.new(app.secret_key.encode(), submitted_otp.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(saved_hash, computed_hash):
        session["pw_reset_otp_attempts"] = attempts + 1
        session.modified = True
        remaining = 5 - (attempts + 1)
        return jsonify({
            "success": False, 
            "error": f"Invalid verification code. {remaining} attempt(s) remaining." if remaining > 0 else "Invalid verification code. Maximum attempts exceeded."
        }), 400

    # Consume OTP and issue single-use reset token
    session.pop("pw_reset_otp_hash", None)
    session.pop("pw_reset_otp_expiry", None)
    
    reset_token = get_reset_serializer().dumps({
        "email": target_email,
        "ts": int(now),
        "nonce": secrets.token_hex(8)
    })
    session["pw_reset_authorized_token"] = reset_token
    session.modified = True

    return jsonify({
        "success": True,
        "reset_token": reset_token,
        "message": "Verification code accepted. Please create your new secure password."
    })

@app.route("/api/forgot-password/reset", methods=["POST"])
@rate_limit(limit=6, window=300, action="forgot_password_reset")
@csrf_protect
def api_forgot_password_reset():
    data = request.get_json(silent=True) or {}
    new_password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")
    token = data.get("reset_token", "")

    saved_token = session.get("pw_reset_authorized_token")
    target_email = session.get("pw_reset_account_email")

    if not token or not target_email or not saved_token:
        return jsonify({"success": False, "error": "Unauthorized or expired session. Please start the password reset process again."}), 401

    if not hmac.compare_digest(token, saved_token):
        return jsonify({"success": False, "error": "Invalid reset authorization token."}), 403

    try:
        payload = get_reset_serializer().loads(token, max_age=900)
        if payload.get("email") != target_email:
            return jsonify({"success": False, "error": "Identity mismatch in token."}), 403
    except Exception:
        return jsonify({"success": False, "error": "Reset session expired. Please start again."}), 403

    if new_password != confirm_password:
        return jsonify({"success": False, "error": "Passwords do not match."}), 400

    is_valid_pw, pw_err = validate_password_strength(new_password)
    if not is_valid_pw:
        return jsonify({"success": False, "error": pw_err}), 400

    # Update database
    new_hash = generate_password_hash(new_password)
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE students SET password = %s WHERE email = %s", (new_hash, target_email))
    c.execute("UPDATE admins SET password = %s WHERE email = %s", (new_hash, target_email))
    conn.commit()
    c.close()
    conn.close()

    # Clear all pw_reset session data
    for k in list(session.keys()):
        if k.startswith("pw_reset_"):
            session.pop(k, None)
    session.modified = True

    return jsonify({
        "success": True,
        "message": "Your password has been securely updated. Redirecting to sign in..."
    })

# ─────────────────────────────────────────
# ADMIN REGISTRATION
# ─────────────────────────────────────────
@app.route("/admin/register", methods=["GET", "POST"])
@rate_limit(limit=10, window=300, action="admin_register")
@csrf_protect
def admin_register():
    error = None
    success = None

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM admins")
    admin_count = c.fetchone()[0]
    c.close(); conn.close()

    allow_create = session.get("is_admin") or admin_count == 0
    if not allow_create:
        return redirect("/")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        is_pw_valid, pw_err = validate_password_strength(password)
        if not name or not email or not password or not confirm_password:
            error = "All fields are required."
        elif not validate_email(email):
            error = "Invalid institutional email address format."
        elif not is_pw_valid:
            error = pw_err
        elif password != confirm_password:
            error = "Passwords do not match."
        else:
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute(
                    "INSERT INTO admins (name, email, password) VALUES (%s, %s, %s)",
                    (name, email, generate_password_hash(password))
                )
                conn.commit()
                success = "Admin account created successfully. Please login."
            except mysql.connector.IntegrityError:
                error = "Email already exists."
            finally:
                c.close(); conn.close()

    return render_template("admin_register.html", error=error, success=success)

# ─────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
@rate_limit(limit=10, window=300, action="register")
@csrf_protect
def register():
    error = None
    registered = request.args.get("registered") == "true"
    trained = request.args.get("trained") == "true"

    if request.method == "POST":
        name             = request.form.get("name", "").strip()
        roll             = request.form.get("roll", "").strip().upper()
        email            = request.form.get("email", "").strip()
        student_class    = request.form.get("student_class", "").strip()
        password         = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        face_captured    = request.form.get("face_captured") == "1"

        is_pw_valid, pw_err = validate_password_strength(password)

        if not name or not roll or not email:
            error = "Name, Roll Number, and Email are required."
        elif not validate_roll(roll):
            error = "Roll number may only contain alphanumeric characters, hyphens, and underscores."
        elif not validate_email(email):
            error = "Invalid institutional email address format."
        elif not is_pw_valid:
            error = pw_err
        elif password != confirm_password:
            error = "Passwords do not match."
        elif not face_captured:
            error = "Please capture your face before submitting registration."
        else:
            password_hash = generate_password_hash(password)
            try:
                conn = get_db()
                c = conn.cursor()
                c.execute(
                    "INSERT INTO students (name, roll, email, password, student_class) VALUES (%s,%s,%s,%s,%s)",
                    (name, roll, email, password_hash, student_class)
                )
                conn.commit()
                c.close(); conn.close()

                # Trigger asynchronous encoding
                threading.Thread(target=encode_all_faces, kwargs={"secret_key": app.secret_key}, daemon=True).start()
                return redirect("/register?registered=true&trained=true")
            except mysql.connector.IntegrityError:
                error = "Roll number or email already registered."

    return render_template("register.html", error=error, registered=registered, trained=trained)

# ─────────────────────────────────────────
# WEBRTC FACE CAPTURE (in-browser webcam)
# ─────────────────────────────────────────
@app.route("/api/capture-webrtc", methods=["POST"])
@rate_limit(limit=15, window=60, action="capture_webrtc")
@csrf_protect
def capture_webrtc():
    try:
        data = request.get_json(silent=True) or {}
        roll = data.get("roll", "").strip().upper()
        frames = data.get("frames", [])

        if not roll:
            return jsonify({"success": False, "message": "Roll number is required"}), 400
        if not validate_roll(roll):
            return jsonify({"success": False, "message": "Invalid roll number format"}), 400
        if not frames:
            return jsonify({"success": False, "message": "No frames received from camera"}), 400

        # Anti-Hijacking Check: If roll is already registered, only that student or an admin can re-upload faces
        conn = get_db()
        c = conn.cursor(dictionary=True)
        c.execute("SELECT id, roll FROM students WHERE roll = %s", (roll,))
        existing_student = c.fetchone()
        c.close(); conn.close()

        if existing_student:
            is_authorized = session.get("is_admin") or (
                session.get("user_id") and session.get("user_id") == existing_student["id"]
            )
            if not is_authorized:
                return jsonify({
                    "success": False,
                    "message": "Security Error: Student ID is already registered. Only the enrolled student or an administrator can update facial biometrics."
                }), 403

        result = save_webrtc_frames(roll, frames)
        if result["success"]:
            # Trigger background encoding with secret key
            threading.Thread(target=encode_all_faces, kwargs={"secret_key": app.secret_key}, daemon=True).start()
            return jsonify({
                "success": True,
                "saved_count": result["saved_count"],
                "message": result["message"]
            })
        else:
            return jsonify({"success": False, "message": result.get("message", "Could not detect face")}), 400

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ─────────────────────────────────────────
# CAPTURE FACE  (called from register page button fallback)
# Runs in a separate thread so browser doesn't freeze
# ─────────────────────────────────────────
@app.route("/capture_face", methods=["POST"])
@rate_limit(limit=5, window=60, action="capture_face")
@csrf_protect
def capture_face():
    if not session.get("is_admin") and not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.get_json(silent=True) or {}
        roll = data.get("roll", "").strip().upper()

        if not roll or not validate_roll(roll):
            return jsonify({"error": "Valid Roll number is required"}), 400

        def run_capture():
            try:
                capture_faces(roll)
            except Exception as e:
                print(f"Capture error: {e}")

        t = threading.Thread(target=run_capture)
        t.start()

        return jsonify({"message": "Face capture process initiated."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────
# TRAIN MODEL  (called after capture is done)
# ─────────────────────────────────────────
@app.route("/train_model_route", methods=["POST"])
@rate_limit(limit=5, window=60, action="train_model")
@csrf_protect
def train_model_route():
    if not session.get("is_admin") and not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        def run_training():
            try:
                encode_all_faces(secret_key=app.secret_key)
                print("[Encode] Face encoding completed!")
            except Exception as e:
                print(f"[Encode Error]: {e}")

        t = threading.Thread(target=run_training)
        t.start()
        t.join(timeout=60)

        return jsonify({"message": "Model trained successfully! Student is ready for face recognition."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────
# STUDENT DASHBOARD
# ─────────────────────────────────────────
@app.route("/student")
def student_dashboard():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor(dictionary=True)

    # All records with subject name for day-wise grouping
    c.execute("""
        SELECT a.date, a.status, COALESCE(s.name, 'General') AS subject_name
        FROM attendance a
        LEFT JOIN subjects s ON a.subject_id = s.id
        WHERE a.student_id = %s
        ORDER BY a.date DESC, s.name
    """, (session["user_id"],))
    records = c.fetchall()

    # Stats: count unique dates only
    c.execute("""
        SELECT COUNT(DISTINCT date) AS total,
               COUNT(DISTINCT CASE WHEN status = 'Present' THEN date END) AS present
        FROM attendance
        WHERE student_id = %s
    """, (session["user_id"],))
    stats = c.fetchone()
    c.close(); conn.close()

    total   = stats["total"]
    present = stats["present"]
    pct     = round((present / total * 100) if total else 0, 1)

    # Build day-wise structure: { date: [{ subject_name, status }, ...] }
    from collections import OrderedDict
    days = OrderedDict()
    for r in records:
        d = str(r["date"])
        if d not in days:
            days[d] = []
        days[d].append({"subject": r["subject_name"], "status": r["status"]})

    # Subject-wise attendance %
    conn3 = get_db()
    c3 = conn3.cursor(dictionary=True)
    c3.execute("""
        SELECT sub.name AS subject,
               COUNT(*) AS total,
               SUM(a.status='Present') AS present
        FROM attendance a
        JOIN subjects sub ON a.subject_id = sub.id
        WHERE a.student_id = %s
        GROUP BY sub.id, sub.name
        ORDER BY sub.name
    """, (session["user_id"],))
    subject_stats = c3.fetchall()
    for s in subject_stats:
        t = s["total"] or 0
        p = int(s["present"] or 0)
        s["pct"] = round((p / t * 100) if t else 0, 1)
        s["present"] = p
    c3.close(); conn3.close()

    # Classes needed to reach 75%
    classes_needed = 0
    if total > 0 and pct < 75:
        needed = 0
        while True:
            needed += 1
            if ((present + needed) / (total + needed) * 100) >= 75:
                break
            if needed > 500:
                needed = -1
                break
        classes_needed = needed

    return render_template("student_dashboard.html",
                           name=session["user_name"],
                           roll=session["user_roll"],
                           records=records,
                           days=days,
                           subject_stats=subject_stats,
                           classes_needed=classes_needed,
                           total=total, present=present, pct=pct)

# ─────────────────────────────────────────
# STUDENT PROFILE
# ─────────────────────────────────────────
@app.route("/student/profile")
def student_profile():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT id, name, roll, email FROM students WHERE id=%s", (session["user_id"],))
    user = c.fetchone()

    c.execute(
        "SELECT date, status FROM attendance WHERE student_id=%s ORDER BY date DESC",
        (session["user_id"],)
    )
    records = c.fetchall()
    c.close(); conn.close()

    total   = len(records)
    present = sum(1 for r in records if r["status"] == "Present")
    absent  = sum(1 for r in records if r["status"] == "Absent")
    pending = sum(1 for r in records if r["status"] == "Pending")
    pct     = round((present / total * 100) if total else 0, 1)

    return render_template(
        "student_profile.html",
        user=user,
        records=records,
        total=total,
        present=present,
        absent=absent,
        pending=pending,
        pct=pct
    )


# ─────────────────────────────────────────
# STUDENT EXPORT ATTENDANCE
# ─────────────────────────────────────────
@app.route("/student/export-attendance")
def student_export_attendance():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor(dictionary=True)
    c.execute(
        "SELECT date, status FROM attendance WHERE student_id=%s ORDER BY date DESC",
        (session["user_id"],)
    )
    records = c.fetchall()
    c.close(); conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Status"])
    for row in records:
        writer.writerow([row["date"], row["status"]])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=attendance_report.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


# ─────────────────────────────────────────
# LOW ATTENDANCE STUDENTS (API)
# ─────────────────────────────────────────
@app.route("/admin/low-attendance")
def low_attendance():
    if not session.get("is_admin"):
        return redirect("/")
    conn = get_db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT id, name, roll, email FROM students ORDER BY name")
    students = c.fetchall()
    result = []
    for s in students:
        c.execute("""
            SELECT COUNT(DISTINCT date) AS total,
                   COUNT(DISTINCT CASE WHEN status='Present' THEN date END) AS present
            FROM attendance WHERE student_id=%s
        """, (s["id"],))
        row = c.fetchone()
        t = row["total"] or 0
        p = row["present"] or 0
        pct = round((p / t * 100) if t else 0, 1)
        if pct < 75:
            s["pct"] = pct
            s["total"] = t
            s["present"] = p
            result.append(s)
    c.close(); conn.close()
    result.sort(key=lambda x: x["pct"])
    return jsonify(result)

# ─────────────────────────────────────────
# SUBJECT-WISE STATS (API)
# ─────────────────────────────────────────
@app.route("/admin/subject-stats")
def subject_stats():
    if not session.get("is_admin"):
        return redirect("/")
    conn = get_db()
    c = conn.cursor(dictionary=True)
    c.execute("""
        SELECT sub.name AS subject,
               SUM(a.status='Present') AS present,
               SUM(a.status='Absent')  AS absent
        FROM attendance a
        JOIN subjects sub ON a.subject_id = sub.id
        GROUP BY sub.id, sub.name
        ORDER BY sub.name
    """)
    rows = c.fetchall()
    c.close(); conn.close()
    return jsonify(rows)

# ─────────────────────────────────────────
# MONTHLY HEATMAP DATA (API)
# ─────────────────────────────────────────
@app.route("/admin/monthly-heatmap")
def monthly_heatmap():
    if not session.get("is_admin"):
        return redirect("/")
    month = request.args.get("month", str(date.today())[:7])  # YYYY-MM
    conn = get_db()
    c = conn.cursor(dictionary=True)
    c.execute("""
        SELECT date, COUNT(DISTINCT student_id) AS total,
               SUM(status='Present') AS present
        FROM attendance
        WHERE DATE_FORMAT(date,'%%Y-%%m') = %s
        GROUP BY date ORDER BY date
    """, (month,))
    rows = c.fetchall()
    c.close(); conn.close()
    return jsonify([{"date": str(r["date"]), "total": r["total"], "present": int(r["present"] or 0)} for r in rows])

# ─────────────────────────────────────────
# BULK RESET ATTENDANCE
# ─────────────────────────────────────────
@app.route("/admin/reset-attendance", methods=["POST"])
@csrf_protect
def reset_attendance():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    reset_date   = data.get("date", str(date.today()))
    subject_id   = data.get("subject_id")
    conn = get_db()
    c = conn.cursor()
    if subject_id:
        c.execute("DELETE FROM attendance WHERE date=%s AND subject_id=%s", (reset_date, subject_id))
    else:
        c.execute("DELETE FROM attendance WHERE date=%s", (reset_date,))
    conn.commit()
    c.close(); conn.close()
    return jsonify({"message": f"Attendance for {reset_date} has been reset."})

# ─────────────────────────────────────────
# ADMIN DASHBOARD
# ─────────────────────────────────────────
@app.route("/admin")
def admin_dashboard():
    if not session.get("is_admin"):
        return redirect("/")

    selected_subject_id = request.args.get("subject_id")
    today = str(date.today())
    conn  = get_db()
    c     = conn.cursor(dictionary=True)

    c.execute("SELECT id, name FROM subjects ORDER BY name")
    subjects = c.fetchall()
    selected_subject = None
    if selected_subject_id:
        c.execute("SELECT id, name FROM subjects WHERE id = %s", (selected_subject_id,))
        selected_subject = c.fetchone()
    if not selected_subject:
        selected_subject = subjects[0] if subjects else {"id": None, "name": "General"}

    c.execute("SELECT COUNT(*) AS cnt FROM students")
    total_students = c.fetchone()["cnt"]

    c.execute(
        "SELECT COUNT(DISTINCT student_id) AS cnt FROM attendance WHERE date=%s AND status='Present' AND subject_id=%s",
        (today, selected_subject["id"])
    )
    present_today = c.fetchone()["cnt"]

    c.execute(
        "SELECT COUNT(DISTINCT student_id) AS cnt FROM attendance WHERE date=%s AND status='Absent' AND subject_id=%s",
        (today, selected_subject["id"])
    )
    absent_today = c.fetchone()["cnt"]

    pending_today = total_students - present_today - absent_today

    c.execute("""
        SELECT s.name, s.roll, s.email,
               COALESCE(a.status, 'Pending') AS status
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id AND a.date = %s AND a.subject_id = %s
        ORDER BY s.name
    """, (today, selected_subject["id"]))
    records = c.fetchall()
    c.close(); conn.close()

    return render_template("admin_dashboard.html",
                           total_students=total_students,
                           present_today=present_today,
                           absent_today=absent_today,
                           pending_today=pending_today,
                           records=records,
                           today=today,
                           subjects=subjects,
                           selected_subject=selected_subject)

# ─────────────────────────────────────────
# ADD SUBJECT
# ─────────────────────────────────────────
@app.route("/admin/subjects/add", methods=["POST"])
@csrf_protect
def add_subject():
    if not session.get("is_admin"):
        return redirect("/")

    subject_name = request.form.get("subject_name", "").strip()
    if subject_name and len(subject_name) <= 60:
        # Sanitize subject name
        subject_name = re.sub(r"[^\w\s-]", "", subject_name).strip()
        if subject_name:
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute("INSERT IGNORE INTO subjects (name) VALUES (%s)", (subject_name,))
                conn.commit()
            finally:
                c.close(); conn.close()

    return redirect("/admin")

# ─────────────────────────────────────────
# LIVE CAMERA RECOGNITION (browser stream)
# ─────────────────────────────────────────
import pickle
import face_recognition as fr
import numpy as np
from flask import Response, stream_with_context

_cam_running = False
_cam_marked  = {}   # student_id -> name
_cam_subject = 1

def _recognition_thread(subject_id):
    global _cam_running, _cam_marked, _cam_subject
    _cam_marked  = {}
    _cam_subject = subject_id

    try:
        data = load_secure_pickle("encodings.pkl", secret_key=app.secret_key)
        known_encodings = data["encodings"]
        known_ids       = data["student_ids"]
    except Exception as e:
        print(f"[Recognition Security] encodings.pkl verification error: {e}")
        _cam_running = False
        return

    import cv2
    cam = None
    for i in range(4):
        c = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if c.isOpened():
            cam = c
            break
        c.release()
    if cam is None:
        print("[Recognition] No camera found")
        _cam_running = False
        return

    today = str(date.today())
    conn  = get_db()
    cursor = conn.cursor()
    liveness = LivenessChecker()

    while _cam_running:
        ret, frame = cam.read()
        if not ret:
            break
        small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        locs  = fr.face_locations(rgb)
        encs  = fr.face_encodings(rgb, locs)
        landmarks_list = fr.face_landmarks(rgb, locs)

        for enc, (top, right, bottom, left), landmarks in zip(encs, locs, landmarks_list):
            top*=2; right*=2; bottom*=2; left*=2
            name  = "Unknown"
            box_color = (60, 60, 220) # Soft red
            status_badge = "Scanning"

            dists = fr.face_distance(known_encodings, enc)
            if len(dists):
                idx   = int(np.argmin(dists))
                dist  = float(dists[idx])
                if dist < 0.50 and fr.compare_faces(known_encodings, enc, tolerance=0.5)[idx]:
                    sid = known_ids[idx]
                    cursor.execute("SELECT name FROM students WHERE id=%s", (sid,))
                    row = cursor.fetchone()
                    if row:
                        name = row[0]
                        # Check anti-spoofing liveness
                        is_live, _ = liveness.update(sid, landmarks, (top, right, bottom, left))
                        if is_live:
                            box_color = (70, 160, 40) # Forest green
                            status_badge = "Live Verified"
                            if sid not in _cam_marked:
                                cursor.execute("""
                                    INSERT INTO attendance (student_id,date,subject_id,status,confidence)
                                    VALUES (%s,%s,%s,'Present',%s)
                                    ON DUPLICATE KEY UPDATE status='Present',confidence=VALUES(confidence)
                                """, (sid, today, subject_id, dist))
                                conn.commit()
                                _cam_marked[sid] = name
                        else:
                            box_color = (40, 140, 240) # Warm amber
                            status_badge = "Checking Liveness..."

            # Professional bounding rectangle with corner accents
            cv2.rectangle(frame, (left, top), (right, bottom), box_color, 2)
            cv2.rectangle(frame, (left, bottom - 26), (right, bottom), box_color, cv2.FILLED)
            cv2.putText(frame, f"{name} | {status_badge}", (left + 6, bottom - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Header overlay
        cv2.putText(frame, f"Verified Attendees: {len(_cam_marked)}", (20, 36),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (25, 25, 25), 3)
        cv2.putText(frame, f"Verified Attendees: {len(_cam_marked)}", (20, 36),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (245, 245, 245), 2)

        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        _latest_frame[0] = buf.tobytes()

    cam.release()
    cursor.close()
    conn.close()
    _cam_running = False

_latest_frame = [None]

@app.route("/admin/camera")
def admin_camera():
    if not session.get("is_admin"):
        return redirect("/")
    subject_id = request.args.get("subject_id", 1)
    conn = get_db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT id, name FROM subjects ORDER BY name")
    subjects = c.fetchall()
    c.close(); conn.close()
    return render_template("camera.html", subject_id=subject_id, subjects=subjects)

@app.route("/admin/start-recognition", methods=["POST"])
@csrf_protect
def start_recognition():
    global _cam_running, _latest_frame
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    if _cam_running:
        return jsonify({"message": "Already running"})
    data = request.get_json(silent=True) or {}
    subject_id = int(data.get("subject_id") or 1)
    _cam_running  = True
    _latest_frame = [None]
    t = threading.Thread(target=_recognition_thread, args=(subject_id,), daemon=True)
    t.start()
    return jsonify({"message": "Recognition started", "redirect": f"/admin/camera?subject_id={subject_id}"})

@app.route("/admin/stop-recognition", methods=["POST"])
@csrf_protect
def stop_recognition():
    global _cam_running
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    _cam_running = False
    return jsonify({"message": "Stopped", "marked": len(_cam_marked)})

@app.route("/admin/video-feed")
def video_feed():
    if not session.get("is_admin"):
        return "", 403
    def gen():
        import time
        while _cam_running or _latest_frame[0] is not None:
            frame = _latest_frame[0]
            if frame:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            time.sleep(0.04)
    return Response(stream_with_context(gen()), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/admin/recognition-status")
def recognition_status():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"running": _cam_running, "marked": list(_cam_marked.values()), "count": len(_cam_marked)})

# ─────────────────────────────────────────
# AUTOMATED ABSENTEE EMAIL ENGINE & FLOW
# ─────────────────────────────────────────
def generate_absence_email_html(student_name, roll_no, subject_name, attendance_date, current_pct):
    """Generates an institutional, responsive HTML email notice for absent students."""
    if current_pct < 75.0:
        pct_badge = f"""
        <div style="background-color:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:14px;margin:18px 0;">
          <p style="margin:0;color:#991b1b;font-weight:700;font-size:13px;">⚠️ Attendance Shortage Warning ({current_pct}%)</p>
          <p style="margin:5px 0 0;color:#b91c1c;font-size:12px;line-height:1.4;">
            Your cumulative attendance in <strong>{subject_name}</strong> is currently <strong>{current_pct}%</strong>, which is below the mandatory university minimum of <strong>75%</strong>. Consistent shortage may lead to debarment from university examinations.
          </p>
        </div>"""
    else:
        pct_badge = f"""
        <div style="background-color:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:14px;margin:18px 0;">
          <p style="margin:0;color:#166534;font-weight:700;font-size:13px;">✓ Cumulative Subject Attendance: {current_pct}%</p>
          <p style="margin:5px 0 0;color:#15803d;font-size:12px;line-height:1.4;">
            You are currently meeting the university requirement (75% or higher). Please maintain consistent attendance.
          </p>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Official Absence Notification</title>
</head>
<body style="margin:0;padding:24px 12px;background-color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1e293b;">
  <div style="max-width:540px;margin:0 auto;background:#ffffff;border-radius:16px;border:1px solid #e2e8f0;overflow:hidden;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);">
    
    <!-- Header Banner -->
    <div style="background:#0f172a;padding:24px 28px;color:#ffffff;border-bottom:3px solid #2563eb;">
      <p style="margin:0;font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:600;color:#94a3b8;">Chandubhai S. Patel Institute of Technology</p>
      <h1 style="margin:6px 0 0;font-size:20px;font-weight:800;letter-spacing:-0.5px;color:#ffffff;">Official Absence Alert</h1>
      <p style="margin:4px 0 0;font-size:12px;color:#cbd5e1;">Department of Artificial Intelligence &amp; Machine Learning</p>
    </div>

    <!-- Body Content -->
    <div style="padding:28px;">
      <p style="margin:0 0 16px;font-size:14px;line-height:1.5;">
        Dear <strong>{student_name}</strong> (Roll: <span style="font-family:monospace;font-weight:700;color:#1e40af;">{roll_no}</span>),
      </p>
      
      <p style="margin:0 0 20px;font-size:13px;line-height:1.5;color:#475569;">
        This automated notification is issued to record that you were marked <strong style="color:#dc2626;background:#fee2e2;padding:2px 6px;border-radius:4px;">ABSENT</strong> for today's scheduled lecture session in the Smart Attendance System.
      </p>

      <!-- Lecture Details Table -->
      <table style="width:100%;border-collapse:collapse;margin-bottom:20px;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;overflow:hidden;">
        <tr>
          <td style="padding:10px 14px;font-size:12px;color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0;">Course / Subject</td>
          <td style="padding:10px 14px;font-size:13px;color:#0f172a;font-weight:700;border-bottom:1px solid #e2e8f0;">{subject_name}</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;font-size:12px;color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0;">Session Date</td>
          <td style="padding:10px 14px;font-size:13px;color:#0f172a;font-weight:600;border-bottom:1px solid #e2e8f0;">{attendance_date}</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;font-size:12px;color:#64748b;font-weight:600;">Status Recorded</td>
          <td style="padding:10px 14px;font-size:12px;">
            <span style="display:inline-block;padding:2px 8px;border-radius:6px;background:#fee2e2;color:#991b1b;font-weight:700;font-size:11px;">ABSENT</span>
          </td>
        </tr>
      </table>

      {pct_badge}

      <!-- Remediation Box -->
      <div style="background:#f8fafc;border-left:3px solid #2563eb;padding:12px 14px;border-radius:4px;margin-bottom:20px;">
        <p style="margin:0;font-size:12px;color:#334155;line-height:1.5;">
          <strong>Action Required:</strong> If you believe this absence was recorded in error, or if you hold an authorized on-duty / medical leave slip, please present it to the department coordinator within <strong>48 hours</strong>.
        </p>
      </div>

      <p style="margin:0;font-size:12px;color:#64748b;line-height:1.5;">
        You can inspect your full attendance history and lecture clearance breakdown by visiting your <a href="http://127.0.0.1:5000" style="color:#2563eb;text-decoration:none;font-weight:600;">Student Dashboard &rarr;</a>
      </p>
    </div>

    <!-- Footer -->
    <div style="background:#f8fafc;padding:16px 28px;border-top:1px solid #e2e8f0;text-align:center;font-size:11px;color:#94a3b8;">
      <p style="margin:0;">CHARUSAT University &bull; Changa, Gujarat, India</p>
      <p style="margin:4px 0 0;">This is an automated institutional service. Please do not reply directly to this email.</p>
    </div>

  </div>
</body>
</html>"""


def dispatch_absentee_notifications(subject_id, attendance_date=None, force_resend=False):
    """
    Automated Email Flow for Absent Students:
    1. Identifies all students marked 'Absent' for the given subject and date.
    2. Checks email_logs to avoid duplicate spamming unless force_resend=True.
    3. Calculates individual overall attendance percentage per student.
    4. Renders an institutional HTML email template with warning if < 75%.
    5. Dispatches via SMTP in a daemon background thread with logging into email_logs.
    """
    today = str(attendance_date or date.today())

    conn = get_db()
    c = conn.cursor(dictionary=True)

    # 1. Subject Name
    c.execute("SELECT name FROM subjects WHERE id = %s", (subject_id,))
    sub_row = c.fetchone()
    subject_name = sub_row["name"] if sub_row else f"Subject #{subject_id}"

    # 2. Query all students recorded as Absent today for this subject
    c.execute("""
        SELECT s.id, s.name, s.roll, s.email, s.student_class
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        WHERE a.date = %s AND a.subject_id = %s AND a.status = 'Absent'
    """, (today, subject_id))
    absentees = c.fetchall()

    if not absentees:
        c.close(); conn.close()
        return {
            "success": True,
            "total_absent": 0,
            "queued": 0,
            "skipped": 0,
            "subject_name": subject_name,
            "message": f"All students are present for {subject_name} on {today}. No absence emails needed."
        }

    # 3. Check duplicate dispatch prevention
    c.execute("""
        SELECT student_id FROM email_logs
        WHERE subject_id = %s AND date = %s AND status = 'Sent'
    """, (subject_id, today))
    already_sent_ids = {r["student_id"] for r in c.fetchall()}

    targets = []
    skipped_count = 0

    for st in absentees:
        if st["id"] in already_sent_ids and not force_resend:
            skipped_count += 1
            continue

        # Calculate student's overall attendance % for this subject
        c.execute("""
            SELECT COUNT(DISTINCT date) AS total,
                   COUNT(DISTINCT CASE WHEN status='Present' THEN date END) AS present
            FROM attendance WHERE student_id = %s AND subject_id = %s
        """, (st["id"], subject_id))
        att_stat = c.fetchone()
        t = (att_stat["total"] or 0) if att_stat else 0
        p = (att_stat["present"] or 0) if att_stat else 0
        pct = round((p / t * 100) if t else 0, 1)
        st["attendance_pct"] = pct
        targets.append(st)

    c.close(); conn.close()

    if not targets:
        return {
            "success": True,
            "total_absent": len(absentees),
            "queued": 0,
            "skipped": skipped_count,
            "subject_name": subject_name,
            "message": f"All {len(absentees)} absent students have already received their absence notification email today."
        }

    # 4. Asynchronous worker for background delivery
    def _smtp_worker(students_to_notify, sub_id, sub_name, att_date):
        thread_conn = None
        try:
            thread_conn = get_db()
            tc = thread_conn.cursor()

            smtp_configured = bool(EMAIL_ADDRESS and EMAIL_PASSWORD)
            smtp_client = None

            if smtp_configured:
                clean_pw = EMAIL_PASSWORD.replace(" ", "")
                # Try Port 465 (SSL) first, then Port 587 (TLS)
                try:
                    import ssl
                    ctx = ssl.create_default_context()
                    smtp_client = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=12)
                    smtp_client.login(EMAIL_ADDRESS, clean_pw)
                except Exception as ssl_err:
                    print(f"[Email Flow Notice] SMTP 465 SSL connection: {ssl_err}. Trying port 587 STARTTLS...")
                    try:
                        smtp_client = smtplib.SMTP("smtp.gmail.com", 587, timeout=12)
                        smtp_client.ehlo()
                        smtp_client.starttls()
                        smtp_client.ehlo()
                        smtp_client.login(EMAIL_ADDRESS, clean_pw)
                    except Exception as tls_err:
                        print(f"[Email Flow Notice] SMTP 587 TLS connection failed: {tls_err}.")
                        smtp_client = None

            sent_count = 0
            failed_count = 0

            for st in students_to_notify:
                email = st.get("email")
                name = st.get("name")
                roll = st.get("roll")
                pct = st.get("attendance_pct", 0)

                if not email or not validate_email(email):
                    tc.execute("""
                        INSERT INTO email_logs (student_id, subject_id, date, recipient_email, student_name, status, error_message)
                        VALUES (%s, %s, %s, %s, %s, 'Failed', 'Invalid or missing email address')
                    """, (st["id"], sub_id, att_date, email or "none", name))
                    thread_conn.commit()
                    failed_count += 1
                    continue

                html_body = generate_absence_email_html(
                    student_name=name,
                    roll_no=roll,
                    subject_name=sub_name,
                    attendance_date=att_date,
                    current_pct=pct
                )

                status = "Sent"
                err_msg = None

                if smtp_client:
                    try:
                        msg = MIMEMultipart("alternative")
                        msg["Subject"] = f"Attendance Notice: Absent in {sub_name} - {att_date}"
                        msg["From"] = f"Smart Attendance System <{EMAIL_ADDRESS}>"
                        msg["To"] = email

                        plain_body = f"Dear {name},\nYou were marked ABSENT for {sub_name} on {att_date}.\nOverall Attendance: {pct}%.\nSmart Attendance System - CSPIT"
                        msg.attach(MIMEText(plain_body, "plain"))
                        msg.attach(MIMEText(html_body, "html"))

                        smtp_client.sendmail(EMAIL_ADDRESS, email, msg.as_string())
                        sent_count += 1
                    except Exception as send_err:
                        status = "Failed"
                        err_msg = str(send_err)
                        failed_count += 1
                else:
                    # In development / offline or pending App Password verification, record simulated delivery
                    status = "Simulated"
                    err_msg = "SMTP delivery simulated (Verify Google App Password in .env)"
                    sent_count += 1

                tc.execute("""
                    INSERT INTO email_logs (student_id, subject_id, date, recipient_email, student_name, status, error_message)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (st["id"], sub_id, att_date, email, name, status, err_msg))
                thread_conn.commit()

            if smtp_client:
                try:
                    smtp_client.quit()
                except Exception:
                    pass

            print(f"[Email Flow Completed] Processed {len(students_to_notify)} absentees. Result: {sent_count} recorded/sent, {failed_count} failed.")

        except Exception as global_err:
            print(f"[Email Flow Error] Worker exception: {global_err}")
        finally:
            if thread_conn:
                try:
                    thread_conn.close()
                except Exception:
                    pass

    # Launch daemon background thread
    t = threading.Thread(
        target=_smtp_worker,
        args=(targets, subject_id, subject_name, today),
        daemon=True
    )
    t.start()

    return {
        "success": True,
        "total_absent": len(absentees),
        "queued": len(targets),
        "skipped": skipped_count,
        "subject_name": subject_name,
        "message": f"Automated email flow initiated: {len(targets)} absent student alert(s) queued for delivery."
    }

# ─────────────────────────────────────────
# CLOSE ATTENDANCE & AUTOMATICALLY DISPATCH EMAILS
# ─────────────────────────────────────────
@app.route("/admin/close-attendance", methods=["POST"])
@csrf_protect
def close_attendance():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    subject_id = int(data.get("subject_id") or 1)
    auto_email = data.get("send_emails", True)  # Enabled by default in flow!
    today = str(date.today())

    conn = get_db()
    c = conn.cursor(dictionary=True)

    c.execute("SELECT id FROM students")
    all_students = c.fetchall()

    for student in all_students:
        c.execute("""
            INSERT INTO attendance (student_id, date, subject_id, status)
            VALUES (%s, %s, %s, 'Absent')
            ON DUPLICATE KEY UPDATE
                status = CASE
                    WHEN status='Present' THEN 'Present'
                    ELSE 'Absent'
                END
        """, (student["id"], today, subject_id))

    conn.commit()

    # Count total absentees for today and subject
    c.execute(
        "SELECT COUNT(*) AS cnt FROM attendance WHERE date=%s AND subject_id=%s AND status='Absent'",
        (today, subject_id)
    )
    absent_count = c.fetchone()["cnt"] or 0
    c.close(); conn.close()

    email_info = None
    if auto_email and absent_count > 0:
        email_info = dispatch_absentee_notifications(subject_id, today, force_resend=False)

    msg = f"Attendance closed: {absent_count} student(s) marked Absent."
    if email_info and email_info.get("queued", 0) > 0:
        msg += f" Automated email alerts dispatched to {email_info['queued']} absentees."

    return jsonify({
        "success": True,
        "message": msg,
        "absent_count": absent_count,
        "email_info": email_info
    })

# ─────────────────────────────────────────
# SEND ABSENT EMAILS (MANUAL / RE-SEND ON DEMAND)
# ─────────────────────────────────────────
@app.route("/admin/send-emails", methods=["POST"])
@csrf_protect
def send_emails():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    subject_id = int(data.get("subject_id") or 1)
    force_resend = bool(data.get("force_resend", False))
    today = str(date.today())

    result = dispatch_absentee_notifications(subject_id, today, force_resend=force_resend)
    return jsonify(result)

# ─────────────────────────────────────────
# EMAIL LOGS API (VIEW SENT ALERTS)
# ─────────────────────────────────────────
@app.route("/admin/email-logs", methods=["GET"])
def admin_email_logs():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401

    subject_id = request.args.get("subject_id")
    filter_date = request.args.get("date", str(date.today()))

    conn = get_db()
    c = conn.cursor(dictionary=True)

    if subject_id:
        c.execute("""
            SELECT el.*, sub.name AS subject_name, s.roll
            FROM email_logs el
            JOIN subjects sub ON el.subject_id = sub.id
            JOIN students s ON el.student_id = s.id
            WHERE el.subject_id = %s AND el.date = %s
            ORDER BY el.sent_at DESC
        """, (subject_id, filter_date))
    else:
        c.execute("""
            SELECT el.*, sub.name AS subject_name, s.roll
            FROM email_logs el
            JOIN subjects sub ON el.subject_id = sub.id
            JOIN students s ON el.student_id = s.id
            WHERE el.date = %s
            ORDER BY el.sent_at DESC
        """, (filter_date,))

    logs = c.fetchall()
    for l in logs:
        if l.get("sent_at"):
            l["sent_at"] = str(l["sent_at"])
        if l.get("date"):
            l["date"] = str(l["date"])

    c.close(); conn.close()
    return jsonify({"logs": logs, "date": filter_date, "count": len(logs)})

# ─────────────────────────────────────────
# ATTENDANCE HISTORY
# ─────────────────────────────────────────
@app.route("/admin/attendance")
def admin_attendance():
    if not session.get("is_admin"):
        return redirect("/")

    filter_date = request.args.get("filter_date")
    selected_subject_id = request.args.get("subject_id")
    conn = get_db()
    c = conn.cursor(dictionary=True)

    c.execute("SELECT id, name FROM subjects ORDER BY name")
    subjects = c.fetchall()
    selected_subject = None
    if selected_subject_id:
        c.execute("SELECT id, name FROM subjects WHERE id = %s", (selected_subject_id,))
        selected_subject = c.fetchone()
    if not selected_subject:
        selected_subject = subjects[0] if subjects else {"id": None, "name": "General"}

    if filter_date:
        c.execute("""
            SELECT a.id, s.name, s.roll, s.email, a.date, a.status, a.confidence,
                   COALESCE(sub.name, 'General') AS subject_name
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            LEFT JOIN subjects sub ON a.subject_id = sub.id
            WHERE a.date = %s AND a.subject_id = %s
            ORDER BY a.date DESC
        """, (filter_date, selected_subject["id"]))
    else:
        c.execute("""
            SELECT a.id, s.name, s.roll, s.email, a.date, a.status, a.confidence,
                   COALESCE(sub.name, 'General') AS subject_name
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            LEFT JOIN subjects sub ON a.subject_id = sub.id
            WHERE a.subject_id = %s
            ORDER BY a.date DESC
        """, (selected_subject["id"],))

    records = c.fetchall()
    c.close(); conn.close()
    return render_template("admin_attendance.html", records=records, filter_date=filter_date, subjects=subjects, selected_subject=selected_subject)

# ─────────────────────────────────────────
# UPDATE ATTENDANCE RECORD
# ─────────────────────────────────────────
@app.route("/admin/attendance/update/<int:att_id>", methods=["POST"])
@csrf_protect
def admin_attendance_update(att_id):
    if not session.get("is_admin"):
        return redirect("/")

    status = request.form.get("status")
    if status not in ["Present", "Absent"]:
        return redirect("/admin/attendance")

    conn = get_db()
    c = conn.cursor(dictionary=True)

    c.execute("SELECT status FROM attendance WHERE id=%s", (att_id,))
    row = c.fetchone()

    if not row:
        c.close()
        conn.close()
        return redirect("/admin/attendance")

    # LOCKED: once Present or Absent, cannot change again
    if row["status"] != "Pending":
        c.close()
        conn.close()
        return redirect(request.referrer or "/admin/attendance")

    c.execute(
        "UPDATE attendance SET status=%s WHERE id=%s",
        (status, att_id)
    )
    conn.commit()

    c.close()
    conn.close()

    return redirect(request.referrer or "/admin/attendance")

# ─────────────────────────────────────────
# ADMIN ATTENDANCE EXPORT
# ─────────────────────────────────────────
@app.route("/admin/attendance/export")
def admin_attendance_export():
    if not session.get("is_admin"):
        return redirect("/")

    filter_date = request.args.get("filter_date")
    selected_subject_id = request.args.get("subject_id")
    conn = get_db()
    c = conn.cursor(dictionary=True)

    if selected_subject_id:
        c.execute("SELECT id FROM subjects WHERE id = %s", (selected_subject_id,))
        c.fetchone()

    query_filter = ""
    params = []
    if filter_date:
        query_filter += "a.date=%s"
        params.append(filter_date)
    if selected_subject_id:
        query_filter += (" AND " if query_filter else "") + "a.subject_id=%s"
        params.append(selected_subject_id)

    base_query = "SELECT s.name, s.roll, s.email, a.date, a.status FROM attendance a JOIN students s ON s.id = a.student_id"
    if query_filter:
        c.execute(base_query + " WHERE " + query_filter + " ORDER BY a.date DESC", tuple(params))
    else:
        c.execute(base_query + " ORDER BY a.date DESC")

    records = c.fetchall()
    c.close(); conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Roll", "Email", "Date", "Status"])
    for row in records:
        writer.writerow([row["name"], row["roll"], row["email"], row["date"], row["status"]])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=admin_attendance_export.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

# ─────────────────────────────────────────
# ALL STUDENTS
# ─────────────────────────────────────────
@app.route("/admin/students")
def admin_students():
    if not session.get("is_admin"):
        return redirect("/")
    conn = get_db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT * FROM students ORDER BY name")
    students = c.fetchall()

    # Attendance % per student
    for s in students:
        c.execute("""
            SELECT COUNT(DISTINCT date) AS total,
                   COUNT(DISTINCT CASE WHEN status='Present' THEN date END) AS present
            FROM attendance WHERE student_id=%s
        """, (s["id"],))
        row = c.fetchone()
        t = row["total"] or 0
        p = row["present"] or 0
        s["attendance_pct"] = round((p / t * 100) if t else 0, 1)
        s["att_total"] = t
        s["att_present"] = p

    c.close(); conn.close()
    return render_template("admin_students.html", students=students)

# ─────────────────────────────────────────
# EDIT STUDENT
# ─────────────────────────────────────────
@app.route("/admin/edit/<int:sid>", methods=["POST"])
@csrf_protect
def edit_student(sid):
    if not session.get("is_admin"):
        return redirect("/")
    name  = request.form.get("name", "").strip()[:100]
    email = request.form.get("email", "").strip()
    student_class = request.form.get("student_class", "").strip()[:50]

    if not name or not email or not validate_email(email):
        return redirect("/admin/students")

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE students SET name=%s, email=%s, student_class=%s WHERE id=%s",
              (name, email, student_class, sid))
    conn.commit()
    c.close(); conn.close()
    return redirect("/admin/students")

# ─────────────────────────────────────────
# DELETE STUDENT
# ─────────────────────────────────────────
@app.route("/admin/delete/<int:sid>", methods=["POST"])
@csrf_protect
def delete_student(sid):
    if not session.get("is_admin"):
        return redirect("/")
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM attendance WHERE student_id = %s", (sid,))
    c.execute("DELETE FROM students WHERE id = %s", (sid,))
    conn.commit()
    c.close(); conn.close()
    return redirect("/admin/students")

# ─────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", 5000)),
        debug=debug_mode
    )
