// Configuration settings for the frontend application

const config = {
    // API configuration
    api: {
        baseUrl: process.env.REACT_APP_API_URL || 'http://127.0.0.1:5000',
    },

    // Image settings
    imageSettings: {
        webcam: {
            width: 480,
            height: 480,
            facingMode: "user" // or "environment" for rear camera
        }
    }
};

export default config;