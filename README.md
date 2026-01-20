# 🎓 Smart Attendance System using Face Recognition & Email Notification

## 📌 Project Description
The Smart Attendance System using Face Recognition is an automated attendance management application developed using Python and computer vision techniques. The system captures real-time video through a webcam, detects student faces, and recognizes them using previously trained facial data. Based on recognition results, the system automatically marks attendance without any manual effort. After the attendance session is completed, students who are not detected are marked absent, and an automatic email notification is sent to inform them about their absence. A simple web-based dashboard is also provided to view attendance records.

This project is designed to reduce manual work, prevent proxy attendance, and improve accuracy in attendance management systems used in educational institutions.

---

## 🎯 Objectives
- To automate the attendance process using face recognition
- To reduce proxy and fake attendance
- To save time for teachers and institutions
- To notify absent students automatically via email
- To provide a simple and user-friendly attendance dashboard

---

## 🚀 Features
- Real-time face detection using webcam
- Accurate face recognition using trained data
- Automatic attendance marking with date and time
- Identification of absent students
- Email notification to absent students
- Web-based attendance dashboard
- Contactless and secure attendance system
- Easy to use and deploy

---

## 🧠 System Workflow
1. Student face images are collected and stored in the dataset.
2. Facial features are extracted and encoded during the training phase.
3. Live video feed is captured using a webcam.
4. Faces are detected in each video frame.
5. Detected faces are compared with stored encodings.
6. Recognized students are marked as present.
7. Unrecognized or missing students are marked absent.
8. Email notifications are sent to absent students.
9. Attendance records are displayed on a web dashboard.

---

## 🛠️ Technologies Used
- Python (Core programming language)
- OpenCV (Face detection and image processing)
- Face Recognition Library (Face encoding and matching)
- Flask (Web framework for dashboard)
- Pandas (Data handling and CSV operations)
- NumPy (Numerical computations)
- SMTP (Email sending service)
- HTML (Dashboard rendering)
- VS Code (Development environment)

---

## 📂 Project Structure
Smart_Attendance/
│
├── dataset/ # Student face images
│ ├── Student_1/
│ ├── Student_2/
│
├── attendance.csv # Attendance records
├── students_email.py # Student email mapping
├── train_faces.py # Face training script
├── attendance.py # Face detection & attendance
├── send_mail.py # Email notification script
├── app.py # Flask dashboard
└── README.md


