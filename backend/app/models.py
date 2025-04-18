from app import db
from datetime import datetime
import json
import numpy as np  # Needed for converting list back to numpy array

# Association table for the many-to-many relationship between Guardian and Student
guardian_student_association = db.Table('guardian_student', db.metadata,
                                        db.Column('guardian_id', db.Integer, db.ForeignKey(
                                            'guardian.id'), primary_key=True),
                                        db.Column('student_id', db.Integer, db.ForeignKey(
                                            'student.id'), primary_key=True)
                                        )


class Guardian(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True, nullable=False)
    # Store path relative to the UPLOAD_FOLDER defined in config
    reference_image_path = db.Column(
        db.String(256), nullable=False, unique=True)
    # Store face encoding as JSON string (list of floats)
    _face_encoding = db.Column(db.Text, nullable=True)  # Internal storage

    students = db.relationship(
        'Student', secondary=guardian_student_association,
        back_populates='guardians', lazy='dynamic'  # Use dynamic for queries
    )
    pickup_logs = db.relationship(
        'PickupLog', backref='guardian', lazy='dynamic')

    @property
    def face_encoding(self):
        """Gets the face encoding, converting from JSON string to numpy array."""
        if self._face_encoding:
            # Convert list of floats back to numpy array
            return np.array(json.loads(self._face_encoding))
        return None

    @face_encoding.setter
    def face_encoding(self, value):
        """Sets the face encoding, converting numpy array to JSON string."""
        if value is not None:
            # Convert numpy array to list for JSON serialization
            self._face_encoding = json.dumps(value.tolist())
        else:
            self._face_encoding = None

    def __repr__(self):
        return f'<Guardian {self.name}>'


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True, nullable=False)
    teacher_email = db.Column(
        db.String(128), index=True, nullable=True)  # For notifications

    guardians = db.relationship(
        'Guardian', secondary=guardian_student_association,
        back_populates='students', lazy='dynamic'
    )
    pickup_logs = db.relationship(
        'PickupLog', backref='student', lazy='dynamic')

    def __repr__(self):
        return f'<Student {self.name}>'


class PickupLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guardian_id = db.Column(db.Integer, db.ForeignKey(
        'guardian.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey(
        'student.id'), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # Store path relative to the UPLOAD_FOLDER defined in config
    verified_image_path = db.Column(db.String(256), nullable=False)

    def __repr__(self):
        return f'<PickupLog {self.timestamp} - G:{self.guardian_id} S:{self.student_id}>'
