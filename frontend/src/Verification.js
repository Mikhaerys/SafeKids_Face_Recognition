import React, { useState, useRef, useCallback } from 'react';
import Webcam from 'react-webcam';
import axios from 'axios';

const Verification = () => {
    const webcamRef = useRef(null);
    const [imgSrc, setImgSrc] = useState(null);
    const [verificationResult, setVerificationResult] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const videoConstraints = {
        width: 480,
        height: 480,
        facingMode: "user" // or "environment" for rear camera
    };

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
        const imageSrc = webcamRef.current.getScreenshot();
        if (imageSrc) {
            setImgSrc(imageSrc);
            setVerificationResult(null); // Clear previous results
            setError(''); // Clear previous errors
        } else {
            setError("Could not capture image from webcam.");
            setImgSrc(null);
        }
    }, [webcamRef, setImgSrc, setVerificationResult, setError]);

    const handleVerify = async () => {
        if (!imgSrc) {
            setError("Please capture an image first.");
            return;
        }

        const imageBlob = dataURLtoBlob(imgSrc);
        if (!imageBlob) {
            setError("Failed to process captured image.");
            return;
        }

        const formData = new FormData();
        // The backend will generate a unique filename using timestamps
        formData.append('image', imageBlob, 'capture.jpg');

        setLoading(true);
        setError('');
        setVerificationResult(null);

        try {
            // Assuming backend runs on http://127.0.0.1:5000
            // Adjust if your Flask server runs elsewhere
            const response = await axios.post('http://127.0.0.1:5000/verify_pickup', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });
            setVerificationResult(response.data);
            console.log("Verification response:", response.data);
        } catch (err) {
            console.error("Verification API error:", err);
            if (err.response) {
                // Error from backend (e.g., no match, no face detected)
                setError(err.response.data.error || `Verification failed: ${err.response.statusText}`);
            } else if (err.request) {
                // Network error
                setError("Verification failed: Could not connect to the server.");
            } else {
                // Other errors
                setError(`Verification failed: ${err.message}`);
            }
            setVerificationResult(null); // Clear result on error
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <h2>Guardian Verification</h2>
            <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-start' }}>
                <div>
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
                {imgSrc && (
                    <div>
                        <h3>Captured Image:</h3>
                        <img src={imgSrc} alt="Captured guardian" width={videoConstraints.width / 2} />
                        <button onClick={handleVerify} disabled={loading}>
                            {loading ? 'Verifying...' : 'Verify Identity'}
                        </button>
                    </div>
                )}
            </div>

            {error && <p style={{ color: 'red' }}>Error: {error}</p>}

            {verificationResult && (
                <div>
                    <h3>Verification Result:</h3>
                    {verificationResult.match ? (
                        <div>
                            <p><strong>Match Found!</strong></p>
                            <p>Guardian: {verificationResult.guardian_name} (ID: {verificationResult.guardian_id})</p>
                            <p>Pickup Time: {new Date(verificationResult.pickup_log_time).toLocaleString()}</p>
                            <h4>Authorized Students:</h4>
                            {verificationResult.authorized_students && verificationResult.authorized_students.length > 0 ? (
                                <ul>
                                    {verificationResult.authorized_students.map(student => (
                                        <li key={student.id}>
                                            {student.name} (ID: {student.id})
                                            {student.teacher_email && ` - Teacher: ${student.teacher_email}`}
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <p>No students associated with this guardian.</p>
                            )}
                            <p style={{ fontStyle: 'italic' }}>Teachers have been notified (simulated).</p>
                        </div>
                    ) : (
                        <p style={{ color: 'orange' }}>{verificationResult.message || "No match found."}</p>
                    )}
                </div>
            )}
        </div>
    );
};

export default Verification;