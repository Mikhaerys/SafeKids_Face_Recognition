import os
from dotenv import load_dotenv

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    # Secret key - strong recommend to set in environment variable for production
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)

    # SQLite database path
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # CORS settings - restrict in production
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')

    # Upload folders configuration
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    REFERENCE_FOLDER = os.path.join(UPLOAD_FOLDER, 'reference')
    VERIFIED_FOLDER = os.path.join(UPLOAD_FOLDER, 'verified')

    # Ensure upload folders exist when config is loaded
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(REFERENCE_FOLDER, exist_ok=True)
    os.makedirs(VERIFIED_FOLDER, exist_ok=True)

    # Face recognition settings
    FACE_RECOGNITION_TOLERANCE = 0.6  # Lower is stricter
    FACE_RECOGNITION_MODEL = 'hog'    # 'hog' (faster) or 'cnn' (more accurate)
