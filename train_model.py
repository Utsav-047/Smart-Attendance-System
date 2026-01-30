import cv2
import numpy as np
import os

# ----------- FACE DETECTOR -----------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# ----------- DATASET PATH -----------
dataset_path = "face_dataset"

faces = []
labels = []

# ----------- READ DATASET -----------
for folder_name in os.listdir(dataset_path):
    folder_path = os.path.join(dataset_path, folder_name)

    if not os.path.isdir(folder_path):
        continue

    label = int(folder_name)  # student ID

    for image_name in os.listdir(folder_path):
        image_path = os.path.join(folder_path, image_name)

        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

        faces.append(img)
        labels.append(label)

print(f"Total faces: {len(faces)}")
print(f"Total labels: {len(labels)}")

# ----------- TRAIN MODEL -----------
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.train(faces, np.array(labels))

# ----------- SAVE MODEL -----------
recognizer.save("trainer.yml")

print(" Face recognition model trained and saved successfully!")
