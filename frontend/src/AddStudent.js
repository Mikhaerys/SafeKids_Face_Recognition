import React, { useState } from 'react';
import axios from 'axios';

const AddStudent = () => {
    const [studentName, setStudentName] = useState('');
    const [teacherEmail, setTeacherEmail] = useState(''); // Optional
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleAddStudent = async (e) => {
        e.preventDefault(); // Prevent default form submission
        if (!studentName.trim()) {
            setError("Student name cannot be empty.");
            return;
        }

        setLoading(true);
        setError('');
        setResult(null);

        const studentData = {
            name: studentName.trim(),
            teacher_email: teacherEmail.trim() || null // Send null if empty
        };

        try {
            // Adjust API endpoint if needed
            const response = await axios.post('http://127.0.0.1:5000/add_student', studentData, {
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            setResult(response.data);
            console.log("Add student response:", response.data);
            // Clear form on success
            setStudentName('');
            setTeacherEmail('');
        } catch (err) {
            console.error("Add student API error:", err);
            if (err.response) {
                setError(err.response.data.error || `Failed to add student: ${err.response.statusText}`);
            } else if (err.request) {
                setError("Failed to add student: Could not connect to the server.");
            } else {
                setError(`Failed to add student: ${err.message}`);
            }
            setResult(null);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="add-student-container"> {/* Optional: Add class for styling */}
            <h2>Add New Student</h2>
            <form onSubmit={handleAddStudent}>
                <div>
                    <label htmlFor="studentName">Student Name:</label>
                    <input
                        type="text"
                        id="studentName"
                        value={studentName}
                        onChange={(e) => setStudentName(e.target.value)}
                        placeholder="Enter student's full name"
                        disabled={loading}
                        required
                    />
                </div>
                <div>
                    <label htmlFor="teacherEmail">Teacher's Email (Optional):</label>
                    <input
                        type="email" // Use type email for basic validation
                        id="teacherEmail"
                        value={teacherEmail}
                        onChange={(e) => setTeacherEmail(e.target.value)}
                        placeholder="Enter teacher's email address"
                        disabled={loading}
                    />
                </div>
                <button type="submit" disabled={loading || !studentName.trim()}>
                    {loading ? 'Adding...' : 'Add Student'}
                </button>
            </form>

            {error && <p className="error-message">Error: {error}</p>}

            {result && (
                <div className="success-message">
                    <p>{result.message}</p>
                    <p>Student: {result.name} (ID: {result.student_id})</p>
                    {result.teacher_email && <p>Teacher Email: {result.teacher_email}</p>}
                </div>
            )}
        </div>
    );
};

export default AddStudent;