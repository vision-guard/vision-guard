import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const ProtectedRoute = ({ children, allowedRoles }) => {
    const { user } = useAuth();
    const location = useLocation();

    if (!user) {
        // Not logged in
        return <Navigate to="/" state={{ from: location }} replace />;
    }

    if (allowedRoles && !allowedRoles.includes(user.role)) {
        // Logged in but wrong role
        if (user.role === 'UNASSIGNED') {
            if (location.pathname === '/pending') return children;
            return <Navigate to="/pending" replace />;
        }
        if (location.pathname === '/home') {
            // To absolutely prevent infinite loops if we are already at home but unauthorized
            // (Ideally this shouldn't happen if user.role is valid and allowedRoles includes it)
            return <div>Unauthorized Access. Check your role permissions.</div>;
        }
        return <Navigate to="/home" replace />;
    }

    return children;
};

export default ProtectedRoute;
