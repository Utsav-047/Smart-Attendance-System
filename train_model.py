# import cv2
# import numpy as np
# import os
# import mysql.connector

# DATASET_PATH = "face_dataset"

# conn = mysql.connector.connect(
#     host="localhost", user="root", password="", database="attendance_db"
# )
# cursor = conn.cursor()

# faces  = []
# labels = []

# for roll in os.listdir(DATASET_PATH):
#     folder = os.path.join(DATASET_PATH, roll)
#     if not os.path.isdir(folder):
#         continue

#     cursor.execute("SELECT id FROM students WHERE roll = %s", (roll,))
#     result = cursor.fetchone()
#     if result is None:
#         print(f"Roll {roll} not found in database - skipping")
#         continue

#     student_id = result[0]

#     for img_name in os.listdir(folder):
#         img_path = os.path.join(folder, img_name)
#         img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
#         if img is None:
#             continue
#         faces.append(img)
#         labels.append(student_id)

# cursor.close()
# conn.close()

# if not faces:
#     print("No face images found. Run capture_faces.py first.")
#     exit()

# print(f"Training on {len(faces)} images...")
# recognizer = cv2.face.LBPHFaceRecognizer_create()
# recognizer.train(faces, np.array(labels))
# recognizer.save("trainer.yml")
# print("Model trained and saved as trainer.yml")

import cv2
import numpy as np
import os
import mysql.connector

def train_model():

    DATASET_PATH = "face_dataset"

    conn = mysql.connector.connect(
        host="localhost", user="root", password="", database="attendance_db"
    )
    cursor = conn.cursor()

    faces = []
    labels = []

    for roll in os.listdir(DATASET_PATH):
        folder = os.path.join(DATASET_PATH, roll)

        if not os.path.isdir(folder):
            continue

        cursor.execute("SELECT id FROM students WHERE roll = %s", (roll,))
        result = cursor.fetchone()

        if result is None:
            continue

        student_id = result[0]

        for img_name in os.listdir(folder):
            img_path = os.path.join(folder, img_name)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

            if img is None:
                continue

            faces.append(img)
            labels.append(student_id)

    cursor.close()
    conn.close()

    if not faces:
        return

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))
    recognizer.save("trainer.yml")
