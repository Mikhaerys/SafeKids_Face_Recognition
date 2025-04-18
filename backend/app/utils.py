import face_recognition
import numpy as np
from PIL import Image  # Pillow is used by face_recognition
import os
import time  # Import time for timestamp generation
from werkzeug.utils import secure_filename
from flask import current_app
from pathlib import Path

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    """Checks if the filename has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file, folder_type):
    """Saves an uploaded file to the appropriate folder (reference or verified).

    Args:
        file: The file object from the request.
        folder_type (str): 'reference' or 'verified'.

    Returns:
        tuple: (relative_path_for_db, full_path_on_disk) or (None, None) if failed.
    """
    if not file or not allowed_file(file.filename or ''):
        current_app.logger.warning(
            f"File not saved. Invalid file or not allowed type: {getattr(file, 'filename', None)}")
        return None, None

    # Get original filename and make it secure
    orig_filename = secure_filename(file.filename)
    name, ext = os.path.splitext(orig_filename)

    # Create unique filename with timestamp to prevent collisions
    timestamp = int(time.time())
    unique_filename = f"{name}_{timestamp}{ext}"

    # Determine appropriate folder
    if folder_type == 'reference':
        folder_path = current_app.config['REFERENCE_FOLDER']
    elif folder_type == 'verified':
        folder_path = current_app.config['VERIFIED_FOLDER']
    else:
        current_app.logger.error(
            f"Invalid folder_type specified: {folder_type}")
        raise ValueError("Invalid folder_type specified")

    # Ensure the folder exists (should be created by config, but double-check)
    Path(folder_path).mkdir(parents=True, exist_ok=True)

    file_path = os.path.join(folder_path, unique_filename)
    current_app.logger.info(
        f"Generated unique filename: {unique_filename} from original: {orig_filename}")

    try:
        file.save(file_path)
        # Return the path relative to the base UPLOAD_FOLDER for storing in DB
        relative_path = os.path.join(folder_type, unique_filename)
        current_app.logger.info(f"Saved file to: {file_path}")
        return relative_path, file_path  # Return relative for DB, full for processing
    except Exception as e:
        current_app.logger.error(
            f"Failed to save file {unique_filename} to {folder_path}: {e}")
        return None, None


def get_face_encoding(image_path):
    """Loads an image and returns the first face encoding found."""
    try:
        current_app.logger.debug(f"Loading image for encoding: {image_path}")
        image = face_recognition.load_image_file(image_path)

        # Use model from config - either 'hog' (faster) or 'cnn' (more accurate)
        model = current_app.config.get('FACE_RECOGNITION_MODEL', 'hog')
        encodings = face_recognition.face_encodings(image, model=model)

        if encodings:
            current_app.logger.info(f"Found face encoding in: {image_path}")
            return encodings[0]  # Return the first encoding found
        else:
            current_app.logger.warning(f"No face found in image: {image_path}")
            return None
    except FileNotFoundError:
        current_app.logger.error(f"Image file not found at path: {image_path}")
        return None
    except Exception as e:
        current_app.logger.error(f"Error processing image {image_path}: {e}")
        return None


def compare_faces(known_encodings, unknown_encoding, tolerance=None):
    """Compares an unknown encoding against a list of known encodings.

    Args:
        known_encodings (list): A list of known face encodings (numpy arrays).
        unknown_encoding (numpy.ndarray): The encoding of the face to check.
        tolerance (float, optional): How much distance between faces to consider it a match.
                         Lower is stricter. Defaults to config value or 0.6.

    Returns:
        list: A list of booleans indicating matches for each known encoding.
    """
    # If no tolerance provided, use the value from config
    if tolerance is None:
        tolerance = current_app.config.get('FACE_RECOGNITION_TOLERANCE', 0.6)

    if unknown_encoding is None or not known_encodings:
        current_app.logger.debug(
            "Compare faces: No unknown encoding or no known encodings provided.")
        return []  # Return empty list if no unknown face or no known faces

    # Ensure known_encodings is a list of numpy arrays (filter out Nones)
    valid_known_encodings = [
        enc for enc in known_encodings if enc is not None and isinstance(enc, np.ndarray)]

    if not valid_known_encodings:
        current_app.logger.warning(
            "Compare faces: No valid known encodings available after filtering.")
        return []

    try:
        # Ensure unknown_encoding is also a numpy array
        if not isinstance(unknown_encoding, np.ndarray):
            current_app.logger.error(
                "Compare faces: unknown_encoding is not a numpy array.")
            return []

        current_app.logger.info(
            f"Comparing unknown face against {len(valid_known_encodings)} known faces (tolerance: {tolerance}).")
        matches = face_recognition.compare_faces(
            valid_known_encodings, unknown_encoding, tolerance=tolerance)
        return matches
    except Exception as e:
        current_app.logger.error(f"Error during face comparison: {e}")
        return []  # Return empty list on error
