import React from 'react';
import { ShieldAlert, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Navigate } from 'react-router-dom';

const AccessPending = () => {
    const { logout, user } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        window.location.href = '/';
    };

    return (
        <div className="auth-container ambient-background">
            <div className="auth-card glass-panel text-center animate-slide-in">
                <div className="logo-container mx-auto mb-4">
                    <ShieldAlert size={48} className="text-warning" />
                </div>
                <h2 className="mb-2">Access Pending</h2>
                <div className="alert alert-warning mb-4">
                    Your account (<strong>{user?.username}</strong>) has been successfully registered but is currently awaiting administrator approval.
                </div>
                <p className="text-muted mb-4">
                    You have been assigned the default <strong>UNASSIGNED</strong> role. An administrator must upgrade your role to VIEWER or ADMIN before you can access the Vision Guard system.
                </p>
                <button className="btn btn-outline-danger btn-block" onClick={handleLogout}>
                    <LogOut size={18} /> Sign Out
                </button>
            </div>
        </div>
    );
};

export default AccessPending;
