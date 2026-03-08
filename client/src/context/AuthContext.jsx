import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const storedUser = localStorage.getItem('vision_user');
        if (storedUser && storedUser !== "undefined") {
            try {
                const parsedUser = JSON.parse(storedUser);
                // Force logout if legacy user object without role exists
                if (!parsedUser.role) {
                    localStorage.removeItem('vision_user');
                    setUser(null);
                } else {
                    setUser(parsedUser);
                }
            } catch (e) {
                console.error("Invalid user data in storage", e);
                localStorage.removeItem('vision_user');
                setUser(null);
            }
        }
        setLoading(false);
    }, []);

    const login = (userData) => {
        localStorage.setItem('vision_user', JSON.stringify(userData));
        setUser(userData);
    };

    const logout = () => {
        localStorage.removeItem('vision_user');
        setUser(null);
    };

    // Update user but keep same token
    const updateUser = (userData) => {
        const newUserData = { ...user, ...userData };
        localStorage.setItem('vision_user', JSON.stringify(newUserData));
        setUser(newUserData);
    }

    return (
        <AuthContext.Provider value={{ user, login, logout, updateUser, loading }}>
            {!loading && children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
