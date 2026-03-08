import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, MonitorPlay, AlertTriangle, Activity } from 'lucide-react';
import { apiCall } from '../services/api';
import { useTranslation } from 'react-i18next';

const LiveMonitor = () => {
    const navigate = useNavigate();
    const { t } = useTranslation();
    const [streamUrl, setStreamUrl] = useState('');
    const [loading, setLoading] = useState(true);
    const [cameraError, setCameraError] = useState(false);

    useEffect(() => {
        const fetchConfig = async () => {
            try {
                const data = await apiCall('/api/config/stream-url');
                setStreamUrl(data.stream_url);
            } catch (err) {
                console.error(err);
                setCameraError(true);
            } finally {
                setLoading(false);
            }
        };

        fetchConfig();
    }, []);

    const handleImageError = () => {
        setCameraError(true);
    };

    return (
        <div className="page-container flex-col">
            <header className="page-header">
                <button className="btn-back" onClick={() => navigate('/home')}>
                    <ArrowLeft size={20} /> {t('live_monitor.back')}
                </button>
                <h1><MonitorPlay className="text-primary" /> {t('live_monitor.title')}</h1>
            </header>

            <div className="content-scrollable flex-center">
                <div className="live-monitor-wrapper panel-glass">
                    <div className="monitor-header">
                        <div className="monitor-status">
                            <span className={`dot pulse-dot ${cameraError ? 'offline' : (loading ? 'warning' : 'online')}`}></span>
                            <span>{cameraError ? t('live_monitor.offline') : (loading ? t('live_monitor.connecting') : t('live_monitor.live'))}</span>
                        </div>
                        <div className="ai-overlay-badge">
                            <Activity size={16} /> {t('live_monitor.ai_active')}
                        </div>
                    </div>

                    <div className="monitor-screen">
                        {loading && !cameraError ? (
                            <div className="loader-container h-full">
                                <div className="spinner-large"></div>
                                <p className="mt-4 text-muted">{t('live_monitor.establishing')}</p>
                            </div>
                        ) : cameraError ? (
                            <div className="error-container h-full">
                                <AlertTriangle size={64} className="text-danger mb-4" />
                                <h3>{t('live_monitor.unavailable')}</h3>
                                <p className="text-muted">{t('live_monitor.error_desc')}</p>
                                <button className="btn btn-outline-primary mt-4" onClick={() => window.location.reload()}>
                                    {t('live_monitor.retry')}
                                </button>
                            </div>
                        ) : (
                            <div className="video-feed-container">
                                <img
                                    src={streamUrl}
                                    alt={t('live_monitor.title')}
                                    className="live-video-stream"
                                    onError={handleImageError}
                                />
                                <div className="feed-overlay">
                                    {t('live_monitor.primary_sector')}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LiveMonitor;
