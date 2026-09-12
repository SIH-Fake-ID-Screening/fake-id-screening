import cv2
import insightface
import numpy as np


THRESHOLD = 0.40


class FaceVerifier:
    def __init__(self):
        self.app = insightface.app.FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"]
        )

        self.app.prepare(
            ctx_id=0,
            det_size=(640, 640)
        )

    def _get_embedding(self, image_path):
        image = cv2.imread(image_path)

        if image is None:
            raise FileNotFoundError(
                f"Could not load image: {image_path}"
            )

        faces = self.app.get(image)

        if len(faces) == 0:
            raise ValueError(
                f"No face detected in image: {image_path}"
            )

        if len(faces) > 1:
            raise ValueError(
                f"Multiple faces detected in image: {image_path}"
            )

        embedding = faces[0].embedding

        # Normalize the embedding
        embedding = embedding / np.linalg.norm(embedding)

        return embedding

    def verify_faces(self, document_image_path, live_image_path):
        document_embedding = self._get_embedding(
            document_image_path
        )

        live_embedding = self._get_embedding(
            live_image_path
        )

        similarity = float(
            np.dot(document_embedding, live_embedding)
        )

        match = similarity >= THRESHOLD

        return {
            "match": match,
            "confidence": similarity
        }