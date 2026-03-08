import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, Users, LogOut, Video, MonitorPlay } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from '../components/LanguageSwitcher';
import NotificationButton from '../components/NotificationButton';

const Home = () => {
    const navigate = useNavigate();
    const { user, logout } = useAuth();
    const { t } = useTranslation();

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    if (!user) {
        navigate('/');
        return null;
    }

    return (
        <div className="home-container">
            <header className="app-header">
                <div className="header-brand">
                    <ShieldAlert className="text-primary" />
                    <span>{t('dashboard.hub_title')}</span>
                </div>
                <div className="header-user flex items-center gap-4">
                    <NotificationButton />
                    <LanguageSwitcher />
                    <span className="user-badge">{user.username} ({user.role})</span>
                    <button onClick={handleLogout} className="btn-icon" title={t('nav.logout')}>
                        <LogOut size={20} />
                    </button>
                </div>
            </header>

            <main className="dashboard-grid">
                <div className="dashboard-card animate-fade-in" onClick={() => navigate('/suspected-videos')}>
                    <div className="card-icon-wrapper bg-gradient-danger">
                        <Video size={32} />
                    </div>
                    <h2>{t('dashboard.detected_incidents')}</h2>
                    <p>{t('dashboard.incident_desc')}</p>
                </div>

                <div className="dashboard-card animate-fade-in" style={{ animationDelay: '0.05s' }} onClick={() => navigate('/live-monitor')}>
                    <div className="card-icon-wrapper bg-gradient-primary">
                        <MonitorPlay size={32} />
                    </div>
                    <h2>{t('dashboard.active_cameras')}</h2>
                    <p>{t('dashboard.monitor_desc')}</p>
                </div>

                {user?.role === 'ADMIN' && (
                    <div className="dashboard-card animate-fade-in" style={{ animationDelay: '0.1s' }} onClick={() => navigate('/access-management')}>
                        <div className="card-icon-wrapper bg-gradient-info">
                            <Users size={32} />
                        </div>
                        <h2>{t('dashboard.access_title')}</h2>
                        <p>{t('dashboard.access_desc')}</p>
                    </div>
                )}
            </main>

            <div className="system-status panel-glass">
                <h3>{t('dashboard.diagnostics')}</h3>
                <div className="status-indicators">
                    <div className="indicator">
                        <span className="dot online pulse-dot"></span> {t('dashboard.algo_online')}
                    </div>
                    <div className="indicator">
                        <span className="dot online pulse-dot"></span> {t('dashboard.feed_streaming')}
                    </div>
                    <div className="indicator">
                        <span className="dot online pulse-dot"></span> {t('dashboard.db_connected')}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Home;
