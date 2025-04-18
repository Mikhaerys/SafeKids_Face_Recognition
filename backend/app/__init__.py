from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS  # Import CORS
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()  # Initialize CORS


def create_app(config_class=Config):
    """Application Factory Pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure instance folder exists (needed for SQLite DB file)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass  # Already exists

    # Initialize Flask extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)  # Enable CORS for the app

    # Import and register routes (or blueprints)
    with app.app_context():  # Need app context for routes using current_app
        from . import routes
        # If using Blueprints, register them here:
        # from .api import bp as api_bp
        # app.register_blueprint(api_bp, url_prefix='/api')

    # Import models here to ensure they are known to Flask-Migrate
    # (though they are primarily used within routes/views)
    from app import models

    return app
