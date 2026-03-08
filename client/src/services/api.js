export const API_BASE = "http://localhost:8001"; // Orchestration Service

export const apiCall = async (endpoint, options = {}) => {
    const defaultHeaders = {
        'Content-Type': 'application/json',
    };

    // In a real app we'd attach a JWT token here. For this demo, we'll
    // rely on passing user state or minimal auth concepts if needed.
    const userStr = localStorage.getItem('vision_user');
    if (userStr) {
        defaultHeaders['user-data'] = userStr; // Simple mock JWT header
    }

    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers,
        },
    };

    const response = await fetch(`${API_BASE}${endpoint}`, config);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || data.message || 'API Request Failed');
    }

    return data;
};
