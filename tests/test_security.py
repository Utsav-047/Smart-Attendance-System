"""
Comprehensive Automated Security Verification Test Suite
Smart Attendance System - DevSecOps & Security Hardening
Tests OWASP Top 10 mitigations, biometric protections, CSRF, HMAC, and input validation.
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from security_core import (
    generate_csrf_token,
    validate_csrf_token,
    SlidingWindowRateLimiter,
    save_secure_pickle,
    load_secure_pickle,
    SecurityTamperError,
    validate_roll,
    validate_email,
    validate_password_strength,
    get_safe_dataset_path
)
import app
from capture_faces import save_webrtc_frames


class TestSecurityCoreUnits(unittest.TestCase):
    """Unit tests for security primitives in security_core.py."""

    def test_csrf_token_validation(self):
        """Test that CSRF tokens validate correctly and reject mismatched tokens."""
        session_dict = {}
        token = generate_csrf_token(session_dict)
        self.assertIsNotNone(token)
        self.assertTrue(len(token) >= 32)
        # Valid token matches session
        self.assertTrue(validate_csrf_token(token, session_dict))
        # Tampered or wrong token fails
        self.assertFalse(validate_csrf_token("invalid-token-here", session_dict))
        self.assertFalse(validate_csrf_token("", session_dict))
        self.assertFalse(validate_csrf_token(None, session_dict))

    def test_rate_limiter_sliding_window(self):
        """Test rate limiter threshold enforcement and IP/action isolation."""
        limiter = SlidingWindowRateLimiter()
        key = "test_ip_1:login"
        
        # Allow 3 attempts within 10 seconds
        for _ in range(3):
            allowed, remaining = limiter.is_allowed(key, max_requests=3, window_seconds=10)
            self.assertTrue(allowed)

        # 4th attempt should be blocked
        allowed, retry_after = limiter.is_allowed(key, max_requests=3, window_seconds=10)
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)

        # Different key is still allowed
        other_allowed, _ = limiter.is_allowed("test_ip_2:login", max_requests=3, window_seconds=10)
        self.assertTrue(other_allowed)

    def test_hmac_pickle_integrity_and_tampering(self):
        """Test secure HMAC pickle serialization and tamper detection."""
        test_file = "test_encodings_temp.pkl"
        payload = {"encodings": [[0.1, 0.2, 0.3]], "names": ["Student1"]}
        key = b"test_secret_hmac_signing_key_32_bytes!!"

        try:
            # 1. Save valid envelope
            save_secure_pickle(payload, test_file, key=key)
            self.assertTrue(os.path.exists(test_file))

            # 2. Load valid envelope
            loaded = load_secure_pickle(test_file, key=key)
            self.assertEqual(loaded["names"], ["Student1"])

            # 3. Tamper with the raw payload bytes
            with open(test_file, "rb") as f:
                import pickle
                envelope = pickle.load(f)
            envelope["payload"] = envelope["payload"][:-4] + b"AAAA"
            with open(test_file, "wb") as f:
                pickle.dump(envelope, f)

            with self.assertRaises(SecurityTamperError):
                load_secure_pickle(test_file, key=key)

            # 4. Tamper with the key (verification with wrong key)
            save_secure_pickle(payload, test_file, key=key)
            wrong_key = b"different_attack_signing_key_32_bytes!!"
            with self.assertRaises(SecurityTamperError):
                load_secure_pickle(test_file, key=wrong_key)

        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_safe_dataset_path_traversal_prevention(self):
        """Test path traversal blocking on face dataset directory paths."""
        base_dir = os.path.abspath("test_face_dataset")
        os.makedirs(base_dir, exist_ok=True)

        try:
            # Legitimate roll numbers
            safe_path = get_safe_dataset_path(base_dir, "21CE050")
            self.assertTrue(safe_path.startswith(base_dir))
            self.assertTrue(safe_path.endswith("21CE050"))

            safe_path2 = get_safe_dataset_path(base_dir, "student_01")
            self.assertTrue(safe_path2.startswith(base_dir))

            # Directory traversal attacks (POSIX and Windows separators)
            traversal_vectors = [
                "../../etc/passwd",
                "..\\..\\Windows\\System32",
                "../sensitive.txt",
                "21CE050/../../root",
                "foo/bar",
                "/absolute/path",
                "C:\\Windows\\win.ini",
                "roll\x00extra",
                "",
                None
            ]

            for vector in traversal_vectors:
                with self.assertRaises(ValueError, msg=f"Vector '{vector}' should have been rejected"):
                    get_safe_dataset_path(base_dir, vector)

        finally:
            if os.path.exists(base_dir):
                import shutil
                shutil.rmtree(base_dir, ignore_errors=True)

    def test_roll_validation(self):
        """Test roll number format validator."""
        self.assertTrue(validate_roll("21CE050"))
        self.assertTrue(validate_roll("D21IT001"))
        self.assertTrue(validate_roll("STUDENT_123"))
        self.assertTrue(validate_roll("CS-2024-01"))

        # Invalid formats / Injection attempts
        self.assertFalse(validate_roll("../21CE050"))
        self.assertFalse(validate_roll("21CE050' OR 1=1--"))
        self.assertFalse(validate_roll("<script>"))
        self.assertFalse(validate_roll("roll with spaces"))
        self.assertFalse(validate_roll("a" * 35))  # Too long

    def test_email_validation(self):
        """Test email address regex and injection blocking."""
        self.assertTrue(validate_email("student@charusat.edu.in"))
        self.assertTrue(validate_email("admin.lab@university.ac.in"))
        self.assertTrue(validate_email("test_user@example.com"))

        # Invalid formats
        self.assertFalse(validate_email("plainaddress"))
        self.assertFalse(validate_email("user@.com"))
        self.assertFalse(validate_email("user@domain..com"))
        self.assertFalse(validate_email("student<script>@charusat.edu.in"))
        self.assertFalse(validate_email(""))
        self.assertFalse(validate_email(None))

    def test_password_strength_validator(self):
        """Test password strength policy enforcement."""
        # Weak passwords
        valid, err = validate_password_strength("short")
        self.assertFalse(valid)
        self.assertIn("at least 8", err)

        valid, err = validate_password_strength("alllowercase123")
        self.assertFalse(valid)
        self.assertIn("uppercase", err)

        valid, err = validate_password_strength("ALLUPPERCASE123")
        self.assertFalse(valid)
        self.assertIn("lowercase", err)

        valid, err = validate_password_strength("NoDigitsHere!")
        self.assertFalse(valid)
        self.assertIn("digit", err)

        # Strong passwords
        valid, err = validate_password_strength("SecureP@ssw0rd2026")
        self.assertTrue(valid)
        self.assertIsNone(err)


class TestFlaskSecurityIntegration(unittest.TestCase):
    """Integration security tests using the Flask test client."""

    def setUp(self):
        app.app.config["TESTING"] = True
        app.app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.app.test_client()

    def test_security_headers_present_on_all_responses(self):
        """Test that HTTP security headers (CSP, X-Frame-Options, etc.) are injected."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

        # Critical Security Headers
        self.assertIn("X-Frame-Options", res.headers)
        self.assertEqual(res.headers["X-Frame-Options"], "SAMEORIGIN")

        self.assertIn("X-Content-Type-Options", res.headers)
        self.assertEqual(res.headers["X-Content-Type-Options"], "nosniff")

        self.assertIn("Content-Security-Policy", res.headers)
        self.assertIn("default-src 'self'", res.headers["Content-Security-Policy"])

        self.assertIn("Referrer-Policy", res.headers)
        self.assertIn("Permissions-Policy", res.headers)

    def test_csrf_protection_rejects_post_without_token(self):
        """Test that POST to protected endpoints without CSRF token returns 403 Forbidden."""
        protected_routes = [
            "/",
            "/api/forgot-password/send-otp",
            "/api/forgot-password/verify-otp",
            "/api/forgot-password/reset",
            "/admin/register",
            "/admin/start-recognition",
            "/admin/stop-recognition",
            "/admin/close-attendance",
            "/admin/send-emails",
            "/admin/reset-attendance",
            "/admin/subjects/add",
            "/admin/attendance/update/1",
            "/admin/edit/1",
            "/admin/delete/1",
            "/api/capture-webrtc"
        ]

        for route in protected_routes:
            res = self.client.post(route, data={"sample": "data"})
            self.assertEqual(
                res.status_code,
                403,
                f"Route {route} allowed POST without CSRF token!"
            )
            # Response should indicate CSRF failure
            self.assertTrue(
                b"CSRF" in res.data or b"403" in res.data or res.is_json,
                f"Route {route} did not provide CSRF error response"
            )

    def test_csrf_protection_accepts_valid_header_token(self):
        """Test that POST with valid session CSRF token is accepted past the CSRF gate."""
        with self.client.session_transaction() as sess:
            token = generate_csrf_token(sess)

        # Send request with X-CSRFToken header
        res = self.client.post(
            "/api/capture-webrtc",
            headers={"X-CSRFToken": token},
            data=json.dumps({"roll": "TEST01", "frames": []}),
            content_type="application/json"
        )
        # Should NOT be 403 Forbidden (may be 400 for empty frames, showing it passed CSRF)
        self.assertNotEqual(res.status_code, 403)
        self.assertEqual(res.status_code, 400)

    def test_rate_limiting_on_login(self):
        """Test that burst POST requests to /login trigger 429 Too Many Requests."""
        with self.client.session_transaction() as sess:
            token = generate_csrf_token(sess)

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor

        # Login has rate limit of 10 requests per 60 seconds
        got_429 = False
        with patch("app.get_db", return_value=mock_conn):
            for i in range(15):
                res = self.client.post(
                    "/",
                    data={"csrf_token": token, "email": "test@charusat.edu.in", "password": "wrong"},
                    environ_overrides={"REMOTE_ADDR": "192.168.1.100"}
                )
                if res.status_code == 429:
                    got_429 = True
                    break

        self.assertTrue(got_429, "Rate limiter failed to block burst requests to /login")

    def test_webrtc_capture_payload_sanitization(self):
        """Test biometric WebRTC capture bounds, preventing buffer overflow / DoS and traversal."""
        # Empty frames list
        empty_res = save_webrtc_frames("21CE001", [])
        self.assertFalse(empty_res["success"])
        self.assertEqual(empty_res["saved_count"], 0)

        # Path traversal in roll
        traversal_res = save_webrtc_frames("../../test", ["data:image/jpeg;base64,ZmFrZQ=="])
        self.assertFalse(traversal_res["success"])
        self.assertTrue("Invalid" in traversal_res["message"] or "traversal" in traversal_res["message"])


    def test_biometric_unauthorized_overwrite_prevention(self):
        """Test that biometric endpoints block unauthorized overwrite of registered student faces."""
        with self.client.session_transaction() as sess:
            token = generate_csrf_token(sess)

        # Mock DB to simulate student '21CE050' already registered
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 101, "name": "Alice"}
        mock_conn.cursor.return_value = mock_cursor

        with patch("app.get_db", return_value=mock_conn):
            res = self.client.post(
                "/api/capture-webrtc",
                headers={"X-CSRFToken": token},
                data=json.dumps({"roll": "21CE050", "frames": ["data:image/jpeg;base64,ZmFrZQ=="]}),
                content_type="application/json"
            )
            # Unauthenticated attacker attempting to overwrite Alice's face must be rejected
            self.assertEqual(res.status_code, 403)
            self.assertIn("already registered", res.get_json().get("message", ""))

    def test_timed_password_reset_token_security(self):
        """Test cryptographic timed password reset token integrity and expiry."""
        email = "student@charusat.edu.in"
        token = app.generate_reset_token(email)
        self.assertIsNotNone(token)

        # Valid token decodes correctly
        verified = app.verify_reset_token(token, max_age_seconds=900)
        self.assertEqual(verified, email)

        # Tampered token is rejected
        tampered = token[:-4] + "abcd"
        self.assertIsNone(app.verify_reset_token(tampered))

        # Expired token is rejected
        expired = app.verify_reset_token(token, max_age_seconds=-1)
        self.assertIsNone(expired)

    def test_generate_absence_email_html_structure(self):
        """Test HTML email generation content, personalizations, and 75% warning logic."""
        # Case A: Below 75% threshold (warning badge)
        html_low = app.generate_absence_email_html(
            student_name="Rahul Sharma",
            roll_no="21CE050",
            subject_name="Machine Learning",
            attendance_date="2026-11-08",
            current_pct=64.5
        )
        self.assertIn("Rahul Sharma", html_low)
        self.assertIn("21CE050", html_low)
        self.assertIn("Machine Learning", html_low)
        self.assertIn("2026-11-08", html_low)
        self.assertIn("ABSENT", html_low)
        self.assertIn("Attendance Shortage Warning", html_low)
        self.assertIn("64.5%", html_low)

        # Case B: At or above 75% threshold (good standing badge)
        html_good = app.generate_absence_email_html(
            student_name="Priya Patel",
            roll_no="21CE099",
            subject_name="Cloud Computing",
            attendance_date="2026-11-08",
            current_pct=88.0
        )
        self.assertIn("Priya Patel", html_good)
        self.assertIn("meeting the university requirement", html_good)
        self.assertIn("88.0%", html_good)

    def test_automated_email_dispatch_on_close_attendance(self):
        """Test that /admin/close-attendance triggers the automated absentee email flow."""
        with self.client.session_transaction() as sess:
            token = generate_csrf_token(sess)
            sess["is_admin"] = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # Mock student roster and absentee count
        mock_cursor.fetchall.return_value = [{"id": 1, "name": "Test Student"}]
        mock_cursor.fetchone.return_value = {"cnt": 1}
        mock_conn.cursor.return_value = mock_cursor

        with patch("app.get_db", return_value=mock_conn):
            with patch("app.dispatch_absentee_notifications") as mock_dispatch:
                mock_dispatch.return_value = {
                    "success": True,
                    "total_absent": 1,
                    "queued": 1,
                    "skipped": 0,
                    "message": "1 email queued"
                }

                res = self.client.post(
                    "/admin/close-attendance",
                    headers={"X-CSRFToken": token},
                    data=json.dumps({"subject_id": 2, "send_emails": True}),
                    content_type="application/json"
                )

                self.assertEqual(res.status_code, 200)
                json_data = res.get_json()
                self.assertTrue(json_data["success"])
                self.assertIn("Automated email alerts dispatched", json_data["message"])
                mock_dispatch.assert_called_once()
                args, kwargs = mock_dispatch.call_args
                self.assertEqual(args[0], 2)

    def test_email_logs_endpoint_rbac(self):
        """Test that /admin/email-logs enforces admin authentication."""
        # Unauthenticated request rejected
        unauth_res = self.client.get("/admin/email-logs")
        self.assertEqual(unauth_res.status_code, 401)

        # Authenticated admin request accepted
        with self.client.session_transaction() as sess:
            sess["is_admin"] = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor

        with patch("app.get_db", return_value=mock_conn):
            auth_res = self.client.get("/admin/email-logs?subject_id=1")
            self.assertEqual(auth_res.status_code, 200)
            self.assertIn("logs", auth_res.get_json())


    def test_otp_recovery_flow_full(self):
        """Test the end-to-end 3-step OTP recovery flow: send OTP, verify OTP, and reset password."""
        # 1. Test Send OTP
        with self.client.session_transaction() as sess:
            token = generate_csrf_token(sess)

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "name": "Kishan Patel",
            "email": "kishan@charusat.edu.in",
            "roll": "21CE050"
        }
        mock_conn.cursor.return_value = mock_cursor

        with patch("app.get_db", return_value=mock_conn), patch("app.send_otp_email_async") as mock_mail:
            send_res = self.client.post(
                "/api/forgot-password/send-otp",
                headers={"X-CSRFToken": token},
                data=json.dumps({"identifier": "21CE050"}),
                content_type="application/json"
            )
            self.assertEqual(send_res.status_code, 200)
            data = send_res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["masked_email"], "k****n@charusat.edu.in")
            mock_mail.assert_called_once()
            _, mail_args, _ = mock_mail.mock_calls[0]
            generated_otp = mail_args[2]

        # 2. Test Invalid OTP rejected
        with self.client.session_transaction() as sess:
            token2 = generate_csrf_token(sess)

        invalid_res = self.client.post(
            "/api/forgot-password/verify-otp",
            headers={"X-CSRFToken": token2},
            data=json.dumps({"otp": "000000"}),
            content_type="application/json"
        )
        self.assertEqual(invalid_res.status_code, 400)
        self.assertFalse(invalid_res.get_json()["success"])

        # 3. Test Valid OTP accepted
        valid_res = self.client.post(
            "/api/forgot-password/verify-otp",
            headers={"X-CSRFToken": token2},
            data=json.dumps({"otp": generated_otp}),
            content_type="application/json"
        )
        self.assertEqual(valid_res.status_code, 200)
        reset_token = valid_res.get_json()["reset_token"]
        self.assertIsNotNone(reset_token)

        # 4. Test Password Reset
        with self.client.session_transaction() as sess:
            token3 = generate_csrf_token(sess)

        with patch("app.get_db", return_value=mock_conn):
            reset_res = self.client.post(
                "/api/forgot-password/reset",
                headers={"X-CSRFToken": token3},
                data=json.dumps({
                    "password": "StrongPassword123!",
                    "confirm_password": "StrongPassword123!",
                    "reset_token": reset_token
                }),
                content_type="application/json"
            )
            self.assertEqual(reset_res.status_code, 200)
            self.assertTrue(reset_res.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
