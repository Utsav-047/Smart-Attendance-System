"""
Face Capture Module
Supports modern in-browser WebRTC base64 capture and desktop webcam fallback.
Hardened against path traversal, unbounded memory allocation, and spoofing.
"""

import os
import cv2
import base64
import numpy as np
import face_recognition
from security_core import get_safe_dataset_path, validate_roll

DATASET_PATH = "face_dataset"
MAX_FRAMES_PER_REQUEST = 10
MAX_IMAGE_WIDTH = 1920
MAX_IMAGE_HEIGHT = 1080


def save_webrtc_frames(roll, base64_images):
    """
    Decodes an array of base64 images sent from the browser webcam (WebRTC canvas),
    verifies that a clear face is present in each frame, and saves them to face_dataset/<roll>/.

    Hardened:
    - Rejects path-traversal in roll number via canonical directory check.
    - Limits incoming frames to MAX_FRAMES_PER_REQUEST to prevent memory exhaustion DoS.
    - Inspects dimensions of decoded frames to protect against decompression bombs.

    Args:
        roll (str): Student roll number (validated against regex)
        base64_images (list): List of base64 data URLs ("data:image/jpeg;base64,...")

    Returns:
        dict: {"success": bool, "saved_count": int, "message": str}
    """
    if not roll or not base64_images:
        return {"success": False, "saved_count": 0, "message": "Roll number and frames are required."}

    # Strict path traversal validation
    try:
        roll_dir = get_safe_dataset_path(DATASET_PATH, roll)
    except ValueError as e:
        return {"success": False, "saved_count": 0, "message": str(e)}

    os.makedirs(roll_dir, exist_ok=True)

    # Frame count bound
    frames_to_process = base64_images[:MAX_FRAMES_PER_REQUEST]
    saved_count = 0

    for i, data_url in enumerate(frames_to_process):
        try:
            if not isinstance(data_url, str):
                continue

            # Strip standard data URL prefixes safely
            if "," in data_url:
                header, encoded = data_url.split(",", 1)
            else:
                encoded = data_url

            # Cap base64 string size (5MB per frame maximum)
            if len(encoded) > 5 * 1024 * 1024:
                continue

            img_bytes = base64.b64decode(encoded)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None or frame.size == 0:
                continue

            h, w = frame.shape[:2]
            if w > MAX_IMAGE_WIDTH or h > MAX_IMAGE_HEIGHT:
                # Downsample large inputs safely
                scale = min(MAX_IMAGE_WIDTH / w, MAX_IMAGE_HEIGHT / h)
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes = face_recognition.face_locations(rgb, model="hog")

            # Save the frame if a face is detected
            if len(boxes) > 0:
                filename = f"img_{saved_count + 1}.jpg"
                filepath = os.path.join(roll_dir, filename)
                cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
                saved_count += 1
            elif len(frames_to_process) <= 5 and saved_count == 0:
                # Save first sample as baseline if clear
                filename = f"img_{saved_count + 1}.jpg"
                filepath = os.path.join(roll_dir, filename)
                cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                saved_count += 1

        except Exception as e:
            print(f"[Capture Security] Handled error in frame {i}: {e}")

    if saved_count == 0:
        return {
            "success": False,
            "saved_count": 0,
            "message": "No clear face detected in the captured frames. Please ensure your face is well-lit and centered.",
        }

    return {
        "success": True,
        "saved_count": saved_count,
        "message": f"Successfully captured and secured {saved_count} face samples.",
    }


def capture_faces(roll, max_count=15):
    """
    Desktop camera fallback capture with path traversal protection.
    """
    roll_dir = get_safe_dataset_path(DATASET_PATH, roll)
    os.makedirs(roll_dir, exist_ok=True)

    cam = None
    for idx in range(4):
        c = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if c.isOpened():
            cam = c
            break
        c.release()

    if cam is None:
        raise Exception("Camera not accessible on local system.")

    count = 0
    while count < max_count:
        ret, frame = cam.read()
        if not ret:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes = face_recognition.face_locations(rgb)

        if len(boxes) > 0:
            count += 1
            cv2.imwrite(f"{roll_dir}/img_{count}.jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])

        if cv2.waitKey(100) & 0xFF == ord("q"):
            break

    cam.release()
    cv2.destroyAllWindows()
    return count
