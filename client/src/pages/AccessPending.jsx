import React from 'react';
import { ShieldAlert, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const AccessPending = () => {
    const { logout, user } = useAuth();
    const { t } = useTranslation();
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
                <h2 className="mb-2">{t('access_pending.title')}</h2>
                <div className="alert alert-warning mb-4">
                    {t('access_pending.alert_part1')}<strong>{user?.username}</strong>{t('access_pending.alert_part2')}
                </div>
                <p className="text-muted mb-4">
                    {t('access_pending.desc1')}<strong>{t('access_pending.desc2')}</strong>{t('access_pending.desc3')}
                </p>
                <button className="btn btn-outline-danger btn-block" onClick={handleLogout}>
                    <LogOut size={18} /> {t('access_pending.signout')}
                </button>
            </div>
        </div>
    );
};

export default AccessPending;
