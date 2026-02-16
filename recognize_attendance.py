# import cv2
# import sqlite3
# from datetime import date

# # ---------------- LOAD TRAINED MODEL ----------------
# recognizer = cv2.face.LBPHFaceRecognizer_create()
# recognizer.read("trainer.yml")

# # ---------------- FACE DETECTOR ----------------
# face_cascade = cv2.CascadeClassifier(
#     cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
# )

# # ---------------- DATABASE ----------------
# conn = sqlite3.connect("database.db")
# cursor = conn.cursor()

# today = str(date.today())
# marked_students = set()

# # ---------------- CAMERA ----------------
# cam = cv2.VideoCapture(0)

# print("Press 'q' to stop attendance")

# while True:
#     ret, frame = cam.read()
#     if not ret:
#         break

#     gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#     faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)

#     for (x, y, w, h) in faces:

#         # -------- IGNORE SMALL / PARTIAL FACES --------
#         if w < 100 or h < 100:
#             continue

#         face_img = gray[y:y+h, x:x+w]

#         student_id, confidence = recognizer.predict(face_img)

#         # -------- STRICT CONFIDENCE CHECK --------
#         # Lower confidence = better match
#         if confidence < 45:
#             cursor.execute(
#                 "SELECT name FROM students WHERE id = ?",
#                 (student_id,)
#             )
#             result = cursor.fetchone()

#             if result:
#                 name = result[0]

#                 # -------- MARK ATTENDANCE ONLY ONCE --------
#                 if student_id not in marked_students:
#                     cursor.execute(
#                         "INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
#                         (student_id, today, "Present")
#                     )
#                     conn.commit()
#                     marked_students.add(student_id)
#             else:
#                 name = "Unknown"
#         else:
#             name = "Unknown"

#         # -------- DRAW BOX & NAME --------
#         color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)

#         cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
#         cv2.putText(
#             frame,
#             name,
#             (x, y-10),
#             cv2.FONT_HERSHEY_SIMPLEX,
#             0.9,
#             color,
#             2
#         )

#     cv2.imshow("Smart Attendance System", frame)

#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break

# # ---------------- CLEANUP ----------------
# cam.release()
# conn.close()
# cv2.destroyAllWindows()


# print("Attendance session ended successfully")


# import cv2
# import sqlite3
# from datetime import date

# # ---------------- LOAD TRAINED MODEL ----------------
# recognizer = cv2.face.LBPHFaceRecognizer_create()
# recognizer.read("trainer.yml")

# # ---------------- FACE DETECTOR ----------------
# face_cascade = cv2.CascadeClassifier(
#     cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
# )

# # ---------------- DATABASE CONNECTION ----------------
# conn = sqlite3.connect("database.db")
# cursor = conn.cursor()

# today = str(date.today())
# marked_students = set()

# cam = cv2.VideoCapture(0)

# print("Press 'q' to stop attendance")

# while True:
#     ret, frame = cam.read()
#     if not ret:
#         break

#     gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#     faces = face_cascade.detectMultiScale(gray, 1.3, 5)

#     for (x, y, w, h) in faces:
#         face_img = gray[y:y+h, x:x+w]

#         student_id, confidence = recognizer.predict(face_img)

#         # -------- CONFIDENCE CHECK --------
#         if confidence < 70:
#             # -------- GET STUDENT NAME SAFELY --------
#             cursor.execute(
#                 "SELECT name FROM students WHERE id = ?",
#                 (student_id,)
#             )
#             result = cursor.fetchone()

#             if result:
#                 name = result[0]

#                 # -------- MARK ATTENDANCE ONCE --------
#                 if student_id not in marked_students:
#                     cursor.execute(
#                         "INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
#                         (student_id, today, "Present")
#                     )
#                     conn.commit()
#                     marked_students.add(student_id)
#             else:
#                 name = "Unknown"
#         else:
#             name = "Unknown"

#         # -------- DRAW ON FRAME --------
#         cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
#         cv2.putText(
#             frame,
#             name,
#             (x, y-10),
#             cv2.FONT_HERSHEY_SIMPLEX,
#             0.9,
#             (0, 255, 0),
#             2
#         )

#     cv2.imshow("Smart Attendance System", frame)

#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break

# # ---------------- CLEANUP ----------------
# cam.release()
# conn.close()
# cv2.destroyAllWindows()

# print(" Attendance session ended successfully")


import cv2
import sqlite3
from datetime import date

# ---------------- LOAD TRAINED MODEL ----------------
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("trainer.yml")

# ---------------- FACE DETECTOR ----------------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# ---------------- DATABASE ----------------
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

today = str(date.today())
marked_students = set()

# ---------------- CAMERA ----------------
cam = cv2.VideoCapture(0)

print("Press 'q' to stop attendance")

while True:
    ret, frame = cam.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)

    for (x, y, w, h) in faces:

        # -------- IGNORE SMALL / PARTIAL FACES --------
        if w < 100 or h < 100:
            continue

        face_img = gray[y:y+h, x:x+w]

        student_id, confidence = recognizer.predict(face_img)

        # -------- STRICT CONFIDENCE CHECK --------
        # Lower confidence = better match
        if confidence < 45:
            cursor.execute(
                "SELECT name FROM students WHERE id = ?",
                (student_id,)
            )
            result = cursor.fetchone()

            if result:
                name = result[0]

                # -------- MARK ATTENDANCE ONLY ONCE --------
                if student_id not in marked_students:
                    cursor.execute(
                        "INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                        (student_id, today, "Present")
                    )
                    conn.commit()
                    marked_students.add(student_id)
            else:
                name = "Unknown"
        else:
            name = "Unknown"

        # -------- DRAW BOX & NAME --------
        color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)

        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        cv2.putText(
            frame,
            name,
            (x, y-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            2
        )

    cv2.imshow("Smart Attendance System", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ---------------- CLEANUP ----------------
cam.release()
conn.close()
cv2.destroyAllWindows()

print("Attendance session ended successfully")
