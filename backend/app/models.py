from datetime import datetime
import json
import numpy as np


class Guardian:
    def __init__(self, doc_id=None, name=None, reference_image_path=None, face_encoding_str=None, student_ids=None):
        self.id = doc_id  # Document ID from Firestore
        self.name = name
        self.reference_image_path = reference_image_path
        self._face_encoding = face_encoding_str  # Stored as JSON string
        # List of student document IDs
        self.student_ids = student_ids if student_ids is not None else []

    @property
    def face_encoding(self):
        """Gets the face encoding, converting from JSON string to numpy array."""
        if self._face_encoding:
            return np.array(json.loads(self._face_encoding))
        return None

    @face_encoding.setter
    def face_encoding(self, value):
        """Sets the face encoding, converting numpy array to JSON string."""
        if value is not None:
            self._face_encoding = json.dumps(value.tolist())
        else:
            self._face_encoding = None

    def to_dict(self):
        return {
            "name": self.name,
            "reference_image_path": self.reference_image_path,
            "_face_encoding": self._face_encoding,
            "student_ids": self.student_ids
        }

    @staticmethod
    def from_dict(source_dict, doc_id):
        guardian = Guardian(
            doc_id=doc_id,
            name=source_dict.get("name"),
            reference_image_path=source_dict.get("reference_image_path"),
            face_encoding_str=source_dict.get("_face_encoding"),
            student_ids=source_dict.get("student_ids", [])
        )
        return guardian

    def __repr__(self):
        return f'<Guardian {self.name}>'


class Student:
    def __init__(self, doc_id=None, name=None, teacher_email=None, guardian_ids=None):
        self.id = doc_id  # Document ID from Firestore
        self.name = name
        self.teacher_email = teacher_email
        # List of guardian document IDs
        self.guardian_ids = guardian_ids if guardian_ids is not None else []

    def to_dict(self):
        return {
            "name": self.name,
            "teacher_email": self.teacher_email,
            "guardian_ids": self.guardian_ids
        }

    @staticmethod
    def from_dict(source_dict, doc_id):
        student = Student(
            doc_id=doc_id,
            name=source_dict.get("name"),
            teacher_email=source_dict.get("teacher_email"),
            guardian_ids=source_dict.get("guardian_ids", [])
        )
        return student

    def __repr__(self):
        return f'<Student {self.name}>'


class PickupLog:
    def __init__(self, doc_id=None, guardian_id=None, student_id=None, timestamp=None, verified_image_path=None):
        self.id = doc_id  # Document ID from Firestore
        self.guardian_id = guardian_id  # Document ID of the guardian
        self.student_id = student_id  # Document ID of the student
        self.timestamp = timestamp if timestamp else datetime.utcnow()
        self.verified_image_path = verified_image_path

    def to_dict(self):
        return {
            "guardian_id": self.guardian_id,
            "student_id": self.student_id,
            "timestamp": self.timestamp,  # Firestore handles datetime objects
            "verified_image_path": self.verified_image_path
        }

    @staticmethod
    def from_dict(source_dict, doc_id):
        log = PickupLog(
            doc_id=doc_id,
            guardian_id=source_dict.get("guardian_id"),
            student_id=source_dict.get("student_id"),
            # Firestore returns datetime objects
            timestamp=source_dict.get("timestamp"),
            verified_image_path=source_dict.get("verified_image_path")
        )
        return log

    def __repr__(self):
        return f'<PickupLog {self.timestamp} - G:{self.guardian_id} S:{self.student_id}>'
