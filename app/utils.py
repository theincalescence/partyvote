import os
import uuid
import logging
import qrcode
from functools import wraps
from flask import request, make_response, current_app
from PIL import Image, ImageOps
from app.db import get_db
from qrcode.constants import ERROR_CORRECT_L

logger = logging.getLogger(__name__)

def generate_qr_code(url):
    """Generate QR code from URL and save it as QR.png in data directory"""
    try:
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # Add data to QR code
        qr.add_data(url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save QR code image as QR.png (overwriting previous)
        qr_filename = "QR.png"
        qr_path = os.path.join(current_app.config['DATA_DIR'], qr_filename)
        img.save(qr_path)
        
        return qr_filename
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None

def get_current_qr_url():
    """Retrieve the currently set QR URL from database"""
    try:
        conn = get_db()
        row = conn.execute('SELECT qr_url FROM state LIMIT 1').fetchone()
        
        if row:
            return row['qr_url']
        else:
            return 'http://localhost:5000'
    except Exception as e:
        print(f"Error retrieving QR URL: {e}")
        return 'http://localhost:5000'

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

DEFAULT_BRANDING = {
    'event_year': '2026',
    'event_location': 'RouwenRick Manor',
    'event_title_line1': 'HALLOWEEN',
    'event_title_line2': 'PARTY'
}

def get_event_branding() -> dict:
    conn = get_db()
    rows = conn.execute(
        "SELECT key, value FROM state WHERE key IN ('event_year', 'event_location', 'event_title_line1', 'event_title_line2')"
    ).fetchall()
    
    branding = dict(DEFAULT_BRANDING)
    for r in rows:
        # If the key exists in DB (even as an empty string for line2), respect it
        if r['value'] is not None:
            branding[r['key']] = r['value']
    return branding

def set_event_branding(year: str, location: str, line1: str, line2: str = ""):
    conn = get_db()
    updates = [
        ('event_year', (year or '').strip()),
        ('event_location', (location or '').strip()),
        ('event_title_line1', (line1 or '').strip().upper()),
        ('event_title_line2', (line2 or '').strip().upper())
    ]
    for key, val in updates:
        conn.execute("""
            INSERT INTO state (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, val))
    conn.commit()