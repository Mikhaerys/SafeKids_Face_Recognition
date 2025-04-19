import React, { useState, useRef, useCallback } from 'react';
import Webcam from 'react-webcam';
import axios from 'axios';
import config from './config';

const Verification = () => {
    const webcamRef = useRef(null);
    const [imgSrc, setImgSrc] = useState(null);
    const [verificationResult, setVerificationResult] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    // Use videoConstraints from config
    const videoConstraints = config.imageSettings.webcam;

    // Function to convert base64 image to Blob
    const dataURLtoBlob = (dataurl) => {
        if (!dataurl) return null;
        try {
            const arr = dataurl.split(',');
            if (arr.length < 2) return null;
            const mimeMatch = arr[0].match(/:(.*?);/);
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
    }, [webcamRef]);

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
        formData.append('image', imageBlob, 'capture.jpg');

        setLoading(true);
        setError('');
        setVerificationResult(null);

        try {
            // Use API URL from config
            const response = await axios.post(`${config.api.baseUrl}/verify_pickup`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });
            setVerificationResult(response.data);
        } catch (err) {
            console.error("Verification API error:", err);
            if (err.response) {
                setError(err.response.data.error || `Verification failed: ${err.response.statusText}`);
            } else if (err.request) {
                setError("Verification failed: Could not connect to the server.");
            } else {
                setError(`Verification failed: ${err.message}`);
            }
            setVerificationResult(null);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="verification-container">
            <h2>Guardian Verification</h2>
            <div className="webcam-capture-section">
                <div className="webcam-container">
                    <Webcam
                        audio={false}
                        ref={webcamRef}
                        screenshotFormat="image/jpeg"
                        videoConstraints={videoConstraints}
                    />
                    <button onClick={capture} disabled={loading}>Capture Photo</button>
                </div>
                {imgSrc && (
                    <div className="preview-container">
                        <h3>Captured Image:</h3>
                        <img src={imgSrc} alt="Captured guardian" />
                        <button onClick={handleVerify} disabled={loading}>
                            {loading ? 'Verifying...' : 'Verify Identity'}
                        </button>
                    </div>
                )}
            </div>

            {error && <p className="error-message">Error: {error}</p>}

            {verificationResult && (
                <div className="verification-result">
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