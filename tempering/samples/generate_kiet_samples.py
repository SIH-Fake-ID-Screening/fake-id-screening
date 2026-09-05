"""
Generate the KIET-card tampering evaluation dataset from the canonical
genuine reference standard.

Genuine re-capture variants (exposure, perspective) are written into
samples/genuine/ without ground truth; tampered variants are written into
samples/tampered_kiet_card/ with a binary ground-truth mask (<stem>_gt.png)
covering the manipulated pixels.

Usage (from the repository root):
    PYTHONPATH=modules/tampering python modules/tampering/samples/generate_kiet_samples.py
"""
import os
import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))          # modules/tampering/samples
MODULE_DIR = os.path.dirname(BASE_DIR)                          # modules/tampering
GENUINE_DIR = os.path.join(BASE_DIR, "genuine")
TAMPERED_DIR = os.path.join(BASE_DIR, "tampered_kiet_card")

FRONT_PATH = os.path.join(MODULE_DIR, "reference", "kiet_id_front.png")
BACK_PATH = os.path.join(MODULE_DIR, "reference", "kiet_id_back.jpg")

# Card layout fractions (must match forensic/reference_matching.py zones)
PHOTO_BOX = (0.27, 0.225, 0.37, 0.26)
NAME_LINE = (0.15, 0.505, 0.70, 0.045)
QR_BOX = (0.115, 0.725, 0.26, 0.17)
SIGNATURE_BOX = (0.63, 0.69, 0.24, 0.14)
DOB_LINE = (0.30, 0.045, 0.40, 0.045)


def _zone(img, box):
    h, w = img.shape[:2]
    fx, fy, fw, fh = box
    return int(fx * w), int(fy * h), int(fw * w), int(fh * h)


def genuine_exposure_variants(front):
    return {
        "kiet_genuine_exposure": cv2.convertScaleAbs(front, alpha=1.12, beta=8),
        "kiet_genuine_dim": cv2.convertScaleAbs(front, alpha=0.88, beta=-6),
    }


def genuine_perspective_variant(front, rng):
    h, w = front.shape[:2]
    src = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
    dst = np.float32([
        [w * 0.020, h * 0.010], [w * 0.985, h * 0.025],
        [w * 0.980, h * 0.985], [w * 0.015, h * 0.970],
    ])
    warped = cv2.warpPerspective(front, cv2.getPerspectiveTransform(src, dst), (w, h))
    return {"kiet_genuine_perspective": warped}


def tamper_photo(front):
    """Re-printed photo: blurred, re-toned region pasted over the portrait."""
    out = front.copy()
    mask = np.zeros(front.shape[:2], np.uint8)
    x, y, w, h = _zone(front, PHOTO_BOX)
    region = out[y:y + h, x:x + w]
    region = cv2.convertScaleAbs(cv2.GaussianBlur(region, (9, 9), 0), alpha=1.18, beta=14)
    out[y:y + h, x:x + w] = region
    mask[y:y + h, x:x + w] = 255
    return out, mask


def tamper_name(front):
    """Name rewritten: original line erased, new name printed."""
    out = front.copy()
    mask = np.zeros(front.shape[:2], np.uint8)
    x, y, w, h = _zone(front, NAME_LINE)
    out[y:y + h, x:x + w] = np.full((h, w, 3), 205, np.uint8)
    cv2.putText(out, "RAHUL KUMAR VERMA", (x, y + h - 6),
                cv2.FONT_HERSHEY_DUPLEX, 1.1, (30, 30, 30), 2)
    mask[y:y + h, x:x + w] = 255
    return out, mask


def tamper_qr(front):
    """QR code replaced with a counterfeit block pattern."""
    out = front.copy()
    mask = np.zeros(front.shape[:2], np.uint8)
    x, y, w, h = _zone(front, QR_BOX)
    rng = np.random.default_rng(7)
    blocks = (rng.random((20, 14)) > 0.5).astype(np.uint8) * 40
    out[y:y + h, x:x + w] = cv2.resize(
        cv2.merge([blocks * 3, blocks * 3, blocks * 3]), (w, h),
        interpolation=cv2.INTER_NEAREST)
    mask[y:y + h, x:x + w] = 255
    return out, mask


def tamper_signature(front):
    """Original signature erased and replaced with a forged scribble."""
    out = front.copy()
    mask = np.zeros(front.shape[:2], np.uint8)
    x, y, w, h = _zone(front, SIGNATURE_BOX)
    out[y:y + h, x:x + w] = np.full((h, w, 3), 208, np.uint8)
    pts = np.array([[x + 8, y + h - 10], [x + w * 0.3, y + 10], [x + w * 0.5, y + h - 14],
                    [x + w * 0.7, y + 18], [x + w - 6, y + h - 20]], np.int32)
    cv2.polylines(out, [pts], False, (40, 40, 40), 3)
    mask[y:y + h, x:x + w] = 255
    return out, mask


def tamper_dob(back):
    """Back side: date of birth digits altered."""
    out = back.copy()
    mask = np.zeros(back.shape[:2], np.uint8)
    x, y, w, h = _zone(back, DOB_LINE)
    out[y:y + h, x:x + w] = np.full((h, w, 3), 210, np.uint8)
    cv2.putText(out, "27/12/2009", (x, y + h - 6),
                cv2.FONT_HERSHEY_DUPLEX, 1.0, (30, 30, 30), 2)
    mask[y:y + h, x:x + w] = 255
    return out, mask


def main():
    front = cv2.imread(FRONT_PATH)
    back = cv2.imread(BACK_PATH)
    if front is None or back is None:
        raise SystemExit("Canonical genuine reference images not found.")

    os.makedirs(GENUINE_DIR, exist_ok=True)
    os.makedirs(TAMPERED_DIR, exist_ok=True)
    rng = np.random.default_rng(42)

    for stem, img in {**genuine_exposure_variants(front),
                      **genuine_perspective_variant(front, rng)}.items():
        path = os.path.join(GENUINE_DIR, f"{stem}.png")
        cv2.imwrite(path, img)
        print(f"genuine  -> {os.path.relpath(path, BASE_DIR)}")

    tampers = [
        ("kiet_tamper_photo", tamper_photo(front)),
        ("kiet_tamper_name", tamper_name(front)),
        ("kiet_tamper_qr", tamper_qr(front)),
        ("kiet_tamper_signature", tamper_signature(front)),
        ("kiet_tamper_dob_back", tamper_dob(back)),
    ]
    for stem, (img, mask) in tampers:
        img_path = os.path.join(TAMPERED_DIR, f"{stem}.png")
        gt_path = os.path.join(TAMPERED_DIR, f"{stem}_gt.png")
        cv2.imwrite(img_path, img)
        cv2.imwrite(gt_path, mask)
        print(f"tampered -> {os.path.relpath(img_path, BASE_DIR)} (+ gt mask)")

    print("\nKIET-card evaluation dataset generated.")


if __name__ == "__main__":
    main()
