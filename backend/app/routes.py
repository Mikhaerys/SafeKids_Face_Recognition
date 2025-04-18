from flask import request, jsonify, current_app
from app import db  # db is initialized in __init__
from app.models import Guardian, Student, PickupLog
from app.utils import save_uploaded_file, get_face_encoding, compare_faces
import os
import numpy as np
from datetime import datetime

# Note: Routes are registered within the app factory in __init__.py
# We use current_app to access the application instance within requests


@current_app.route('/register_guardian', methods=['POST'])
def register_guardian():
    current_app.logger.info("Received request to /register_guardian")
    # --- Input Validation ---
    if 'image' not in request.files:
        current_app.logger.warning(
            "Register guardian failed: No image file provided")
        return jsonify({"error": "No image file provided"}), 400
    if 'name' not in request.form:
        current_app.logger.warning(
            "Register guardian failed: Guardian name not provided")
        return jsonify({"error": "Guardian name not provided"}), 400
    if 'student_ids' not in request.form:  # Expecting comma-separated IDs
        current_app.logger.warning(
            "Register guardian failed: Student IDs not provided")
        return jsonify({"error": "Student IDs not provided"}), 400

    file = request.files['image']
    name = request.form['name']
    student_ids_str = request.form['student_ids']

    if file.filename == '':
        current_app.logger.warning(
            "Register guardian failed: No selected file")
        return jsonify({"error": "No selected file"}), 400

    # --- File Handling & Face Encoding ---
    relative_path, full_path = save_uploaded_file(file, 'reference')
    if not relative_path:
        current_app.logger.error(
            "Register guardian failed: File save failed or type not allowed")
        return jsonify({"error": "File type not allowed or save failed"}), 400

    face_encoding = get_face_encoding(full_path)
    if face_encoding is None:
        current_app.logger.warning(
            f"Register guardian failed: No face detected or encoding error for {full_path}")
        # Clean up the saved file if encoding failed
        try:
            os.remove(full_path)
            current_app.logger.info(
                f"Removed file after failed encoding: {full_path}")
        except OSError as e:
            current_app.logger.error(
                f"Error removing file {full_path} after failed encoding: {e}")
        return jsonify({"error": "Could not detect a face in the provided image or processing failed."}), 400

    # --- Database Operations ---
    # Check if guardian with this image path already exists (should be unique)
    # Note: Using relative_path which includes folder_type
    existing_guardian = Guardian.query.filter_by(
        reference_image_path=relative_path).first()
    if existing_guardian:
        current_app.logger.warning(
            f"Register guardian conflict: Image path {relative_path} already exists.")
        # Clean up the newly saved file as it's a duplicate path
        try:
            os.remove(full_path)
        except OSError as e:
            current_app.logger.error(
                f"Error removing duplicate file {full_path}: {e}")
        # Conflict
        return jsonify({"error": f"An image with this filename ({file.filename}) already exists as a reference."}), 409

    # Find associated students
    student_ids = []
    try:
        student_ids = [int(id_str.strip())
                       for id_str in student_ids_str.split(',') if id_str.strip()]
        if not student_ids:
            raise ValueError("No valid student IDs provided.")
    except ValueError as e:
        current_app.logger.warning(
            f"Register guardian failed: Invalid student IDs format '{student_ids_str}'. Error: {e}")
        # Clean up saved file
        try:
            os.remove(full_path)
        except OSError:
            pass
        return jsonify({"error": "Invalid Student IDs format. Please provide comma-separated integers."}), 400

    students = Student.query.filter(Student.id.in_(student_ids)).all()
    if len(students) != len(student_ids):
        found_ids = {s.id for s in students}
        missing_ids = [sid for sid in student_ids if sid not in found_ids]
        current_app.logger.warning(
            f"Register guardian failed: Could not find students with IDs: {missing_ids}")
        # Clean up saved file
        try:
            os.remove(full_path)
        except OSError:
            pass
        # Not Found
        return jsonify({"error": f"Could not find students with IDs: {missing_ids}"}), 404

    # Create and save the new guardian
    try:
        guardian = Guardian(
            name=name,
            reference_image_path=relative_path,
            # The face_encoding setter handles numpy array -> JSON conversion
            face_encoding=face_encoding
        )
        # Add students to the guardian
        for student in students:
            guardian.students.append(student)

        db.session.add(guardian)
        db.session.commit()
        current_app.logger.info(
            f"Successfully registered guardian ID {guardian.id} ({guardian.name}) associated with students {[s.id for s in students]}")

        return jsonify({
            "message": "Guardian registered successfully",
            "guardian_id": guardian.id,
            "name": guardian.name,
            "students_associated": [{"id": s.id, "name": s.name} for s in guardian.students]
        }), 201  # Created
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Database error during guardian registration: {e}", exc_info=True)
        # Clean up saved file on DB error
        try:
            os.remove(full_path)
            current_app.logger.info(
                f"Removed file {full_path} after DB error.")
        except OSError as e_os:
            current_app.logger.error(
                f"Error removing file {full_path} after DB error: {e_os}")
        return jsonify({"error": "Database error occurred during registration."}), 500


@current_app.route('/verify_pickup', methods=['POST'])
def verify_pickup():
    current_app.logger.info("Received request to /verify_pickup")
    # --- Input Validation ---
    if 'image' not in request.files:
        current_app.logger.warning(
            "Verify pickup failed: No image file provided")
        return jsonify({"error": "No image file provided"}), 400

    file = request.files['image']
    if file.filename == '':
        current_app.logger.warning("Verify pickup failed: No selected file")
        return jsonify({"error": "No selected file"}), 400

    # --- File Handling & Face Encoding ---
    # Save the incoming image to the 'verified' folder (kept for records)
    relative_path, full_path = save_uploaded_file(file, 'verified')
    if not relative_path:
        current_app.logger.error(
            "Verify pickup failed: File save failed or type not allowed")
        return jsonify({"error": "File type not allowed or save failed"}), 400

    unknown_encoding = get_face_encoding(full_path)
    if unknown_encoding is None:
        current_app.logger.warning(
            f"Verify pickup failed: No face detected or encoding error for {full_path}")
        # Keep the verified image for auditing failed attempts
        return jsonify({"error": "Could not detect a face in the provided image or processing failed."}), 400

    # --- Face Comparison ---
    # Get all known guardians with valid encodings
    guardians = Guardian.query.filter(
        Guardian._face_encoding.isnot(None)).all()
    if not guardians:
        current_app.logger.warning(
            "Verify pickup failed: No registered guardians with face encodings found.")
        return jsonify({"error": "No registered guardians with face encodings found in the system."}), 404

    # The face_encoding property getter handles JSON -> numpy array conversion
    known_encodings = [g.face_encoding for g in guardians]
    known_guardian_ids = [g.id for g in guardians]

    matches = compare_faces(known_encodings, unknown_encoding)

    matched_guardian = None
    matched_guardian_id = None
    match_indices = [i for i, match in enumerate(matches) if match]

    if match_indices:
        # Simple approach: take the first match
        # More robust: calculate distances and take the closest if multiple matches
        first_match_index = match_indices[0]
        matched_guardian_id = known_guardian_ids[first_match_index]
        matched_guardian = Guardian.query.get(matched_guardian_id)
        current_app.logger.info(
            f"Verification successful: Matched guardian ID {matched_guardian.id} ({matched_guardian.name})")

        # --- Logging & Notification ---
        students_authorized = []
        log_entries = []
        try:
            # Log pickup for all students associated with the matched guardian
            for student in matched_guardian.students:
                log_entry = PickupLog(
                    guardian_id=matched_guardian.id,
                    student_id=student.id,
                    verified_image_path=relative_path,  # Store relative path of verified image
                    timestamp=datetime.utcnow()
                )
                db.session.add(log_entry)
                log_entries.append(log_entry)  # Keep track for timestamp
                students_authorized.append({
                    "id": student.id,
                    "name": student.name,
                    "teacher_email": student.teacher_email
                })

            db.session.commit()
            current_app.logger.info(
                f"Pickup logged for guardian {matched_guardian.id} and students {[s['id'] for s in students_authorized]}")

            # --- Teacher Notification Placeholder --- #
            # In a real app, this would trigger emails/SMS/push notifications
            # Example: iterate through students_authorized and send email to teacher_email
            for student_info in students_authorized:
                if student_info.get('teacher_email'):
                    current_app.logger.info(
                        f"NOTIFICATION: Send email to {student_info['teacher_email']} for pickup of {student_info['name']} by {matched_guardian.name}")
                else:
                    current_app.logger.warning(
                        f"NOTIFICATION: No teacher email for student {student_info['name']} (ID: {student_info['id']}) to notify.")
            # ---------------------------------------- #

            # Use timestamp from the first log entry (they should be nearly identical)
            # ISO 8601 format
            pickup_time = log_entries[0].timestamp.isoformat() + "Z"

            return jsonify({
                "match": True,
                "guardian_id": matched_guardian.id,
                "guardian_name": matched_guardian.name,
                "authorized_students": students_authorized,
                "pickup_log_time": pickup_time
            }), 200  # OK

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"Database error during pickup logging: {e}", exc_info=True)
            return jsonify({"error": "Database error occurred during pickup logging."}), 500
    else:
        # No match found
        current_app.logger.warning(
            f"Verification failed: No match found for image {relative_path}")
        # Keep the verified image for auditing failed attempts
        # Unauthorized
        return jsonify({"match": False, "message": "No authorized guardian matched the provided image."}), 401

# === Helper/Management Routes ===


@current_app.route('/add_student', methods=['POST'])
def add_student():
    """Adds a new student to the database."""
    current_app.logger.info("Received request to /add_student")
    data = request.get_json()
    if not data or 'name' not in data:
        current_app.logger.warning(
            "Add student failed: Missing 'name' in request body")
        return jsonify({"error": "Student name not provided in JSON body"}), 400

    name = data['name']
    teacher_email = data.get('teacher_email')  # Optional

    # Basic check for existing student by name (consider making name unique in model if required)
    if Student.query.filter_by(name=name).first():
        current_app.logger.warning(
            f"Add student conflict: Student with name '{name}' already exists")
        # Conflict
        return jsonify({"error": f"Student with name '{name}' already exists"}), 409

    try:
        student = Student(name=name, teacher_email=teacher_email)
        db.session.add(student)
        db.session.commit()
        current_app.logger.info(
            f"Successfully added student ID {student.id} ({student.name})")
        return jsonify({
            "message": "Student added successfully",
            "student_id": student.id,
            "name": student.name,
            "teacher_email": student.teacher_email
        }), 201  # Created
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Database error adding student: {e}", exc_info=True)
        return jsonify({"error": "Database error occurred adding student."}), 500


@current_app.route('/students', methods=['GET'])
def get_students():
    """Returns a list of all students."""
    current_app.logger.debug("Received request to GET /students")
    try:
        students = Student.query.all()
        return jsonify([{
            "id": s.id,
            "name": s.name,
            "teacher_email": s.teacher_email
        } for s in students]), 200
    except Exception as e:
        current_app.logger.error(
            f"Error fetching students: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve students"}), 500


@current_app.route('/guardians', methods=['GET'])
def get_guardians():
    """Returns a list of all guardians and their associated students."""
    current_app.logger.debug("Received request to GET /guardians")
    try:
        guardians = Guardian.query.all()
        result = []
        for g in guardians:
            # Access students through the relationship (dynamic query)
            students = [{"id": s.id, "name": s.name} for s in g.students.all()]
            result.append({
                "id": g.id,
                "name": g.name,
                "reference_image_path": g.reference_image_path,
                # Check if encoding exists (might be null if registration failed mid-way once)
                "has_face_encoding": g._face_encoding is not None,
                "students": students
            })
        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(
            f"Error fetching guardians: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve guardians"}), 500
