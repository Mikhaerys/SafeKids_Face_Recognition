import os
from dotenv import load_dotenv

# Load environment variables from .env file (optional, for sensitive config)
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    SECRET_KEY = os.environ.get(
        'SECRET_KEY') or 'a-hard-to-guess-string'  # Change in production!
    # Use SQLite for simplicity
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Define upload folders relative to the backend base directory
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    REFERENCE_FOLDER = os.path.join(UPLOAD_FOLDER, 'reference')
    VERIFIED_FOLDER = os.path.join(UPLOAD_FOLDER, 'verified')

    # Ensure upload folders exist when config is loaded
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(REFERENCE_FOLDER, exist_ok=True)
    os.makedirs(VERIFIED_FOLDER, exist_ok=True)
