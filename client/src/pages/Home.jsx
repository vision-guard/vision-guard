import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, Users, LogOut, Video, MonitorPlay } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import NotificationButton from '../components/NotificationButton';

const Home = () => {
    const navigate = useNavigate();
    const { user, logout } = useAuth();

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
                    <span>Vision Guard Hub</span>
                </div>
                <div className="header-user flex items-center gap-4">
                    <NotificationButton />
                    <span className="user-badge">{user.username} ({user.role})</span>
                    <button onClick={handleLogout} className="btn-icon" title="Logout">
                        <LogOut size={20} />
                    </button>
                </div>
            </header>

            <main className="dashboard-grid">
                <div className="dashboard-card animate-fade-in" onClick={() => navigate('/suspected-videos')}>
                    <div className="card-icon-wrapper bg-gradient-danger">
                        <Video size={32} />
                    </div>
                    <h2>Suspected Videos</h2>
                    <p>Review and analyze AI-detected violent activities captured by the surveillance network.</p>
                </div>

                <div className="dashboard-card animate-fade-in" style={{ animationDelay: '0.05s' }} onClick={() => navigate('/live-monitor')}>
                    <div className="card-icon-wrapper bg-gradient-primary">
                        <MonitorPlay size={32} />
                    </div>
                    <h2>Live Monitor</h2>
                    <p>Watch the real-time surveillance feed with active AI overlay and event tagging.</p>
                </div>

                {user?.role === 'ADMIN' && (
                    <div className="dashboard-card animate-fade-in" style={{ animationDelay: '0.1s' }} onClick={() => navigate('/access-management')}>
                        <div className="card-icon-wrapper bg-gradient-info">
                            <Users size={32} />
                        </div>
                        <h2>Access Management</h2>
                        <p>Authorize new operatives and manage system clearances across the network.</p>
                    </div>
                )}
            </main>

            <div className="system-status panel-glass">
                <h3>System Diagnostics</h3>
                <div className="status-indicators">
                    <div className="indicator">
                        <span className="dot online pulse-dot"></span> Core Algorithm: ONLINE
                    </div>
                    <div className="indicator">
                        <span className="dot online pulse-dot"></span> Video Feed: STREAMING
                    </div>
                    <div className="indicator">
                        <span className="dot online pulse-dot"></span> Database: CONNECTED
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Home;
