"""
CLI Attendance Recognition Module
Runs face recognition with anti-spoofing liveness checks from command-line.
"""

import sys
import os
import cv2
import pickle
import numpy as np
import mysql.connector
import face_recognition
from datetime import date
from dotenv import load_dotenv
from liveness import LivenessChecker
from security_core import load_secure_pickle

load_dotenv()

subject_id = 1
if len(sys.argv) > 1:
    try:
        subject_id = int(sys.argv[1])
    except ValueError:
        subject_id = 1

# Load verified face encodings
if not os.path.exists("encodings.pkl"):
    print("[Error] encodings.pkl not found. Please run encode_faces.py first.")
    sys.exit(1)

try:
    data = load_secure_pickle("encodings.pkl")
    known_encodings = data["encodings"]
    known_ids = data["student_ids"]
except Exception as e:
    print(f"[Security Error] Failed to load verified encodings: {e}")
    sys.exit(1)

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3307)),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "attendance_db"),
)
cursor = conn.cursor()

today = str(date.today())
marked_students = set()
liveness = LivenessChecker()


def open_camera(max_index=3):
    for i in range(max_index + 1):
        cam = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cam.isOpened():
            return cam
        cam.release()
    return None


cam = open_camera()
if cam is None or not cam.isOpened():
    print("[Error] Camera not accessible. Checked indices 0-3.")
    sys.exit(1)

print(f"Face recognition running for Subject ID {subject_id}. Press Q to quit.")

while True:
    ret, frame = cam.read()
    if not ret:
        break

    small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb)
    face_encodings = face_recognition.face_encodings(rgb, face_locations)
    face_landmarks_list = face_recognition.face_landmarks(rgb, face_locations)

    for face_encoding, (top, right, bottom, left), landmarks in zip(
        face_encodings, face_locations, face_landmarks_list
    ):
        top *= 2
        right *= 2
        bottom *= 2
        left *= 2

        name = "Unknown"
        color = (0, 0, 220)
        status_text = "Scanning"

        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
        if len(face_distances) > 0:
            best_match_index = int(np.argmin(face_distances))
            distance_score = float(face_distances[best_match_index])

            if distance_score < 0.50:
                student_id = known_ids[best_match_index]

                # Anti-spoofing liveness check
                is_live, liveness_reason = liveness.update(
                    student_id, landmarks, (top, right, bottom, left)
                )

                cursor.execute("SELECT name FROM students WHERE id=%s", (student_id,))
                result = cursor.fetchone()

                if result:
                    name = result[0]
                    if is_live:
                        color = (40, 180, 40)
                        status_text = "Verified"

                        if student_id not in marked_students:
                            cursor.execute(
                                """
                                INSERT INTO attendance (student_id, date, subject_id, status, confidence)
                                VALUES (%s, %s, %s, 'Present', %s)
                                ON DUPLICATE KEY UPDATE status='Present', confidence=VALUES(confidence)
                            """,
                                (student_id, today, subject_id, distance_score),
                            )
                            conn.commit()
                            marked_students.add(student_id)
                            print(f"[Marked Present] {name} (confidence: {1-distance_score:.2f})")
                    else:
                        color = (0, 140, 255)
                        status_text = "Verifying Liveness"

        # Display bounding box and label
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.rectangle(frame, (left, bottom - 30), (right, bottom), color, cv2.FILLED)
        cv2.putText(
            frame,
            f"{name} ({status_text})",
            (left + 6, bottom - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
        )

    cv2.putText(
        frame,
        f"Marked Present: {len(marked_students)}",
        (16, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (255, 255, 255),
        2,
    )

    cv2.imshow("Attendance Camera - Press Q to stop", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cam.release()
cv2.destroyAllWindows()
cursor.close()
conn.close()
