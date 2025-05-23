from flask import Flask
from config import Config
# from flask_sqlalchemy import SQLAlchemy # Removed
# from flask_migrate import Migrate # Removed
from flask_cors import CORS
import os
import logging
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize extensions
# db = SQLAlchemy() # Removed
# migrate = Migrate() # Removed
firestore_db = None  # Firebase client


def create_app(config_class=Config):
    """Application Factory Pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure logging
    if not app.debug:
        # In production, you might want to log to a file
        logging.basicConfig(level=logging.INFO)
        app.logger.setLevel(logging.INFO)
    else:
        # In development, log more details
        logging.basicConfig(level=logging.DEBUG)
        app.logger.setLevel(logging.DEBUG)
        app.logger.info('FR Safe Kids startup')

    # Ensure instance folder exists (needed for SQLite DB file) # Removed
    # try: # Removed
    #     os.makedirs(app.instance_path) # Removed
    # except OSError: # Removed
    #     pass  # Already exists # Removed

    # Initialize Firebase Admin SDK
    global firestore_db
    if not firebase_admin._apps:  # Check if already initialized
        try:
            cred_path = app.config.get('FIREBASE_CREDENTIALS_PATH')
            # db_url = app.config.get('FIREBASE_DATABASE_URL') # Removed

            if not cred_path:
                app.logger.error(
                    "FIREBASE_CREDENTIALS_PATH not set in config.")
                raise ValueError("Firebase credentials path not set.")
            # if not db_url: # Removed
            #     app.logger.error("FIREBASE_DATABASE_URL not set in config.") # Removed
            #     raise ValueError("Firebase database URL not set.") # Removed

            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)  # Removed databaseURL option
            firestore_db = firestore.client()
            app.logger.info(
                "Firebase Admin SDK initialized successfully for Cloud Firestore.")
        except Exception as e:
            app.logger.error(
                f"Failed to initialize Firebase Admin SDK: {e}", exc_info=True)
            # Depending on the app's requirements, you might want to raise the exception
            # or handle it gracefully (e.g., run in a limited mode or exit).
            raise RuntimeError(f"Firebase initialization failed: {e}") from e
    else:
        # If already initialized (e.g., in a test setup or multiple create_app calls),
        # ensure firestore_db is set for the current context if needed,
        # though typically initialize_app is called once.
        if firestore_db is None:
            firestore_db = firestore.client()
        app.logger.info("Firebase Admin SDK already initialized.")

    # Initialize Flask extensions with the app # Removed
    # db.init_app(app) # Removed
    # migrate.init_app(app, db) # Removed

    # Configure CORS with settings from config
    cors_origins = app.config.get('CORS_ORIGINS', '*')
    # Handle comma-separated list of origins
    if isinstance(cors_origins, str) and cors_origins != '*':
        cors_origins = [origin.strip() for origin in cors_origins.split(',')]
        # Special handling for patterns with wildcards (like 192.168.0.*)
        import re
        for i, origin in enumerate(cors_origins[:]):
            if '*' in origin:
                # Convert wildcard pattern to regex pattern
                pattern = origin.replace('.', '\\.').replace('*', '.*')
                cors_origins[i] = re.compile(pattern)

    CORS(app, resources={r"/*": {"origins": cors_origins}},
         supports_credentials=True)
    app.logger.info(f"CORS enabled with origins: {cors_origins}")

    # Import and register routes (or blueprints)
    with app.app_context():  # Need app context for routes using current_app
        from . import routes
        # Import models here to ensure they are known to Flask-Migrate # Models will be different
        from app import models  # Models will be refactored for Firebase

    return app
