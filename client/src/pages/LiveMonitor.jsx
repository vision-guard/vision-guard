import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, MonitorPlay, AlertTriangle, Activity } from 'lucide-react';
import { apiCall } from '../services/api';

const LiveMonitor = () => {
    const navigate = useNavigate();
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
                    <ArrowLeft size={20} /> Back to Hub
                </button>
                <h1><MonitorPlay className="text-primary" /> Live Surveillance Monitor</h1>
            </header>

            <div className="content-scrollable flex-center">
                <div className="live-monitor-wrapper panel-glass">
                    <div className="monitor-header">
                        <div className="monitor-status">
                            <span className={`dot pulse-dot ${cameraError ? 'offline' : (loading ? 'warning' : 'online')}`}></span>
                            <span>{cameraError ? 'CAMERA OFFLINE' : (loading ? 'CONNECTING...' : 'LIVE FEED ACTIVE')}</span>
                        </div>
                        <div className="ai-overlay-badge">
                            <Activity size={16} /> AI Active
                        </div>
                    </div>

                    <div className="monitor-screen">
                        {loading && !cameraError ? (
                            <div className="loader-container h-full">
                                <div className="spinner-large"></div>
                                <p className="mt-4 text-muted">Establishing secure video link...</p>
                            </div>
                        ) : cameraError ? (
                            <div className="error-container h-full">
                                <AlertTriangle size={64} className="text-danger mb-4" />
                                <h3>Feed Unavailable</h3>
                                <p className="text-muted">The camera service is currently offline or unreachable. Please check the infrastructure.</p>
                                <button className="btn btn-outline-primary mt-4" onClick={() => window.location.reload()}>
                                    Retry Connection
                                </button>
                            </div>
                        ) : (
                            <div className="video-feed-container">
                                <img
                                    src={streamUrl}
                                    alt="Live Surveillance Monitor"
                                    className="live-video-stream"
                                    onError={handleImageError}
                                />
                                <div className="feed-overlay">
                                    Primary Sector - REC
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
