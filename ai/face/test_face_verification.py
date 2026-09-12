from face_verification import FaceVerifier


verifier = FaceVerifier()

result = verifier.verify_faces(
    "ai/face/person1.jpeg",
    "ai/face/person2.jpeg"
)

print("Face Verification Result:")
print(result)