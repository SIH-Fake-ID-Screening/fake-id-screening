import requests
import io
from PIL import Image

BASE = 'http://127.0.0.1:8000'

def make_jpeg_bytes():
    buf = io.BytesIO()
    img = Image.new('RGB', (100, 100), color=(100, 149, 237))
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf.read()

doc_front_bytes = make_jpeg_bytes()
doc_back_bytes = make_jpeg_bytes()
live_bytes = make_jpeg_bytes()
empty_bytes = b""
invalid_bytes = b"not an image"

print("Test 1: Valid front + back + live")
r = requests.post(
    f'{BASE}/api/v1/screen',
    files={
        'document_front': ('front.jpg', doc_front_bytes, 'image/jpeg'),
        'document_back': ('back.jpg', doc_back_bytes, 'image/jpeg'),
        'live_photo': ('live.jpg',  live_bytes, 'image/jpeg'),
    }
)
print("Status Code:", r.status_code)
print("Response:", r.json())
print("-" * 50)

print("Test 2: Invalid file content")
r2 = requests.post(
    f'{BASE}/api/v1/screen',
    files={
        'document_front': ('front.jpg', invalid_bytes, 'image/jpeg'),
        'document_back': ('back.jpg', doc_back_bytes, 'image/jpeg'),
        'live_photo': ('live.jpg',  live_bytes, 'image/jpeg'),
    }
)
print("Status Code:", r2.status_code)
print("Response:", r2.json())
print("-" * 50)

print("Test 3: Empty file")
r3 = requests.post(
    f'{BASE}/api/v1/screen',
    files={
        'document_front': ('front.jpg', doc_front_bytes, 'image/jpeg'),
        'document_back': ('back.jpg', doc_back_bytes, 'image/jpeg'),
        'live_photo': ('live.jpg',  empty_bytes, 'image/jpeg'),
    }
)
print("Status Code:", r3.status_code)
print("Response:", r3.json())
print("-" * 50)

print("Tests completed.")
