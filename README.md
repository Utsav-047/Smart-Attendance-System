# 📷 Smart Attendance System Using Face Recognition

> An AI-powered web-based attendance system that uses **face recognition** to automatically mark student attendance, with **automated email alerts** for absent students and a full **admin dashboard**.

---

## 👨‍💻 Developed By

| Student ID | Name |
|------------|------|
| 24AIML047 | Patel Utsav |
| 24AIML044 | Patel Renish |

**Institution:** Chandubhai S. Patel Institute of Technology (CSPIT)  
**Department:** Artificial Intelligence & Machine Learning  
**University:** CHARUSAT

---

## 🚀 Features

- 🤖 **AI Face Recognition** — Automatically detects and identifies students using OpenCV LBPH
- ⏳ **3-Stage Attendance** — Pending → Present → Absent flow
- 📧 **Auto Email Alerts** — Sends absence notification emails to absent students
- 🔒 **Close Attendance** — Admin can lock attendance, converting all Pending to Absent
- 📊 **Admin Dashboard** — Live stats, attendance rate progress bar, today's records
- 📅 **Attendance History** — Filter by date, view all records
- 👨‍🎓 **Student Portal** — Students can view their own attendance percentage and history
- 🗄️ **MySQL Database** — All data stored in MySQL via XAMPP
- 🔐 **Secure Login** — Hashed passwords using Werkzeug

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask |
| Face Recognition | OpenCV (LBPH), Haar Cascade |
| Database | MySQL (XAMPP) |
| Frontend | HTML, Bootstrap 5, Font Awesome |
| Email | Python smtplib (Gmail SMTP) |
| Security | Werkzeug password hashing |

---

## 📁 Project Structure

```
ATTENDANCE_SYSTEM/
├── app.py                    # Main Flask application
├── capture_faces.py          # Capture student face images
├── train_model.py            # Train LBPH face recognition model
├── recognize_attendance.py   # Run face recognition & mark attendance
├── reset_today_attendance.py # Reset today's attendance records
├── email_config.py           # Gmail SMTP configuration
├── requirements.txt          # Python dependencies
├── trainer.yml               # Trained face model (auto-generated)
├── face_dataset/             # Captured face images (auto-generated)
│   └── <roll_number>/
│       └── img1.jpg ...
└── templates/
    ├── login.html
    ├── register.html
    ├── admin_dashboard.html
    ├── admin_attendance.html
    ├── admin_students.html
    └── student_dashboard.html
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites

- Python 3.14
- XAMPP (Apache + MySQL)
- Git

### 2. Clone the Repository

```bash
git clone https://github.com/yourusername/smart-attendance-system.git
cd smart-attendance-system
```

### 3. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Setup Database

1. Open **XAMPP Control Panel**
2. Start **Apache** and **MySQL**
3. Open **phpMyAdmin** → http://localhost/phpmyadmin
4. Create a new database named `attendance_db`
5. Tables are created **automatically** when you run the app

### 6. Configure Email

Open `email_config.py` and update:

```python
EMAIL_ADDRESS  = "your_email@gmail.com"
EMAIL_PASSWORD = "your_gmail_app_password"
```

> **How to get Gmail App Password:**
> Google Account → Security → 2-Step Verification → App Passwords → Generate

### 7. Run the Application

```bash
python app.py
```

Open browser → **http://localhost:5000**

---

## 📋 How to Use

### First Time Setup

```
1. Run app.py
2. Register student at http://localhost:5000/register
3. Run capture_faces.py → enter roll number → capture 20 face images
4. Run train_model.py → trains the recognition model
5. Login as admin → Start Face Recognition
```

### Daily Use

```
1. Start XAMPP → Apache + MySQL
2. Activate venv → python app.py
3. Admin Dashboard → Start Face Recognition
4. Press Q when done
5. Click Close Attendance → Pending becomes Absent
6. Click Send Absent Emails → emails sent automatically
```

### Adding New Student

```
1. Register on website
2. Run capture_faces.py
3. Run train_model.py
4. Done!
```

---

## 🔑 Default Admin Credentials

| Field | Value |
|-------|-------|
| Email | admin@gmail.com |
| Password | admin123 |

---

## 📊 Attendance Status Flow

```
Morning → All students: ⏳ PENDING
              ↓
    Start Face Recognition
              ↓
    Face matched → ✅ PRESENT
              ↓
    Click Close Attendance
              ↓
    Remaining → ❌ ABSENT
              ↓
    Send Absent Emails → 📧 Email sent
```

---

## 📸 Screenshots

> Admin Dashboard — shows total, present, absent, pending stats with live progress bar

> Face Recognition — camera window opens, detects and marks attendance in real time

> Student Dashboard — shows attendance percentage, history, and 75% threshold warning

---

## 📦 Requirements

```
Flask==3.1.3
mysql-connector-python==9.6.0
opencv-contrib-python==4.13.0.92
numpy==2.4.2
Werkzeug==3.1.6
```

---

## ⚠️ Important Notes

- Make sure **XAMPP MySQL is running** before starting the app
- Run `capture_faces.py` and `train_model.py` again after adding any new student
- Face recognition accuracy depends on **good lighting** and **clear face visibility**
- Confidence threshold is set to `< 45` — lower = stricter matching

---

## 🙏 Acknowledgements

- [OpenCV](https://opencv.org/) — Face detection and recognition
- [Flask](https://flask.palletsprojects.com/) — Web framework
- [Bootstrap](https://getbootstrap.com/) — Frontend UI
- [XAMPP](https://www.apachefriends.org/) — Local MySQL server

---

<p align="center">Made with ❤️ by Patel Utsav & Patel Renish | CSPIT AIML 2024</p>
