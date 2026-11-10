# Smart Attendance System

An institutional, AI-powered biometric attendance automation platform utilizing deep learning facial recognition, anti-spoofing liveness verification, in-browser WebRTC face capture, and automated academic notification workflows.

Designed and engineered for higher education institutions following production-grade security standards and the OWASP Top 10 defensive framework.

---

## Academic Information

- **Institution:** Chandubhai S. Patel Institute of Technology (CSPIT)
- **Department:** Artificial Intelligence & Machine Learning
- **University:** CHARUSAT

---

## Key Features

- **Deep Learning Biometrics:** Employs 128-dimensional facial embeddings (dlib ResNet backbone) for high-accuracy verification.
- **Anti-Spoofing & Liveness Verification:** Eye Aspect Ratio (EAR) blink detection and head pose micro-variance tracking prevent presentation attacks from smartphones, printed photos, and screen replays.
- **In-Browser WebRTC Capture:** Students enroll facial biometrics directly from modern web browsers with interactive visual feedback, target alignment reticles, and multi-frame quality validation.
- **Zero-Trust Security Core:** Comprehensive CSRF defense, sliding-window rate limiters, anti-enumeration protections, parameterized queries, and HTTP security headers (CSP, HSTS, X-Frame-Options).
- **Anti-RCE Serialized Encodings:** Cryptographically signed pickle envelopes utilizing HMAC-SHA256 to eliminate Remote Code Execution risks from untrusted model payloads.
- **3-Step Cryptographic OTP Recovery:** Secure password reset wizard with 6-digit random codes, constant-time HMAC comparison, 10-minute expiry, and 5-attempt anti-brute force lockouts.
- **Academic Compliance Management:** Automated calculation and real-time tracking of the university's 75% attendance threshold with dynamic shortfall calculators.
- **Automated Absence Notification:** Background asynchronous SMTP email alerts dispatched to absent students and guardians upon lecture session finalization.
- **Modular Asset Architecture:** Fully decoupled, human-crafted light aesthetic with Plus Jakarta Sans typography, high-contrast indicators, and zero AI-generated emojis.

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Python 3, Flask, Werkzeug |
| **Biometrics & Computer Vision** | `face_recognition`, `dlib`, `OpenCV` |
| **Anti-Spoofing & Liveness** | 68-point facial landmark tracking, Eye Aspect Ratio (EAR) (`liveness.py`) |
| **Security Framework** | Custom zero-trust defensive core (`security_core.py`), HMAC-SHA256, itsdangerous |
| **Frontend Architecture** | Decoupled HTML5, Tailwind CSS, Plus Jakarta Sans, Font Awesome, Chart.js |
| **Database** | MySQL / MariaDB (Enterprise relational schema) |
| **Email Service** | Asynchronous SMTP with TLS/SSL encryption |
| **Testing** | Python `unittest` (comprehensive 18-suite security integration tests) |

---

## Security Architecture & Hardening

| Security Domain | Defense-in-Depth Implementation |
|---|---|
| **Authentication & Password Storage** | Werkzeug PBKDF2-SHA256 / bcrypt salted hashes; live NIST/CIS password strength policy enforcement (length, upper, lower, digit). |
| **Cross-Site Request Forgery (CSRF)** | Session-bound cryptographically random tokens validated on all state-changing `POST` endpoints via request headers (`X-CSRFToken`) and form bodies. |
| **Rate Limiting & Brute-Force Defense** | Sliding-window memory limiters on sensitive endpoints (`/login`, `/api/forgot-password/*`, WebRTC captures) returning `429 Too Many Requests`. |
| **Biometric RCE Prevention** | Biometric embeddings are serialized in tamper-evident envelopes signed with HMAC-SHA256 (`save_secure_pickle` / `load_secure_pickle`). Tampered payloads are rejected immediately. |
| **Path Traversal & Biometric Overwrite** | Canonical path resolution (`os.path.realpath`) restricts file operations strictly within `face_dataset/`. Unauthenticated overwrite of existing student biometric profiles is blocked. |
| **Credential & Secret Protection** | Zero secrets in source code; 100% environment-driven configuration via `.env` with a sanitized `.env.example` template. |
| **HTTP Security Headers** | Automated injection of `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy`. |

---

## Installation & Setup

### 1. Prerequisites
- **Python 3.10+**
- **MySQL Server** (via XAMPP, Docker, or standalone service)
- **C++ Build Tools** (required by `dlib` and `CMake`)

### 2. Clone the Repository
```bash
git clone https://github.com/Utsav-047/Smart-Attendance-System.git
cd Smart-Attendance-System
```

### 3. Create and Activate Virtual Environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Environment Configuration
Copy `.env.example` to create your local `.env`:
```bash
cp .env.example .env
```
Configure your database and mail credentials in `.env`:
```ini
SECRET_KEY=generate_a_strong_random_secret_key_here

DB_HOST=localhost
DB_PORT=3307
DB_USER=root
DB_PASSWORD=your_db_password
DB_NAME=attendance_db

EMAIL_ADDRESS=your_institutional_email@gmail.com
EMAIL_PASSWORD=your_16_char_google_app_password

DEFAULT_ADMIN_EMAIL=admin@institution.edu
DEFAULT_ADMIN_PASSWORD=AdminPassword!2026
```

### 6. Run Automated Security Test Suite
Verify that all defensive mechanisms pass before starting the server:
```bash
python -m unittest tests/test_security.py -v
```

### 7. Run the Application
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000`.

---

## Project Directory Structure

```
Smart-Attendance-System/
├── app.py                     # Main Flask application and secure API routing
├── security_core.py           # Zero-Trust security engine (CSRF, HMAC pickles, rate limiting, sanitization)
├── capture_faces.py           # In-browser WebRTC frame decoder and directory sanitizer
├── encode_faces.py            # Deep feature extractor (128-d encodings generator)
├── liveness.py                # Anti-spoofing and Eye Aspect Ratio (EAR) validator
├── recognize_attendance.py    # Standalone CLI recognition module with liveness checks
├── email_config.py            # SMTP configuration helper with environment fallback
├── requirements.txt           # Python package requirements
├── .env.example               # Sanitized production environment template
├── .gitignore                 # Exclusion rules protecting secrets, biometrics, and cache
├── static/                    # Modular front-end assets
│   ├── css/
│   │   ├── main.css           # Core typography, Plus Jakarta Sans, tabular numbers
│   │   ├── auth.css           # Authentication cards, step indicators, OTP boxes
│   │   └── camera.css         # Facial alignment reticle, pulse radar animations
│   └── js/
│       ├── forgot_password.js # 3-step OTP wizard engine with countdown timers
│       ├── login.js           # Institutional sign-in handler & visibility toggles
│       ├── camera.js          # Live recognition HUD, attendance polling & email dispatch
│       ├── register.js        # Multi-frame WebRTC camera capture & sample validation
│       └── admin_dashboard.js # Chart.js doughnut metrics, roster filtering, email logs modal
├── templates/                 # Modular, viewer-friendly HTML templates
│   ├── login.html             # Institutional sign-in
│   ├── register.html          # Student biometric enrollment portal
│   ├── forgot_password.html   # 3-step OTP recovery wizard
│   ├── camera.html            # Live facial recognition and attendee roster HUD
│   ├── admin_dashboard.html   # Administrator executive dashboard & KPI metrics
│   ├── admin_attendance.html  # Attendance audit history and CSV report exporter
│   ├── admin_students.html    # Student directory and compliance monitoring
│   ├── admin_register.html    # Administrator account provisioner
│   ├── student_dashboard.html # Student personal portal with 75% goal tracker
│   └── student_profile.html   # Student academic profile and historical timeline
└── tests/
    └── test_security.py       # 18-suite unit & integration security tests
```

---

## Verification & Automated Testing

The project includes an automated test suite verifying both functional and defensive controls:
```bash
$ python -m unittest tests/test_security.py -v
test_automated_email_dispatch_on_close_attendance ... ok
test_biometric_unauthorized_overwrite_prevention ... ok
test_csrf_protection_accepts_valid_header_token ... ok
test_csrf_protection_rejects_post_without_token ... ok
test_email_logs_endpoint_rbac ... ok
test_generate_absence_email_html_structure ... ok
test_otp_recovery_flow_full ... ok
test_rate_limiting_on_login ... ok
test_security_headers_present_on_all_responses ... ok
test_timed_password_reset_token_security ... ok
test_webrtc_capture_payload_sanitization ... ok
test_csrf_token_validation ... ok
test_email_validation ... ok
test_hmac_pickle_integrity_and_tampering ... ok
test_password_strength_validator ... ok
test_rate_limiter_sliding_window ... ok
test_roll_validation ... ok
test_safe_dataset_path_traversal_prevention ... ok

Ran 18 tests in 0.20s - OK
```

---

## License & Attribution

Developed for academic and educational administration under institutional guidelines.
All rights reserved &copy; CSPIT, CHARUSAT University.
