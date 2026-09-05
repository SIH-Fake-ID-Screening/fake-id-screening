# from ai.ocr import extract_document

# print("\n========== FRONT SIDE ==========")

# front = extract_document("img2.jpeg")

# print("Name:", front["fields"]["name"])
# print("Student ID:", front["fields"]["student_id"])
# print("College:", front["fields"]["college"])
# print("Course:", front["fields"]["course"])
# print("Valid Till:", front["fields"]["valid_till"])
# print("DOB:", front["fields"]["dob"])


# print("\n========== BACK SIDE ==========")

# back = extract_document("img.jpeg")

# print("Name:", back["fields"]["name"])
# print("Student ID:", back["fields"]["student_id"])
# print("College:", back["fields"]["college"])
# print("Course:", back["fields"]["course"])
# print("Valid Till:", back["fields"]["valid_till"])
# print("DOB:", back["fields"]["dob"])

import json
from ai.ocr import extract_document

print("\n========== FRONT SIDE ==========")
front = extract_document("img2.jpeg")
print(json.dumps(front, indent=2))

print("\n========== BACK SIDE ==========")
back = extract_document("img.jpeg")
print(json.dumps(back, indent=2))