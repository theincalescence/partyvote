import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    DATA_DIR = os.environ.get('DATA_DIR', os.path.join(BASE_DIR, 'data'))
    UPLOAD_FOLDER = os.path.join(DATA_DIR, 'uploads')
    DB_PATH = os.path.join(DATA_DIR, 'party.db')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'party-vote-insecure-secret-key')
    
    # Basic Auth credentials
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'partytime')
    
    CATEGORIES = {
        "individual": "Best Individual Costume",
        "couples": "Best Couples Costume",
        "pumpkins": "Best Jack-O-Lantern"
    }