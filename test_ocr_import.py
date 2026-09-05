import json
from ai.ocr import extract_document


# Process both sides of the student ID card (img2: front, img: back with DOB)
result = extract_document(["img2.jpeg", "img.jpeg"])

print("\nOCR IMPORT TEST (FRONT + BACK)")
print(json.dumps(result, indent=2))

# Verify strict contract keys
expected_keys = {"student_id", "name", "dob", "course", "valid_till"}
assert set(result.keys()) == expected_keys, f"Expected keys {expected_keys}, got {set(result.keys())}"

# Check important fields from both sides of the real card
assert result["name"] == "PRIYANSHU RANJAN"
assert result["student_id"] == "202501100600212"
assert result["course"] == "B TECH IT"
assert result["valid_till"] == "2029-07-01"
assert result["dob"] == "2005-12-27"

print("\nOCR IMPORT TEST PASSED")