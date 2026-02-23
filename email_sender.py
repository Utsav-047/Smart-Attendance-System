
import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import date
from email_config import EMAIL_ADDRESS, EMAIL_PASSWORD

# -------- DATABASE --------
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

today = str(date.today())

# -------- GET ALL STUDENTS --------
cursor.execute("SELECT id, name, email FROM students")
students = cursor.fetchall()

# -------- GET PRESENT STUDENTS --------
cursor.execute(
    "SELECT student_id FROM attendance WHERE date = ? AND status = 'Present'",
    (today,)
)
present_ids = {row[0] for row in cursor.fetchall()}

conn.close()

# -------- EMAIL SERVER --------
server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

sent_count = 0

for student_id, name, email in students:
    if student_id not in present_ids:
        body = f"""
Dear {name},

You were marked ABSENT today ({today}).

If this is a mistake, please contact the admin.

Regards,
Smart Attendance System
"""

        msg = MIMEText(body)
        msg["Subject"] = "Attendance Alert"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = email

        server.sendmail(EMAIL_ADDRESS, email, msg.as_string())
        sent_count += 1

server.quit()

print(f" Emails sent to {sent_count} absent students")
import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import date
from email_config import EMAIL_ADDRESS, EMAIL_PASSWORD

# -------- DATABASE --------
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

today = str(date.today())

# -------- GET ALL STUDENTS --------
cursor.execute("SELECT id, name, email FROM students")
students = cursor.fetchall()

# -------- GET PRESENT STUDENTS --------
cursor.execute(
    "SELECT student_id FROM attendance WHERE date = ? AND status = 'Present'",
    (today,)
)
present_ids = {row[0] for row in cursor.fetchall()}

conn.close()

# -------- EMAIL SERVER --------
server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

sent_count = 0

for student_id, name, email in students:
    if student_id not in present_ids:
        body = f"""
Dear {name},

You were marked ABSENT today ({today}).

If this is a mistake, please contact the admin.

Regards,
Smart Attendance System
"""

        msg = MIMEText(body)
        msg["Subject"] = "Attendance Alert"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = email

        server.sendmail(EMAIL_ADDRESS, email, msg.as_string())
        sent_count += 1

server.quit()

print(f" Emails sent to {sent_count} absent students")



