from flask import request, jsonify, current_app
# from app import db # Removed SQLAlchemy
from app import firestore_db  # Added Firestore client
from google.cloud.firestore import ArrayUnion  # Changed to this import
from app.models import Guardian, Student, PickupLog
from app.utils import save_uploaded_file, get_face_encoding, compare_faces
import os
import json
from datetime import datetime


@current_app.route('/', methods=['GET'])
def index():
    """Root endpoint to check if the API is working."""
    return jsonify({
        "status": "online",
        "message": "FR Safe Kids API is running",
        "endpoints": [
            "/register_guardian",
            "/verify_pickup",
            "/add_student",
            "/students",
            "/guardians"
        ]
    })


@current_app.route('/register_guardian', methods=['POST'])
def register_guardian():
    """Register a new guardian with their reference image and associated students."""
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

    if 'student_ids' not in request.form:
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
        try:
            os.remove(full_path)
            current_app.logger.info(
                f"Removed file after failed encoding: {full_path}")
        except OSError as e:
            current_app.logger.error(
                f"Error removing file {full_path} after failed encoding: {e}")
        return jsonify({"error": "Could not detect a face in the provided image or processing failed."}), 400

    # --- Check for existing guardian with same image path --- # Firestore query will be different
    # existing_guardian = Guardian.query.filter_by( # Removed SQLAlchemy query
    #     reference_image_path=relative_path).first()
    guardians_ref = firestore_db.collection('guardians')
    query = guardians_ref.where(
        'reference_image_path', '==', relative_path).limit(1)
    results = list(query.stream())
    existing_guardian_doc = results[0] if results else None

    if existing_guardian_doc:
        current_app.logger.warning(
            f"Register guardian conflict: Image path {relative_path} already exists.")
        try:
            os.remove(full_path)
        except OSError as e:
            current_app.logger.error(
                f"Error removing duplicate file {full_path}: {e}")
        return jsonify({"error": f"An image with this filename ({file.filename}) already exists as a reference."}), 409

    # --- Parse and validate student IDs ---
    student_ids_str_list = []  # Changed to store string IDs for Firestore
    try:
        student_ids_str_list = [
            id_str.strip() for id_str in student_ids_str.split(',') if id_str.strip()]
        if not student_ids_str_list:
            raise ValueError("No valid student IDs provided.")
    except ValueError as e:
        current_app.logger.warning(
            f"Register guardian failed: Invalid student IDs format '{student_ids_str}'. Error: {e}")
        try:
            os.remove(full_path)
        except OSError:
            pass
        return jsonify({"error": "Invalid Student IDs format. Please provide comma-separated integers."}), 400

    # --- Find associated students --- # Firestore query will be different
    # students = Student.query.filter(Student.id.in_(student_ids)).all() # Removed SQLAlchemy query
    students_ref = firestore_db.collection('students')
    found_students = []
    missing_ids = []
    # Firestore does not have an 'IN' query for more than 10 items directly in the python client like SQLAlchemy.
    # We will fetch each student document individually or adjust if this becomes a performance bottleneck.
    # For now, assuming student_ids_str_list is not excessively long.
    for s_id_str in student_ids_str_list:
        student_doc = students_ref.document(s_id_str).get()
        if student_doc.exists:
            found_students.append(Student.from_dict(
                student_doc.to_dict(), student_doc.id))
        else:
            missing_ids.append(s_id_str)

    if missing_ids:
        current_app.logger.warning(
            f"Register guardian failed: Could not find students with IDs: {missing_ids}")
        try:
            os.remove(full_path)
        except OSError:
            pass
        return jsonify({"error": f"Could not find students with IDs: {missing_ids}"}), 404

    # --- Create and save the new guardian --- # Firestore operations
    try:
        guardian = Guardian(
            name=name,
            reference_image_path=relative_path,
            face_encoding_str=json.dumps(face_encoding.tolist(
            )) if face_encoding is not None else None,  # Store as JSON string
            # Store list of student document IDs
            student_ids=[s.id for s in found_students]
        )
        # Add students to the guardian # This relationship is now stored in guardian.student_ids and student.guardian_ids
        # for student in students: # Removed
        #     guardian.students.append(student) # Removed

        # db.session.add(guardian) # Removed SQLAlchemy
        # db.session.commit() # Removed SQLAlchemy

        # Add guardian to Firestore
        # Firestore auto-generates an ID if document_id is not provided to .document()
        guardian_doc_ref = firestore_db.collection('guardians').document()
        guardian.id = guardian_doc_ref.id  # Assign the auto-generated ID to the object
        guardian_doc_ref.set(guardian.to_dict())

        # Update students with this guardian's ID
        for student_obj in found_students:
            student_doc_ref = firestore_db.collection(
                'students').document(student_obj.id)
            # Atomically add the new guardian's ID to the student's guardian_ids list
            student_doc_ref.update(
                {'guardian_ids': ArrayUnion([guardian.id])})

        current_app.logger.info(f"Successfully registered guardian ID {guardian.id} ({guardian.name}) "
                                f"associated with students {[s.id for s in found_students]}")

        return jsonify({
            "message": "Guardian registered successfully",
            "guardian_id": guardian.id,
            "name": guardian.name,
            "students_associated": [{"id": s.id, "name": s.name} for s in found_students]
        }), 201  # Created

    except Exception as e:
        # db.session.rollback() # Removed SQLAlchemy
        current_app.logger.error(
            f"Error during guardian registration: {e}", exc_info=True)
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
    """Verify a guardian's identity and log student pickups."""
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
    relative_path, full_path = save_uploaded_file(file, 'verified')
    if not relative_path:
        current_app.logger.error(
            "Verify pickup failed: File save failed or type not allowed")
        return jsonify({"error": "File type not allowed or save failed"}), 400

    unknown_encoding = get_face_encoding(full_path)
    if unknown_encoding is None:
        current_app.logger.warning(
            f"Verify pickup failed: No face detected or encoding error for {full_path}")
        return jsonify({"error": "Could not detect a face in the provided image or processing failed."}), 400

    # --- Get all guardians with valid face encodings --- # Firestore query
    # guardians = Guardian.query.filter( # Removed SQLAlchemy
    #     Guardian._face_encoding.isnot(None)).all()
    guardians_ref = firestore_db.collection('guardians')
    # Firestore doesn't directly support .isnot(None) in the same way.
    # We fetch all guardians and filter in Python, or structure data to query for existing _face_encoding field.
    # For simplicity, fetching all and filtering. This could be optimized if needed.
    all_guardian_docs = guardians_ref.stream()
    guardians = []
    for doc in all_guardian_docs:
        g_data = doc.to_dict()
        if g_data.get('_face_encoding'):
            guardians.append(Guardian.from_dict(g_data, doc.id))

    if not guardians:
        current_app.logger.warning(
            "Verify pickup failed: No registered guardians with face encodings found.")
        return jsonify({"error": "No registered guardians with face encodings found in the system."}), 404

    # --- Compare with known faces ---
    known_encodings = [g.face_encoding for g in guardians]
    known_guardian_ids = [g.id for g in guardians]

    # Get tolerance from config
    tolerance = current_app.config.get('FACE_RECOGNITION_TOLERANCE', 0.6)
    matches = compare_faces(known_encodings, unknown_encoding, tolerance)

    match_indices = [i for i, match in enumerate(matches) if match]

    if not match_indices:
        current_app.logger.warning(
            f"Verification failed: No match found for image {relative_path}")
        return jsonify({"match": False, "message": "No authorized guardian matched the provided image."}), 401

    # --- Process matched guardian --- # Firestore query
    first_match_index = match_indices[0]  # Take the first match
    matched_guardian_id = known_guardian_ids[first_match_index]
    # matched_guardian = Guardian.query.get(matched_guardian_id) # Removed SQLAlchemy
    matched_guardian_doc = firestore_db.collection(
        'guardians').document(matched_guardian_id).get()
    if not matched_guardian_doc.exists:
        current_app.logger.error(
            f"Matched guardian ID {matched_guardian_id} not found in Firestore.")
        return jsonify({"error": "Matched guardian data not found."}), 500
    matched_guardian = Guardian.from_dict(
        matched_guardian_doc.to_dict(), matched_guardian_doc.id)

    current_app.logger.info(
        f"Verification successful: Matched guardian ID {matched_guardian.id} ({matched_guardian.name})")

    # --- Log pickup for all associated students --- # Firestore operations
    students_authorized = []
    log_entries_data = []  # Store dicts for Firestore batch
    pickup_timestamp = datetime.utcnow()

    try:
        # Fetch students associated with the guardian
        # This requires fetching student details based on matched_guardian.student_ids
        students_to_log = []
        if matched_guardian.student_ids:
            students_ref = firestore_db.collection('students')
            for student_id_str in matched_guardian.student_ids:
                s_doc = students_ref.document(student_id_str).get()
                if s_doc.exists:
                    students_to_log.append(
                        Student.from_dict(s_doc.to_dict(), s_doc.id))
                else:
                    current_app.logger.warning(
                        f"Student ID {student_id_str} for guardian {matched_guardian.id} not found.")

        batch = firestore_db.batch()  # Use a batch for atomic writes
        pickup_logs_ref = firestore_db.collection('pickuplogs')

        for student_obj in students_to_log:
            log_entry = PickupLog(
                guardian_id=matched_guardian.id,
                student_id=student_obj.id,
                verified_image_path=relative_path,
                timestamp=pickup_timestamp
            )
            # db.session.add(log_entry) # Removed SQLAlchemy
            log_doc_ref = pickup_logs_ref.document()  # Auto-generate ID for log entry
            log_entry.id = log_doc_ref.id
            batch.set(log_doc_ref, log_entry.to_dict())
            log_entries_data.append(log_entry.to_dict())  # For response

            students_authorized.append({
                "id": student_obj.id,
                "name": student_obj.name,
                "teacher_email": student_obj.teacher_email
            })

        # db.session.commit() # Removed SQLAlchemy
        batch.commit()  # Commit all log entries

        current_app.logger.info(
            f"Pickup logged for guardian {matched_guardian.id} and students {[s['id'] for s in students_authorized]}")

        # --- Simulate teacher notifications ---
        for student_info in students_authorized:
            if student_info.get('teacher_email'):
                current_app.logger.info(
                    f"NOTIFICATION: Send email to {student_info['teacher_email']} for pickup of {student_info['name']} by {matched_guardian.name}")
            else:
                current_app.logger.warning(
                    f"NOTIFICATION: No teacher email for student {student_info['name']} (ID: {student_info['id']}) to notify.")

        # ISO 8601 format for timestamp
        pickup_time = pickup_timestamp.isoformat() + "Z"

        return jsonify({
            "match": True,
            "guardian_id": matched_guardian.id,
            "guardian_name": matched_guardian.name,
            "authorized_students": students_authorized,
            "pickup_log_time": pickup_time
        }), 200

    except Exception as e:
        # db.session.rollback() # Removed SQLAlchemy
        current_app.logger.error(
            f"Database error during pickup logging: {e}", exc_info=True)
        return jsonify({"error": "Database error occurred during pickup logging."}), 500


# === Helper/Management Routes ===

@current_app.route('/add_student', methods=['POST'])
def add_student():
    """Add a new student to the database."""
    current_app.logger.info("Received request to /add_student")
    data = request.get_json()
    if not data or 'name' not in data:
        current_app.logger.warning(
            "Add student failed: Missing 'name' in request body")
        return jsonify({"error": "Student name not provided in JSON body"}), 400

    name = data['name']
    teacher_email = data.get('teacher_email')  # Optional
    # Optional, list of guardian doc IDs
    guardian_ids_str = data.get('guardian_ids', [])

    # existing_student = Student.query.filter_by(name=name).first() # Removed SQLAlchemy
    students_ref = firestore_db.collection('students')
    query = students_ref.where('name', '==', name).limit(1)
    results = list(query.stream())
    existing_student_doc = results[0] if results else None

    if existing_student_doc:
        current_app.logger.warning(
            f"Add student conflict: Student with name '{name}' already exists")
        return jsonify({"error": f"Student with name '{name}' already exists"}), 409

    try:
        student = Student(name=name, teacher_email=teacher_email,
                          guardian_ids=guardian_ids_str)
        # db.session.add(student) # Removed SQLAlchemy
        # db.session.commit() # Removed SQLAlchemy

        student_doc_ref = students_ref.document()  # Auto-generate ID
        student.id = student_doc_ref.id
        student_doc_ref.set(student.to_dict())

        # If guardian_ids are provided, update those guardians to include this new student
        if guardian_ids_str:
            guardians_ref = firestore_db.collection('guardians')
            for g_id_str in guardian_ids_str:
                guardian_doc_ref = guardians_ref.document(g_id_str)
                # Atomically add the new student's ID to the guardian's student_ids list
                guardian_doc_ref.update(
                    {'student_ids': ArrayUnion([student.id])})

        current_app.logger.info(
            f"Successfully added student ID {student.id} ({student.name})")
        return jsonify({
            "message": "Student added successfully",
            "student_id": student.id,
            "name": student.name,
            "teacher_email": student.teacher_email,
            "guardian_ids": student.guardian_ids
        }), 201
    except Exception as e:
        # db.session.rollback() # Removed SQLAlchemy
        current_app.logger.error(
            f"Database error adding student: {e}", exc_info=True)
        return jsonify({"error": "Database error occurred adding student."}), 500


@current_app.route('/students', methods=['GET'])
def get_students():
    """Return a list of all students."""
    current_app.logger.debug("Received request to GET /students")
    try:
        # students = Student.query.all() # Removed SQLAlchemy
        students_ref = firestore_db.collection('students')
        all_student_docs = students_ref.stream()
        students_list = []
        for doc in all_student_docs:
            s_data = doc.to_dict()
            students_list.append({
                "id": doc.id,
                "name": s_data.get("name"),
                "teacher_email": s_data.get("teacher_email"),
                "guardian_ids": s_data.get("guardian_ids", [])
            })
        return jsonify(students_list), 200
    except Exception as e:
        current_app.logger.error(
            f"Error fetching students: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve students"}), 500


@current_app.route('/guardians', methods=['GET'])
def get_guardians():
    """Return a list of all guardians and their associated students."""
    current_app.logger.debug("Received request to GET /guardians")
    try:
        # guardians = Guardian.query.all() # Removed SQLAlchemy
        guardians_ref = firestore_db.collection('guardians')
        all_guardian_docs = guardians_ref.stream()
        result = []

        # To get student names, we might need to fetch them. This can be N+1.
        # For simplicity now, just returning student_ids. Could be optimized.
        # If student names are crucial, consider denormalizing or making separate student queries.

        for doc in all_guardian_docs:
            g_data = doc.to_dict()
            # students = [{"id": s.id, "name": s.name} for s in g.students.all()] # Removed SQLAlchemy
            # Fetch student details for each guardian - this can be inefficient for many guardians/students
            # A better approach for production might be to denormalize student names if frequently needed here,
            # or adjust the client to fetch student details separately if required.
            student_ids = g_data.get("student_ids", [])
            # For this example, we will just return the IDs. Client can fetch details if needed.
            # students_details = []
            # if student_ids:
            #     students_ref = firestore_db.collection('students')
            #     for s_id in student_ids:
            #         s_doc = students_ref.document(s_id).get()
            #         if s_doc.exists:
            #             s_data = s_doc.to_dict()
            #             students_details.append({"id": s_doc.id, "name": s_data.get("name")})
            #         else:
            #             students_details.append({"id": s_id, "name": "(Student not found)"})

            result.append({
                "id": doc.id,
                "name": g_data.get("name"),
                "reference_image_path": g_data.get("reference_image_path"),
                "has_face_encoding": g_data.get("_face_encoding") is not None,
                "student_ids": student_ids  # Returning IDs, not full student objects
            })
        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(
            f"Error fetching guardians: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve guardians"}), 500
