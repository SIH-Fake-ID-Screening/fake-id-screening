import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def create_base_document(width=800, height=500, id_str="IND-8942-001", name="AARAV SHARMA", dob="15/08/1990") -> np.ndarray:
    """Create a pristine synthetic identity card image."""
    img = np.full((height, width, 3), 245, dtype=np.uint8)

    # Header bar
    cv2.rectangle(img, (0, 0), (width, 70), (120, 50, 20), -1)
    cv2.putText(img, "GOVERNMENT OF INDIA - OFFICIAL IDENTITY CARD", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # Face photo container
    cv2.rectangle(img, (40, 100), (200, 320), (200, 200, 200), -1)
    cv2.rectangle(img, (40, 100), (200, 320), (100, 100, 100), 2)
    # Synthetic face (gradient circle + body)
    cv2.circle(img, (120, 170), 40, (140, 100, 80), -1)
    cv2.ellipse(img, (120, 270), (60, 40), 0, 180, 360, (60, 60, 120), -1)

    # Text metadata fields
    cv2.putText(img, "NAME:", (240, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
    cv2.putText(img, name, (240, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)

    cv2.putText(img, "DOB:", (240, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
    cv2.putText(img, dob, (240, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)

    cv2.putText(img, "DOCUMENT ID:", (240, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
    cv2.putText(img, id_str, (240, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (20, 20, 20), 2)

    # Official Stamp Seal (Blue double circle)
    cv2.circle(img, (680, 380), 65, (180, 50, 30), 3)
    cv2.circle(img, (680, 380), 55, (180, 50, 30), 1)
    cv2.putText(img, "VERIFIED", (642, 385), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 50, 30), 2)

    # Footer bar
    cv2.rectangle(img, (0, height - 40), (width, height), (220, 220, 220), -1)
    cv2.putText(img, "CONFIDENTIAL DOCUMENT - FOR INTERNAL USE ONLY", (180, height - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 80, 80), 1)

    return img


def generate_all_samples(base_dir="modules/tampering/samples"):
    categories = ["genuine", "tampered_text", "tampered_photo", "tampered_stamp", "tampered_mixed"]
    for cat in categories:
        os.makedirs(os.path.join(base_dir, cat), exist_ok=True)

    # 1. Genuine Sample
    genuine_doc = create_base_document()
    genuine_path = os.path.join(base_dir, "genuine", "doc_01.png")
    gt_genuine_path = os.path.join(base_dir, "genuine", "doc_01_gt.png")
    cv2.imwrite(genuine_path, genuine_doc)
    cv2.imwrite(gt_genuine_path, np.zeros((500, 800), dtype=np.uint8))

    # 2. Tampered Text Sample
    text_doc = create_base_document()
    gt_text = np.zeros((500, 800), dtype=np.uint8)
    # Tamper ID number region (240, 275) -> (500, 315)
    cv2.rectangle(text_doc, (380, 275), (600, 315), (245, 245, 245), -1)
    # Apply synthetic noise/font discrepancy in tampered text
    cv2.putText(text_doc, "MOD-9999-XXX", (385, 305), cv2.FONT_HERSHEY_TRIPLEX, 0.75, (0, 0, 150), 2)
    gt_text[275:315, 380:600] = 255
    cv2.imwrite(os.path.join(base_dir, "tampered_text", "text_01.png"), text_doc)
    cv2.imwrite(os.path.join(base_dir, "tampered_text", "text_01_gt.png"), gt_text)

    # 3. Tampered Photo Sample
    photo_doc = create_base_document()
    gt_photo = np.zeros((500, 800), dtype=np.uint8)
    # Replace photo area (40, 100) -> (200, 320) with alternate noise/color face
    photo_region = photo_doc[100:320, 40:200].copy()
    # Apply heavy noise and color shift to simulate spliced external photo
    noise = np.random.randint(-40, 40, photo_region.shape, dtype=np.int16)
    spliced_photo = np.clip(photo_region.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    photo_doc[100:320, 40:200] = spliced_photo
    gt_photo[100:320, 40:200] = 255
    cv2.imwrite(os.path.join(base_dir, "tampered_photo", "photo_01.png"), photo_doc)
    cv2.imwrite(os.path.join(base_dir, "tampered_photo", "photo_01_gt.png"), gt_photo)

    # 4. Tampered Stamp Sample (Copy-Move duplication)
    stamp_doc = create_base_document()
    gt_stamp = np.zeros((500, 800), dtype=np.uint8)
    # Copy stamp from (680, 380) area and paste in top right (680, 140)
    stamp_crop = stamp_doc[310:450, 610:750].copy()
    stamp_doc[100:240, 610:750] = stamp_crop
    gt_stamp[100:240, 610:750] = 255
    cv2.imwrite(os.path.join(base_dir, "tampered_stamp", "stamp_01.png"), stamp_doc)
    cv2.imwrite(os.path.join(base_dir, "tampered_stamp", "stamp_01_gt.png"), gt_stamp)

    # 5. Tampered Mixed Sample (Photo + Text edit)
    mixed_doc = create_base_document()
    gt_mixed = np.zeros((500, 800), dtype=np.uint8)

    # Photo edit
    photo_region = mixed_doc[100:320, 40:200].copy()
    noise = np.random.randint(-35, 35, photo_region.shape, dtype=np.int16)
    mixed_doc[100:320, 40:200] = np.clip(photo_region.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    gt_mixed[100:320, 40:200] = 255

    # Name text edit
    cv2.rectangle(mixed_doc, (240, 135), (550, 170), (245, 245, 245), -1)
    cv2.putText(mixed_doc, "VIKRAM RATHORE", (245, 162), cv2.FONT_HERSHEY_COMPLEX, 0.75, (180, 0, 0), 2)
    gt_mixed[135:170, 240:550] = 255

    cv2.imwrite(os.path.join(base_dir, "tampered_mixed", "mixed_01.png"), mixed_doc)
    cv2.imwrite(os.path.join(base_dir, "tampered_mixed", "mixed_01_gt.png"), gt_mixed)

    print("Synthetic dataset successfully generated in 'modules/tampering/samples/'.")


if __name__ == "__main__":
    generate_all_samples()
