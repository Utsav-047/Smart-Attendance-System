import cv2
import numpy as np
import os
import sqlite3

DATASET_PATH = "face_dataset"

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

faces = []
labels = []

for roll in os.listdir(DATASET_PATH):
    folder = os.path.join(DATASET_PATH, roll)
    if not os.path.isdir(folder):
        continue

    cursor.execute("SELECT id FROM students WHERE roll = ?", (roll,))
    result = cursor.fetchone()
    if result is None:
        print(f"⚠ Roll {roll} not found in database")
        continue

    student_id = result[0]

    for img_name in os.listdir(folder):
        img_path = os.path.join(folder, img_name)
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

        faces.append(img)
        labels.append(student_id)

conn.close()

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.train(faces, np.array(labels))
recognizer.save("trainer.yml")

print(" Model trained using roll-number folders")
