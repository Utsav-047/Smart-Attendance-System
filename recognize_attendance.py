import cv2
import mysql.connector
from datetime import date

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("trainer.yml")

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

conn = mysql.connector.connect(
    host="localhost", user="root", password="", database="attendance_db"
)
cursor = conn.cursor()

today           = str(date.today())
marked_students = set()

cam = cv2.VideoCapture(0)
print("Face Recognition started. Press Q to stop.")

while True:
    ret, frame = cam.read()
    if not ret:
        break

    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)

    for (x, y, w, h) in faces:
        if w < 120 or h < 120: # //changes from 100 to 150
            continue

        face_img   = gray[y:y+h, x:x+w]
        student_id, confidence = recognizer.predict(face_img)

        if confidence < 35: # //changes from 45 to 35 for better accuracy
            cursor.execute("SELECT name FROM students WHERE id = %s", (student_id,))
            result = cursor.fetchone()

            if result:
                name = result[0]
                if student_id not in marked_students:
                    try:
                        cursor.execute(
                            "INSERT INTO attendance (student_id, date, status) VALUES (%s, %s, 'Present')",
                            (student_id, today)
                        )
                        conn.commit()
                        marked_students.add(student_id)
                        print(f"Marked Present: {name}")
                    except mysql.connector.IntegrityError:
                        marked_students.add(student_id)
            else:
                name = "Unknown"
        else:
            name = "Unknown"

        color = (0, 200, 0) if name != "Unknown" else (0, 0, 220)
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        cv2.putText(frame, name, (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

    cv2.putText(frame, f"Marked: {len(marked_students)}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    cv2.imshow("Smart Attendance - Press Q to stop", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cursor.close()
conn.close()
cv2.destroyAllWindows()
print(f"Session ended. Total marked: {len(marked_students)}")
