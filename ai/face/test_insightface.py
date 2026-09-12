import cv2
import insightface
import numpy as np


# -----------------------------
# 1. Load InsightFace
# -----------------------------

print("Loading InsightFace...")

app = insightface.app.FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

print("Model loaded!")


# -----------------------------
# 2. Load images
# -----------------------------

img1 = cv2.imread("ai/face/person10.jpeg")
img2 = cv2.imread("ai/face/person11.jpeg")

if img1 is None:
    raise FileNotFoundError("Could not load person1.jpg")

if img2 is None:
    raise FileNotFoundError("Could not load person2.jpg")


# -----------------------------
# 3. Detect faces
# -----------------------------

faces1 = app.get(img1)
faces2 = app.get(img2)

print("Faces in image 1:", len(faces1))
print("Faces in image 2:", len(faces2))


if len(faces1) == 0:
    raise ValueError("No face detected in person1.jpg")

if len(faces2) == 0:
    raise ValueError("No face detected in person2.jpg")


# -----------------------------
# 4. Get face embeddings
# -----------------------------

embedding1 = faces1[0].embedding
embedding2 = faces2[0].embedding

print("Embedding 1 shape:", embedding1.shape)
print("Embedding 2 shape:", embedding2.shape)


# -----------------------------
# 5. Normalize embeddings
# -----------------------------

embedding1 = embedding1 / np.linalg.norm(embedding1)
embedding2 = embedding2 / np.linalg.norm(embedding2)


# -----------------------------
# 6. Calculate cosine similarity
# -----------------------------

similarity = np.dot(embedding1, embedding2)

print("Cosine similarity:", similarity)