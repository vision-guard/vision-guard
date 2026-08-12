import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, MonitorPlay, AlertTriangle, Activity } from 'lucide-react';
import { apiCall } from '../services/api';

const CAMERA_BASE_URL = 'http://localhost:8000';

const LiveMonitor = () => {
    const navigate = useNavigate();
    const [streamUrl, setStreamUrl] = useState('');
    const [loading, setLoading] = useState(true);
    const [cameraError, setCameraError] = useState(false);
    const [streamReady, setStreamReady] = useState(false);

    const initStream = useCallback(async () => {
        setLoading(true);
        setCameraError(false);
        setStreamReady(false);

        try {
            // Step 1: Get the stream URL from orchestration service
            const data = await apiCall('/api/config/stream-url');
            const url = data.stream_url;

            // Step 2: Poll camera service health until it's producing frames
            let ready = false;
            for (let attempt = 0; attempt < 20; attempt++) {
                try {
                    const res = await fetch(`${CAMERA_BASE_URL}/health`);
                    if (res.ok) {
                        ready = true;
                        break;
                    }
                } catch {
                    // Camera service not reachable yet, keep trying
                }
                await new Promise(resolve => setTimeout(resolve, 1500));
            }

            if (!ready) {
                setCameraError(true);
                setLoading(false);
                return;
            }

            // Step 3: Set the stream URL — add a cache-busting param to avoid stale browser cache
            setStreamUrl(`${url}?t=${Date.now()}`);
            setStreamReady(true);
        } catch (err) {
            console.error(err);
            setCameraError(true);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        initStream();
    }, [initStream]);

    const handleImageError = () => {
        setCameraError(true);
        setStreamReady(false);
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
                                <button className="btn btn-outline-primary mt-4" onClick={initStream}>
                                    Retry Connection
                                </button>
                            </div>
                        ) : streamReady ? (
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
                        ) : null}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LiveMonitor;

