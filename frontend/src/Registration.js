import React, { useState, useRef, useCallback, useEffect } from 'react';
import Webcam from 'react-webcam';
import axios from 'axios';
import config from './config';

const Registration = () => {
    const webcamRef = useRef(null);
    const fileInputRef = useRef(null); // Ref for file input
    const [imgSrc, setImgSrc] = useState(null); // Can be from webcam or file
    const [guardianName, setGuardianName] = useState('');
    const [students, setStudents] = useState([]);
    const [selectedStudents, setSelectedStudents] = useState(new Set());
    const [registrationResult, setRegistrationResult] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [useWebcam, setUseWebcam] = useState(true); // Toggle between webcam and file upload
    const [studentSearchTerm, setStudentSearchTerm] = useState(''); // Added for student search

    const videoConstraints = config.imageSettings.webcam;

    // Fetch students on component mount
    useEffect(() => {
        const fetchStudents = async () => {
            try {
                const response = await axios.get(`${config.api.baseUrl}/students`);
                setStudents(response.data || []);
            } catch (err) {
                console.error("Error fetching students:", err);
                setError('Failed to load student list. Please try again later.');
            }
        };
        fetchStudents();
    }, []);

    // Function to convert base64 image to Blob
    const dataURLtoBlob = (dataurl) => {
        if (!dataurl) return null;
        try {
            const arr = dataurl.split(',');
            if (arr.length < 2) return null;
            const mimeMatch = arr[0].match(/:(.*?);/); // Fixed regex: removed space after colon
            if (!mimeMatch || mimeMatch.length < 2) return null;
            const mime = mimeMatch[1];
            const bstr = atob(arr[1]);
            let n = bstr.length;
            const u8arr = new Uint8Array(n);
            while (n--) {
                u8arr[n] = bstr.charCodeAt(n);
            }
            return new Blob([u8arr], { type: mime });
        } catch (e) {
            console.error("Error converting data URL to Blob:", e);
            return null;
        }
    }

    const capture = useCallback(() => {
        if (!webcamRef.current) return;
        const imageSrc = webcamRef.current.getScreenshot();
        if (imageSrc) {
            setImgSrc(imageSrc);
            setRegistrationResult(null);
            setError('');
        } else {
            setError("Could not capture image from webcam.");
            setImgSrc(null);
        }
    }, [webcamRef, setImgSrc, setRegistrationResult, setError]);

    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => {
                setImgSrc(reader.result); // Set as base64 string
                setRegistrationResult(null);
                setError('');
            }
            reader.onerror = () => {
                setError("Failed to read the selected file.");
                setImgSrc(null);
            }
            reader.readAsDataURL(file);
        }
    };

    const handleStudentSelection = (studentId) => {
        setSelectedStudents(prevSelected => {
            const newSelected = new Set(prevSelected);
            if (newSelected.has(studentId)) {
                newSelected.delete(studentId);
            } else {
                newSelected.add(studentId);
            }
            return newSelected;
        });
    };

    const handleRegister = async () => {
        if (!imgSrc) {
            setError("Please capture or upload an image first.");
            return;
        }
        if (!guardianName.trim()) {
            setError("Please enter the guardian's name.");
            return;
        }
        if (selectedStudents.size === 0) {
            setError("Please select at least one student.");
            return;
        }

        let imageBlob;
        let fileName = 'capture.jpg'; // Default for webcam

        if (imgSrc.startsWith('data:image')) {
            // It's a base64 string from webcam or file reader
            imageBlob = dataURLtoBlob(imgSrc);
        } else {
            setError("Invalid image source."); // Should not happen with current logic
            return;
        }

        if (!imageBlob) {
            setError("Failed to process the image.");
            return;
        }

        // If image came from file input, use original filename to help with identification
        // Note: The backend will generate a unique filename with timestamp to prevent conflicts
        if (!useWebcam && fileInputRef.current && fileInputRef.current.files[0]) {
            fileName = fileInputRef.current.files[0].name;
        }


        const formData = new FormData();
        formData.append('image', imageBlob, fileName);
        formData.append('name', guardianName.trim());
        formData.append('student_ids', Array.from(selectedStudents).join(','));

        setLoading(true);
        setError('');
        setRegistrationResult(null);

        try {
            const response = await axios.post(`${config.api.baseUrl}/register_guardian`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });
            setRegistrationResult(response.data);
            console.log("Registration response:", response.data);
            // Optionally clear form on success
            // setGuardianName('');
            // setImgSrc(null);
            // setSelectedStudents(new Set());
            // if (fileInputRef.current) fileInputRef.current.value = ''; // Clear file input
        } catch (err) {
            console.error("Registration API error:", err);
            if (err.response) {
                setError(err.response.data.error || `Registration failed: ${err.response.statusText}`);
            } else if (err.request) {
                setError("Registration failed: Could not connect to the server.");
            } else {
                setError(`Registration failed: ${err.message}`);
            }
            setRegistrationResult(null);
        } finally {
            setLoading(false);
        }
    };

    // Calculate filteredStudents
    const lcSearchTerm = studentSearchTerm.toLowerCase();
    const currentFilteredStudents = (studentSearchTerm && students.length > 0)
        ? students.filter(student =>
            (student.name && student.name.toLowerCase().includes(lcSearchTerm)) ||
            (student.id && student.id.toString().toLowerCase().includes(lcSearchTerm))
        )
        : [];

    return (
        <div className="registration-container">
            <h2>Register New Guardian</h2>

            <div className="input-toggle-container">
                <button
                    onClick={() => setUseWebcam(true)}
                    disabled={useWebcam || loading}
                    className={useWebcam ? 'active' : ''}
                >
                    Use Webcam
                </button>
                <button
                    onClick={() => setUseWebcam(false)}
                    disabled={!useWebcam || loading}
                    className={!useWebcam ? 'active' : ''}
                >
                    Upload File
                </button>
            </div>

            <div className="webcam-capture-section">
                {useWebcam ? (
                    <div className="webcam-container">
                        <Webcam
                            audio={false}
                            ref={webcamRef}
                            screenshotFormat="image/jpeg"
                            width={videoConstraints.width}
                            height={videoConstraints.height}
                            videoConstraints={videoConstraints}
                        />
                        <button onClick={capture} disabled={loading}>Capture Photo</button>
                    </div>
                ) : (
                    <div className="file-input-container">
                        <label htmlFor="file-upload">Upload Reference Image:</label>
                        <input
                            id="file-upload"
                            type="file"
                            accept="image/png, image/jpeg, image/jpg"
                            onChange={handleFileChange}
                            ref={fileInputRef}
                            disabled={loading}
                        />
                    </div>
                )}

                {imgSrc && (
                    <div className="preview-container">
                        <h3>Preview:</h3>
                        <img src={imgSrc} alt="Guardian preview" width={videoConstraints.width / 2} />
                    </div>
                )}
            </div>

            {imgSrc && ( // Only show form fields after image is ready
                <div className="registration-form">
                    <div className="form-group">
                        <label htmlFor="guardianName">Guardian Name:</label>
                        <input
                            type="text"
                            id="guardianName"
                            value={guardianName}
                            onChange={(e) => setGuardianName(e.target.value)}
                            placeholder="Enter guardian's full name"
                            disabled={loading}
                        />
                    </div>

                    <div className="student-selection">
                        <label htmlFor="studentSearchInput">Select Authorized Students:</label>
                        <input
                            type="text"
                            id="studentSearchInput"
                            value={studentSearchTerm}
                            onChange={(e) => setStudentSearchTerm(e.target.value)}
                            placeholder="Buscar estudiantes por nombre o ID..."
                            disabled={loading}
                            className="student-search-input"
                        />

                        {/* Status messages based on loading, error, and student availability */}
                        {loading && students.length === 0 && !error && <p className="info-message">Cargando estudiantes...</p>}
                        {!loading && students.length === 0 && error && <p className="error-message">Error al cargar la lista de estudiantes. Intente más tarde.</p>}
                        {!loading && students.length === 0 && !error && <p className="info-message">No hay estudiantes disponibles para seleccionar.</p>}

                        {/* Display logic when students ARE available */}
                        {students.length > 0 && (
                            <div className="students-container">
                                {!studentSearchTerm && (
                                    <p className="info-message">Escriba en la barra de búsqueda para filtrar y seleccionar estudiantes.</p>
                                )}
                                {studentSearchTerm && currentFilteredStudents.length > 0 && (
                                    <div className="students-list">
                                        {currentFilteredStudents.map(student => (
                                            <div key={student.id} className="student-item">
                                                <div className="custom-checkbox">
                                                    <input
                                                        type="checkbox"
                                                        id={`student-${student.id}`}
                                                        checked={selectedStudents.has(student.id)}
                                                        onChange={() => handleStudentSelection(student.id)}
                                                        disabled={loading}
                                                    />
                                                    <label htmlFor={`student-${student.id}`} className="student-label">
                                                        {student.name} <span className="student-id">(ID: {student.id})</span>
                                                    </label>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                                {studentSearchTerm && currentFilteredStudents.length === 0 && (
                                    <p className="info-message">No se encontraron estudiantes que coincidan con "{studentSearchTerm}".</p>
                                )}
                            </div>
                        )}
                    </div>

                    <button
                        onClick={handleRegister}
                        disabled={loading || !guardianName.trim() || selectedStudents.size === 0 || !imgSrc}
                        className="register-button"
                    >
                        {loading ? 'Registering...' : 'Register Guardian'}
                    </button>
                </div>
            )}

            {error && <p className="error-message">Error: {error}</p>}

            {registrationResult && (
                <div className="registration-result success-message">
                    <p>{registrationResult.message}</p>
                    <p>Guardian: {registrationResult.name} (ID: {registrationResult.guardian_id})</p>
                    <p>Students Associated:</p>
                    <ul>
                        {registrationResult.students_associated?.map(s => <li key={s.id}>{s.name} (ID: {s.id})</li>)}
                    </ul>
                </div>
            )}
        </div>
    );
};

export default Registration;