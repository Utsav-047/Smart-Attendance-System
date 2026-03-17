import cv2
import os
import mysql.connector

roll = input("Enter Student Roll Number (e.g. 24AIML047): ").strip()

conn = mysql.connector.connect(
    host="localhost", user="root", password="", database="attendance_db"
)
cursor = conn.cursor()
cursor.execute("SELECT id, name FROM students WHERE roll = %s", (roll,))
result = cursor.fetchone()
cursor.close()
conn.close()

if result is None:
    print(f"Roll '{roll}' not found. Please register the student via the website first.")
    exit()

print(f"Student found: {result[1]}  (ID: {result[0]})")

dataset_path = f"face_dataset/{roll}"
os.makedirs(dataset_path, exist_ok=True)

cam          = cv2.VideoCapture(0)
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

count = 0
print("Capturing 20 face images. Press Q to stop early.")

while True:
    ret, frame = cam.read()
    if not ret:
        break

    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        count += 1
        face_img = gray[y:y+h, x:x+w]
        cv2.imwrite(f"{dataset_path}/img{count}.jpg", face_img)
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

    cv2.putText(frame, f"Captured: {count}/20", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.imshow("Capture Faces - Press Q to stop", frame)

    if cv2.waitKey(1) & 0xFF == ord('q') or count >= 20:
        break

cam.release()
cv2.destroyAllWindows()
print(f"{count} face images saved. Now run train_model.py")
