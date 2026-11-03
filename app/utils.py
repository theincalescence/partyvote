import os
import uuid
from functools import wraps
from flask import request, make_response, current_app
from PIL import Image, ImageOps
from app.db import get_db

def are_submissions_open():
    conn = get_db()
    row = conn.execute("SELECT value FROM state WHERE key='submissions_open'").fetchone()
    return row[0] == 'true' if row else False

def is_voting_open():
    conn = get_db()
    row = conn.execute("SELECT value FROM state WHERE key='voting_open'").fetchone()
    return row[0] == 'true' if row else False

def get_reveal_level(slug):
    conn = get_db()
    row = conn.execute("SELECT value FROM state WHERE key=?", (f"reveal_{slug}",)).fetchone()
    return int(row[0]) if row else 0

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        user = current_app.config['ADMIN_USERNAME']
        pwd = current_app.config['ADMIN_PASSWORD']
        if not auth or not (auth.username == user and auth.password == pwd):
            return make_response('Could not verify!', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated

def save_and_optimize_image(file_storage):
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    img = Image.open(file_storage)
    img = ImageOps.exif_transpose(img)
    img.thumbnail((800, 800))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(filepath, optimize=True, quality=85)
    return filename

def rotate_entry_image(filename):
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if os.path.isfile(file_path):
        try:
            with Image.open(file_path) as im:
                rotated = im.rotate(270, expand=True)
                if rotated.mode in ("RGBA", "P"):
                    rotated = rotated.convert("RGB")
                rotated.save(file_path, quality=85, optimize=True)
                return True
        except Exception:
            return False
    return False