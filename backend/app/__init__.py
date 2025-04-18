from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import os
import logging

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()


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

    # Ensure instance folder exists (needed for SQLite DB file)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass  # Already exists

    # Initialize Flask extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)

    # Configure CORS with settings from config
    cors_origins = app.config.get('CORS_ORIGINS', '*')
    CORS(app, resources={r"/*": {"origins": cors_origins}})
    app.logger.info(f"CORS enabled with origins: {cors_origins}")

    # Import and register routes (or blueprints)
    with app.app_context():  # Need app context for routes using current_app
        from . import routes
        # Import models here to ensure they are known to Flask-Migrate
        from app import models

    return app
