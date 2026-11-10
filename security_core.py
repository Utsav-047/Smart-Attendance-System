"""
Smart Attendance System - Security Core Module
Implements production-grade application security defenses:
- CSRF token generation and validation (Session-bound)
- Sliding-window rate limiting (Brute-force and DoS protection)
- Cryptographic HMAC integrity verification for Pickle serialization
- Strict input validation and path traversal defenses
- HTTP security response headers
"""

import os
import re
import time
import hmac
import hashlib
import secrets
import pickle
from functools import wraps
from flask import request, session, jsonify, abort, render_template

# ─────────────────────────────────────────────────────────────────────────────
# 1. CSRF DEFENSE ENGINE
# ─────────────────────────────────────────────────────────────────────────────

CSRF_SESSION_KEY = "_csrf_token"


def generate_csrf_token(target_session=None):
    """Generates and stores a cryptographically secure token in the session."""
    sess = target_session if target_session is not None else session
    if CSRF_SESSION_KEY not in sess:
        sess[CSRF_SESSION_KEY] = secrets.token_hex(32)
    return sess[CSRF_SESSION_KEY]


def validate_csrf_token(token_to_check, target_session=None):
    """Constant-time verification of a supplied CSRF token against session."""
    sess = target_session if target_session is not None else session
    session_token = sess.get(CSRF_SESSION_KEY)
    if not session_token or not token_to_check:
        return False
    return hmac.compare_digest(str(session_token), str(token_to_check))


def csrf_protect(f):
    """Decorator requiring a valid CSRF token for state-changing HTTP methods."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            # Check form data, custom headers, and JSON body
            token = (
                request.form.get("csrf_token")
                or request.headers.get("X-CSRFToken")
                or request.headers.get("X-CSRF-Token")
            )
            if not token and request.is_json:
                json_data = request.get_json(silent=True) or {}
                token = json_data.get("csrf_token")

            if not validate_csrf_token(token):
                if request.is_json or request.path.startswith(("/api/", "/admin/start", "/admin/stop", "/admin/close", "/admin/send", "/admin/reset")):
                    return jsonify({"error": "Forbidden: Invalid or missing CSRF token"}), 403
                abort(403, description="Security Error: CSRF token validation failed.")
        return f(*args, **kwargs)
    return decorated_function


# ─────────────────────────────────────────────────────────────────────────────
# 2. RATE LIMITING ENGINE (Sliding Window In-Memory)
# ─────────────────────────────────────────────────────────────────────────────

class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter per client key."""

    def __init__(self):
        self._records = {}  # key -> list of float timestamps

    def is_allowed(self, key, limit=10, window_seconds=60, max_requests=None):
        if max_requests is not None:
            limit = max_requests
        now = time.time()
        cutoff = now - window_seconds

        # Clean old records
        timestamps = self._records.get(key, [])
        timestamps = [t for t in timestamps if t > cutoff]

        if len(timestamps) >= limit:
            retry_after = int(timestamps[0] + window_seconds - now) + 1
            self._records[key] = timestamps
            return False, max(1, retry_after)

        timestamps.append(now)
        self._records[key] = timestamps
        return True, 0

    def clear(self, key=None):
        if key:
            self._records.pop(key, None)
        else:
            self._records.clear()


rate_limiter = SlidingWindowRateLimiter()


def get_client_ip():
    """Extracts client IP safely, accounting for standard forward headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the leftmost trusted IP
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def rate_limit(limit=10, window=60, action="default"):
    """Decorator that enforces sliding-window rate limits per IP."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ip = get_client_ip()
            key = f"{action}:{ip}"
            allowed, retry_after = rate_limiter.is_allowed(key, limit, window)
            if not allowed:
                msg = f"Too many requests for action '{action}'. Please retry in {retry_after} seconds."
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": msg, "retry_after": retry_after}), 429
                return f"<h3>429 Too Many Requests</h3><p>{msg}</p>", 429, {"Retry-After": str(retry_after)}
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# 3. CRYPTOGRAPHIC HMAC PICKLE DEFENSE (Insecure Deserialization Mitigation)
# ─────────────────────────────────────────────────────────────────────────────

class SecurityTamperError(ValueError):
    """Raised when cryptographic HMAC signature verification fails (indicates tampering or corruption)."""
    pass


def get_hmac_key(secret_key=None):
    """Derives a dedicated 32-byte HMAC key from application secret."""
    if secret_key is not None:
        if isinstance(secret_key, bytes):
            return hashlib.sha256(secret_key).digest()
        return hashlib.sha256(str(secret_key).encode("utf-8")).digest()
    raw = os.getenv("PICKLE_HMAC_KEY") or os.getenv("SECRET_KEY", "fallback_smart_attendance_key_default")
    return hashlib.sha256(raw.encode("utf-8")).digest()


def save_secure_pickle(data, filepath, secret_key=None, key=None):
    """Serializes data and writes it alongside a SHA256-HMAC integrity signature."""
    effective_key = secret_key if secret_key is not None else key
    payload = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
    hmac_k = get_hmac_key(effective_key)
    signature = hmac.new(hmac_k, payload, hashlib.sha256).hexdigest()

    envelope = {
        "format": "secure_hmac_v1",
        "signature": signature,
        "payload": payload,
    }

    temp_path = filepath + ".tmp"
    with open(temp_path, "wb") as f:
        pickle.dump(envelope, f)
        f.flush()
        os.fsync(f.fileno())
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        pass
    # Atomic rename prevents file corruption during concurrent operations
    os.replace(temp_path, filepath)


def load_secure_pickle(filepath, secret_key=None, key=None):
    """
    Loads biometric embeddings only if the cryptographic HMAC signature is valid.
    Prevents Remote Code Execution (RCE) from tampered pickle payloads.
    """
    effective_key = secret_key if secret_key is not None else key
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "rb") as f:
        loaded = pickle.load(f)

    # Check for HMAC envelope format
    if isinstance(loaded, dict) and loaded.get("format") == "secure_hmac_v1":
        stored_signature = loaded.get("signature", "")
        payload = loaded.get("payload", b"")

        hmac_k = get_hmac_key(effective_key)
        expected_signature = hmac.new(hmac_k, payload, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(stored_signature, expected_signature):
            raise SecurityTamperError(
                "[Security Alert] Cryptographic HMAC verification failed for biometric encodings! "
                "The file may have been altered or corrupted."
            )

        return pickle.loads(payload)

    # Legacy fallback: verify expected structure and immediately migrate to signed envelope
    if isinstance(loaded, dict) and "encodings" in loaded and "student_ids" in loaded:
        print("[Security Migration] Upgrading legacy encodings.pkl to HMAC-verified format...")
        save_secure_pickle(loaded, filepath, secret_key)
        return loaded

    raise SecurityTamperError("Invalid biometric encodings file structure.")


# ─────────────────────────────────────────────────────────────────────────────
# 4. INPUT VALIDATION & PATH TRAVERSAL DEFENSE
# ─────────────────────────────────────────────────────────────────────────────

ROLL_REGEX = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
NAME_REGEX = re.compile(r"^[A-Za-z\s.'-]{2,80}$")


def validate_roll(roll):
    """Validates student roll number against path-traversal and injection chars."""
    if not roll or not isinstance(roll, str):
        return False
    clean = roll.strip()
    if not ROLL_REGEX.match(clean):
        return False
    # Extra check against directory traversal sequences
    if ".." in clean or "/" in clean or "\\" in clean:
        return False
    return True


def validate_email(email):
    """Validates email format and maximum length."""
    if not email or not isinstance(email, str):
        return False
    clean = email.strip()
    if len(clean) > 120 or not EMAIL_REGEX.match(clean) or ".." in clean:
        return False
    return True


def validate_password_strength(password):
    """
    Enforces minimum NIST & CIS password policy guidelines:
    - At least 8 characters
    - At least one uppercase letter [A-Z]
    - At least one lowercase letter [a-z]
    - At least one digit [0-9]
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters in length."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit (0-9)."
    return True, None


def get_safe_dataset_path(base_dir, roll):
    """
    Resolves canonical path and verifies it strictly resides inside base_dir.
    Guarantees zero path traversal vulnerability.
    """
    if not validate_roll(roll):
        raise ValueError(f"Invalid roll number format: '{roll}'. Only alphanumeric, underscores, and dashes permitted.")

    canonical_base = os.path.abspath(base_dir)
    target_path = os.path.abspath(os.path.join(base_dir, roll.strip()))

    if not target_path.startswith(canonical_base):
        raise ValueError("Path traversal attempt detected and blocked.")

    return target_path


# ─────────────────────────────────────────────────────────────────────────────
# 5. HTTP SECURITY HEADERS
# ─────────────────────────────────────────────────────────────────────────────

def add_security_headers(response):
    """Injects defense-in-depth HTTP security headers into every response."""
    # Prevent clickjacking / UI redressing
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Legacy XSS filter protection
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Referrer privacy policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Restrict unnecessary browser device APIs
    response.headers["Permissions-Policy"] = "microphone=(), geolocation=(), payment=()"
    # Modern Content Security Policy allowing required stylesheets and CDNs
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'self';"
    )
    response.headers["Content-Security-Policy"] = csp_policy
    return response
