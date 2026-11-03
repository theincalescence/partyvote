import os
import uuid
import logging
from functools import wraps
from flask import request, make_response, current_app
from PIL import Image, ImageOps
from app.db import get_db

logger = logging.getLogger(__name__)

def are_submissions_open():
    conn = get_db()
    try:
        row = conn.execute("SELECT value FROM state WHERE key='submissions_open'").fetchone()
        return row[0] == 'true' if row else False
    except Exception as e:
        logger.error(f"Error checking submissions open status: {e}")
        return False

def is_voting_open():
    conn = get_db()
    try:
        row = conn.execute("SELECT value FROM state WHERE key='voting_open'").fetchone()
        return row[0] == 'true' if row else False
    except Exception as e:
        logger.error(f"Error checking voting open status: {e}")
        return False

def get_reveal_level(slug):
    conn = get_db()
    try:
        row = conn.execute("SELECT value FROM state WHERE key=?", (f"reveal_{slug}",)).fetchone()
        return int(row[0]) if row else 0
    except Exception as e:
        logger.error(f"Error getting reveal level for {slug}: {e}")
        return 0

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        user = current_app.config['ADMIN_USERNAME']
        pwd = current_app.config['ADMIN_PASSWORD']
        if not auth or not (auth.username == user and auth.password == pwd):
            logger.warning(f"Failed authentication attempt from {request.remote_addr}")
            return make_response('Could not verify!', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
        logger.info(f"Successful authentication for user {auth.username} from {request.remote_addr}")
        return f(*args, **kwargs)
    return decorated

def save_and_optimize_image(file_storage):
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    try:
        img = Image.open(file_storage)
        img = ImageOps.exif_transpose(img)
        img.thumbnail((800, 800))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(filepath, optimize=True, quality=85)
        logger.info(f"Successfully saved optimized image: {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error saving and optimizing image {filename}: {e}")
        raise

def rotate_entry_image(filename):
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if os.path.isfile(file_path):
        try:
            with Image.open(file_path) as im:
                rotated = im.rotate(270, expand=True)
                if rotated.mode in ("RGBA", "P"):
                    rotated = rotated.convert("RGB")
                rotated.save(file_path, quality=85, optimize=True)
                logger.info(f"Successfully rotated image: {filename}")
                return True
        except Exception as e:
            logger.error(f"Error rotating image {filename}: {e}")
            return False
    return False
