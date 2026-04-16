
import cv2
import os

def capture_faces(roll):

    dataset_path = f"face_dataset/{roll}"
    os.makedirs(dataset_path, exist_ok=True)

    cam = cv2.VideoCapture(0)

    # 🔥 FIX HERE
    if not cam.isOpened():
        raise Exception("Camera not accessible")   # ✅ CHANGE

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    count = 0

    print(f"📸 Starting capture for {roll}...")

    while True:
        ret, frame = cam.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            count += 1
            face_img = gray[y:y+h, x:x+w]

            cv2.imwrite(f"{dataset_path}/img{count}.jpg", face_img)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

        cv2.putText(frame, f"Captured: {count}/20", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.imshow("📸 Capture Face - Press Q to stop", frame)

        if cv2.waitKey(1) & 0xFF == ord('q') or count >= 20:
            break

    cam.release()
    cv2.destroyAllWindows()

    print("✅ Face capture completed!")
