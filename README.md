# Smart Attendance System with Face Recognition

A comprehensive attendance management system using face detection and recognition, with separate dashboards for students and administrators, automated email notifications, and time-based session management.

## Features

### For Students
- Face recognition-based attendance marking
- Personal dashboard with attendance statistics
- View attendance history
- Email notifications for attendance confirmation
- Real-time session tracking

### For Administrators
- Complete attendance management system
- View all students and their attendance records
- Mark absent students automatically
- Send bulk email notifications to absent students
- Generate attendance reports
- Dashboard with real-time statistics
- Manage attendance sessions

### System Features
- **Face Recognition**: Uses OpenCV and face_recognition library
- **Time Sessions**: Morning, Afternoon, Evening sessions
- **Email Notifications**: Automatic emails for absent students
- **Secure Authentication**: Password hashing and session management
- **Database**: SQLite for data persistence
- **Responsive UI**: Bootstrap-based modern interface

## Installation

### Prerequisites
- Python 3.8 or higher
- Webcam for face recognition
- Gmail account for email notifications (or other SMTP server)

### Step 1: Clone or Download the Project

```bash
# Create project directory
mkdir smart_attendance_system
cd smart_attendance_system
```

### Step 2: Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

**Note**: Installing `face_recognition` requires dlib, which may need additional dependencies:

**For Windows:**
```bash
pip install cmake
pip install dlib
pip install face_recognition
```

**For Linux/Mac:**
```bash
sudo apt-get install cmake
pip install dlib
pip install face_recognition
```

### Step 3: Configure Email Settings

Create a `.env` file in the root directory:

```env
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
SECRET_KEY=your-secret-key-here
```

**To get Gmail App Password:**
1. Go to Google Account settings
2. Security > 2-Step Verification
3. App passwords > Select app: Mail
4. Copy the generated password

### Step 4: Create Required Directories

```bash
mkdir -p static/images/students
mkdir -p config
mkdir -p database
mkdir -p face_recognition
mkdir -p email_service
mkdir -p templates
mkdir -p utils
```

### Step 5: Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Default Login Credentials

**Admin Account:**
- Email: `admin@attendance.com`
- Password: `admin123`

**Note**: Change these credentials in production!

## Usage Guide

### For Students

1. **Register**:
   - Go to `/register`
   - Fill in student ID, name, email, password
   - Upload a clear photo of your face
   - Submit registration

2. **Login**:
   - Use your registered email and password
   - Access student dashboard

3. **Mark Attendance**:
   - Click "Start Face Recognition" during active session
   - Look at the webcam
   - System will detect and verify your face
   - Attendance marked automatically
   - Receive confirmation email

### For Administrators

1. **Login**:
   - Use admin credentials
   - Access admin dashboard

2. **View Students**:
   - Navigate to Students section
   - View all registered students

3. **Mark Absent Students**:
   - Click "Mark Absent & Send Emails"
   - System automatically marks absent students
   - Sends email notifications to all absent students

4. **Generate Reports**:
   - Navigate to Reports section
   - Select date range
   - View/download attendance reports

## Project Structure

```
smart_attendance_system/
│
├── config/
│   └── config.py                 # Configuration settings
│
├── database/
│   └── db_manager.py             # Database models and operations
│
├── face_recognition/
│   ├── face_detector.py          # Face detection and recognition
│   └── face_trainer.py           # (Optional) Train models
│
├── email_service/
│   └── email_sender.py           # Email notification service
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│       └── students/             # Student photos
│
├── templates/
│   ├── admin_dashboard.html      # Admin interface
│   ├── student_dashboard.html    # Student interface
│   ├── login.html                # Login page
│   └── register.html             # Registration page
│
├── app.py                        # Main application
├── requirements.txt              # Dependencies
├── attendance.db                 # SQLite database (auto-created)
└── README.md                     # This file
```

## Configuration

### Attendance Sessions

Edit `config/config.py` to modify session times:

```python
ATTENDANCE_SESSIONS = {
    'morning': {'start': '08:00', 'end': '09:00'},
    'afternoon': {'start': '13:00', 'end': '14:00'},
    'evening': {'start': '17:00', 'end': '18:00'}
}
```

### Face Recognition Tolerance

Adjust recognition strictness (lower = more strict):

```python
TOLERANCE = 0.6  # Range: 0.0 to 1.0
```

## Troubleshooting

### Face Recognition Not Working
- Ensure good lighting
- Look directly at the camera
- Avoid wearing masks or sunglasses
- Check if webcam is accessible

### Email Not Sending
- Verify Gmail app password
- Check EMAIL_USER and EMAIL_PASS in .env
- Enable "Less secure app access" or use App Password
- Check spam folder

### Database Errors
- Delete `attendance.db` and restart to recreate
- Check file permissions

### Installation Issues
- For dlib errors: Install cmake first
- For OpenCV errors: Try `pip install opencv-python-headless`
- Use Python 3.8-3.10 for best compatibility

## API Endpoints

- `GET /` - Home page
- `GET/POST /login` - Login page
- `GET/POST /register` - Registration page
- `GET /logout` - Logout
- `GET /student/dashboard` - Student dashboard
- `GET /admin/dashboard` - Admin dashboard
- `POST /mark_attendance` - Mark attendance via face recognition
- `GET /admin/mark_absent` - Mark absent students and send emails
- `GET /admin/students` - View all students
- `GET /admin/reports` - Generate reports

## Security Considerations

1. **Production Deployment**:
   - Change default admin credentials
   - Use strong SECRET_KEY
   - Enable HTTPS
   - Use production database (PostgreSQL/MySQL)
   - Set DEBUG=False

2. **Password Security**:
   - Passwords are hashed using Werkzeug
   - Never store plain text passwords

3. **Face Data**:
   - Face encodings stored as text in database
   - Student photos stored locally
   - Consider encryption for sensitive data

## Future Enhancements

- [ ] Multi-camera support
- [ ] Mobile app integration
- [ ] Biometric authentication
- [ ] Advanced reporting and analytics
- [ ] Integration with LMS
- [ ] Parent portal
- [ ] SMS notifications
- [ ] Geolocation verification
- [ ] Export to Excel/PDF


## Support

For issues or questions, please create an issue in the project repository.

## Contributors

Created as a smart attendance management solution with face recognition technology.
