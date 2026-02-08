# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# from config.config import Config

# class EmailSender:
#     def __init__(self):
#         self.email_user = Config.EMAIL_USER
#         self.email_pass = Config.EMAIL_PASS
#         self.smtp_server = Config.SMTP_SERVER
#         self.smtp_port = Config.SMTP_PORT
    
#     def send_email(self, recipient, subject, message, is_html=True):
#         """Send email to recipient"""
#         try:
#             if not self.email_user or not self.email_pass:
#                 print("Email credentials not configured")
#                 return False
            
#             # Create message
#             msg = MIMEMultipart('alternative')
#             msg['Subject'] = subject
#             msg['From'] = self.email_user
#             msg['To'] = recipient
            
#             # Attach message
#             if is_html:
#                 msg.attach(MIMEText(message, 'html'))
#             else:
#                 msg.attach(MIMEText(message, 'plain'))
            
#             # Send email
#             with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
#                 server.starttls()
#                 server.login(self.email_user, self.email_pass)
#                 server.send_message(msg)
            
#             print(f"Email sent to {recipient}")
#             return True
#         except Exception as e:
#             print(f"Error sending email: {e}")
#             return False
    
#     def send_attendance_confirmation(self, email, name, session_name):
#         """Send attendance confirmation email"""
#         subject = "Attendance Marked - Confirmation"
#         message = f"""
#         <html>
#             <body style="font-family: Arial, sans-serif;">
#                 <h2>Attendance Confirmation</h2>
#                 <p>Dear {name},</p>
#                 <p>Your attendance has been successfully marked for the <strong>{session_name}</strong> session.</p>
#                 <p>
#                     <strong>Details:</strong><br>
#                     Date: {self._get_today()}<br>
#                     Session: {session_name}
#                 </p>
#                 <p>Thank you!</p>
#                 <p><small>This is an automated message from Smart Attendance System</small></p>
#             </body>
#         </html>
#         """
#         return self.send_email(email, subject, message)
    
#     def send_absence_notification(self, email, name, session_name):
#         """Send absence notification email"""
#         subject = "Marked Absent - Action Required"
#         message = f"""
#         <html>
#             <body style="font-family: Arial, sans-serif;">
#                 <h2>Absence Notification</h2>
#                 <p>Dear {name},</p>
#                 <p>You have been marked <strong>absent</strong> for the <strong>{session_name}</strong> session.</p>
#                 <p>
#                     <strong>Details:</strong><br>
#                     Date: {self._get_today()}<br>
#                     Session: {session_name}
#                 </p>
#                 <p>Please contact the administrator if this is incorrect.</p>
#                 <p>Thank you!</p>
#                 <p><small>This is an automated message from Smart Attendance System</small></p>
#             </body>
#         </html>
#         """
#         return self.send_email(email, subject, message)
    
#     def send_bulk_absence_notification(self, recipients_list):
#         """Send bulk absence notifications"""
#         """
#         recipients_list format: [
#             {'email': 'student@example.com', 'name': 'Student Name', 'session': 'morning'},
#             ...
#         ]
#         """
#         results = {'success': 0, 'failed': 0}
#         for recipient in recipients_list:
#             if self.send_absence_notification(
#                 recipient['email'],
#                 recipient['name'],
#                 recipient['session']
#             ):
#                 results['success'] += 1
#             else:
#                 results['failed'] += 1
        
#         return results
    
#     def send_welcome_email(self, email, name):
#         """Send welcome email to new student"""
#         subject = "Welcome to Smart Attendance System"
#         message = f"""
#         <html>
#             <body style="font-family: Arial, sans-serif;">
#                 <h2>Welcome to Smart Attendance System!</h2>
#                 <p>Dear {name},</p>
#                 <p>Thank you for registering with our Smart Attendance System.</p>
#                 <p>Your account has been successfully created. You can now:</p>
#                 <ul>
#                     <li>Log in to your dashboard</li>
#                     <li>Mark attendance using face recognition</li>
#                     <li>View your attendance records</li>
#                     <li>Receive attendance notifications</li>
#                 </ul>
#                 <p>Please keep your password secure and do not share it with anyone.</p>
#                 <p>If you have any questions, please contact the administrator.</p>
#                 <p>Thank you!</p>
#                 <p><small>This is an automated message from Smart Attendance System</small></p>
#             </body>
#         </html>
#         """
#         return self.send_email(email, subject, message)
    
#     def send_password_reset_email(self, email, name, reset_link):
#         """Send password reset email"""
#         subject = "Password Reset Request - Smart Attendance System"
#         message = f"""
#         <html>
#             <body style="font-family: Arial, sans-serif;">
#                 <h2>Password Reset Request</h2>
#                 <p>Dear {name},</p>
#                 <p>We received a request to reset your password for your Smart Attendance System account.</p>
#                 <p>Click the link below to reset your password (valid for 1 hour):</p>
#                 <p><a href="{reset_link}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a></p>
#                 <p>Or copy and paste this link in your browser:</p>
#                 <p><code>{reset_link}</code></p>
#                 <p>If you did not request a password reset, please ignore this email.</p>
#                 <p>This link will expire in 1 hour.</p>
#                 <p>Best regards,<br>Smart Attendance System Team</p>
#                 <p><small>This is an automated message from Smart Attendance System</small></p>
#             </body>
#         </html>
#         """
#         return self.send_email(email, subject, message)
    
#     @staticmethod
#     def _get_today():
#         """Get today's date"""
#         from datetime import date
#         return date.today().strftime("%Y-%m-%d")

# # Create a global email sender instance
# email_sender = EmailSender()



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


