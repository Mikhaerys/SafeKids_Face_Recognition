// Configuration settings for the frontend application

const config = {
    // API configuration
    api: {
        // Check for environment variable first, then use the current hostname with port 5000
        baseUrl: process.env.REACT_APP_API_URL ||
            `http://${window.location.hostname}:5000`,
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