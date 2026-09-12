from ai.ocr.field_extractor import FieldExtractor
from ai.ocr.schemas import BoundingBox


def make_box(text, confidence=0.99, x=0, y=0):
    return BoundingBox(
        text=text,
        confidence=confidence,
        box=[
            [x, y],
            [x + 200, y],
            [x + 200, y + 30],
            [x, y + 30],
        ],
    )


def test_student_card():

    boxes = [
        make_box("NAME", y=0),
        make_box("RAHUL KUMAR", x=250, y=0),

        make_box("STUDENT ID", y=50),
        make_box("STU2025001", x=250, y=50),

        make_box("DOB", y=100),
        make_box("15/08/2004", x=250, y=100),

        make_box("COLLEGE", y=150),
        make_box("ABC UNIVERSITY", x=250, y=150),

        make_box("COURSE", y=200),
        make_box("BTECH CSE", x=250, y=200),

        make_box("VALID TILL", y=250),
        make_box("31/07/2028", x=250, y=250),
    ]

    extractor = FieldExtractor()

    fields, scores = extractor.extract_fields(
        boxes,
        "\n".join(box.text for box in boxes),
    )

    print("\nExtracted:")

    print("student_id:", fields.student_id)
    print("name:", fields.name)
    print("dob:", fields.dob)
    print("college:", fields.college)
    print("course:", fields.course)
    print("valid_till:", fields.valid_till)
    print("document_number:", fields.document_number)
    print("nationality:", fields.nationality)
    print("passport_number:", fields.passport_number)
    print("expiry_date:", fields.expiry_date)
    print("visa_info:", fields.visa_info)

    assert fields.student_id == "STU2025001"
    assert fields.name == "RAHUL KUMAR"
    assert fields.dob == "2004-08-15"
    assert fields.college == "ABC UNIVERSITY"
    assert fields.course == "BTECH CSE"

    assert fields.valid_till == "2028-07-31"
    assert fields.expiry_date == "2028-07-31"

    assert fields.document_number == "STU2025001"

    print("\nSTUDENT CARD TEST PASSED")


def test_dob_does_not_become_expiry():

    boxes = [
        make_box("D.O.B.", y=0),
        make_box("27/12/2005", x=250, y=0),

        make_box("Blood Group", y=50),

        make_box("Mob. No.", y=100),
        make_box("8789427924", x=250, y=100),

        make_box("Address", y=150),
        make_box("841211", y=200),
    ]

    extractor = FieldExtractor()

    fields, scores = extractor.extract_fields(
        boxes,
        "\n".join(box.text for box in boxes),
    )

    assert fields.dob == "2005-12-27"

    assert fields.valid_till is None
    assert fields.expiry_date is None

    assert fields.student_id is None
    assert fields.name is None

    print("FALSE-POSITIVE TEST PASSED")


if __name__ == "__main__":

    test_student_card()
    test_dob_does_not_become_expiry()

    print("\nALL FIELD EXTRACTION TESTS PASSED")