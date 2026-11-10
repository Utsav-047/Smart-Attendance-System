"""
Face Encoding Module
Extracts 128-dimensional deep feature embeddings from captured face images
and securely saves them with SHA256-HMAC integrity verification.
"""

import os
import cv2
import numpy as np
import mysql.connector
import face_recognition
from dotenv import load_dotenv
from security_core import save_secure_pickle, load_secure_pickle, validate_roll

load_dotenv()

DATASET_PATH = "face_dataset"
ENCODINGS_FILE = "encodings.pkl"


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3307)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "attendance_db"),
    )


def encode_all_faces(secret_key=None):
    """
    Scans the dataset folder, detects faces, computes 128-d embeddings,
    and cryptographically signs & saves to encodings.pkl. Returns count of encodings saved.
    """
    if not os.path.exists(DATASET_PATH):
        print(f"[Encode] Dataset directory '{DATASET_PATH}' does not exist.")
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()

    known_encodings = []
    known_ids = []

    print("[Encode] Processing student face dataset...")

    for roll in os.listdir(DATASET_PATH):
        if not validate_roll(roll):
            continue

        folder = os.path.join(DATASET_PATH, roll)
        if not os.path.isdir(folder):
            continue

        cursor.execute("SELECT id FROM students WHERE roll=%s", (roll,))
        result = cursor.fetchone()
        if result is None:
            continue

        student_id = result[0]

        for img_name in os.listdir(folder):
            if not img_name.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            img_path = os.path.join(folder, img_name)
            image = cv2.imread(img_path)
            if image is None:
                continue

            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            boxes = face_recognition.face_locations(rgb, model="hog")
            if len(boxes) == 0:
                continue

            encodings = face_recognition.face_encodings(rgb, boxes)
            if len(encodings) > 0:
                known_encodings.append(encodings[0])
                known_ids.append(student_id)

    cursor.close()
    conn.close()

    data = {
        "encodings": known_encodings,
        "student_ids": known_ids,
    }

    # Secure signed save
    save_secure_pickle(data, ENCODINGS_FILE, secret_key=secret_key)

    count = len(known_encodings)
    print(f"[Encode] Successfully saved and cryptographically signed {count} face encodings to {ENCODINGS_FILE}")
    return count


if __name__ == "__main__":
    encode_all_faces()
