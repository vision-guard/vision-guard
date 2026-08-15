import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, MonitorPlay, AlertTriangle, Activity, Camera, Wifi, WifiOff } from 'lucide-react';
import { apiCall } from '../services/api';

const CameraFeed = ({ camera, index }) => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [streamUrl, setStreamUrl] = useState('');
    const imgRef = useRef(null);
    const lastFrameTimeRef = useRef(Date.now());
    const watchdogRef = useRef(null);
    const retryTimeoutRef = useRef(null);

    const initFeed = useCallback(async () => {
        setLoading(true);
        setError(false);

        // Clear any pending retry
        if (retryTimeoutRef.current) {
            clearTimeout(retryTimeoutRef.current);
            retryTimeoutRef.current = null;
        }

        try {
            // Poll camera-specific health until ready
            let ready = false;
            for (let attempt = 0; attempt < 15; attempt++) {
                try {
                    const res = await fetch(`/health/${camera.camera_id}`);
                    if (res.ok) {
                        ready = true;
                        break;
                    }
                } catch {
                    // Camera not ready yet
                }
                await new Promise(resolve => setTimeout(resolve, 1500));
            }

            if (!ready) {
                setError(true);
                setLoading(false);
                // Auto-retry after 5 seconds
                retryTimeoutRef.current = setTimeout(initFeed, 5000);
                return;
            }

            // Bust the browser cache with a fresh timestamp so the browser
            // opens a brand-new MJPEG connection.
            setStreamUrl(`${camera.stream_url}?t=${Date.now()}`);
            lastFrameTimeRef.current = Date.now();
        } catch (err) {
            console.error(err);
            setError(true);
            retryTimeoutRef.current = setTimeout(initFeed, 5000);
        } finally {
            setLoading(false);
        }
    }, [camera]);

    useEffect(() => {
        initFeed();

        return () => {
            if (retryTimeoutRef.current) {
                clearTimeout(retryTimeoutRef.current);
            }
        };
    }, [initFeed]);

    // Cleanup: force-close the MJPEG connection when this component unmounts.
    // We use a separate effect depending on streamUrl so that imgRef.current
    // has been attached to the DOM node before we capture it.
    useEffect(() => {
        const img = imgRef.current;
        return () => {
            if (img) {
                // Clearing src explicitly aborts the multipart/x-mixed-replace
                // connection and frees up the Chrome 6-connection limit per host.
                img.src = '';
                img.removeAttribute('src');
            }
        };
    }, [streamUrl]);

    // Watchdog: detect when the MJPEG stream silently stalls (no new frames
    // arriving even though the <img> hasn't fired an onerror). This covers
    // edge-cases like the TCP connection staying alive but the server no longer
    // sending new JPEG boundaries.
    useEffect(() => {
        if (!streamUrl || error) return;

        watchdogRef.current = setInterval(() => {
            const elapsed = Date.now() - lastFrameTimeRef.current;
            // If no frame has arrived for 15 seconds, force a reconnect
            if (elapsed > 15000) {
                console.warn(`[${camera.camera_id}] Stream stale for ${elapsed}ms – reconnecting`);
                // Kill the current connection
                if (imgRef.current) {
                    imgRef.current.src = '';
                    imgRef.current.removeAttribute('src');
                }
                initFeed();
            }
        }, 5000);

        return () => {
            if (watchdogRef.current) {
                clearInterval(watchdogRef.current);
            }
        };
    }, [streamUrl, error, camera.camera_id, initFeed]);

    const handleImageError = () => {
        setError(true);
        // Auto-reconnect after a short delay
        retryTimeoutRef.current = setTimeout(initFeed, 3000);
    };

    const handleImageLoad = () => {
        setLoading(false);
        setError(false);
        lastFrameTimeRef.current = Date.now();
    };

    // Determine label styling based on camera type
    const isViolentCam = camera.camera_id === 'cam_1';

    return (
        <div
            className={`camera-cell panel-glass animate-fade-in`}
            style={{ animationDelay: `${index * 0.1}s` }}
        >
            <div className="camera-cell-header">
                <div className="camera-cell-label">
                    <Camera size={14} />
                    <span>{camera.camera_id.replace('_', ' ').toUpperCase()}</span>
                </div>
                <div className="camera-cell-status">
                    {error ? (
                        <><WifiOff size={12} /><span className="dot offline"></span></>
                    ) : loading ? (
                        <><Wifi size={12} className="text-warning" /><span className="dot warning"></span></>
                    ) : (
                        <><Wifi size={12} className="text-success" /><span className="dot online"></span></>
                    )}
                </div>
            </div>

            <div className="camera-cell-viewport">
                {loading && !error ? (
                    <div className="camera-cell-loader">
                        <div className="spinner"></div>
                        <p className="text-muted mt-2" style={{ fontSize: '0.75rem' }}>Connecting...</p>
                    </div>
                ) : error ? (
                    <div className="camera-cell-error">
                        <AlertTriangle size={28} className="text-danger" />
                        <p className="text-muted" style={{ fontSize: '0.75rem', marginTop: '0.5rem' }}>Reconnecting...</p>
                        <button className="btn-retry" onClick={initFeed}>Retry Now</button>
                    </div>
                ) : streamUrl ? (
                    <>
                        <img
                            ref={imgRef}
                            src={streamUrl}
                            alt={`${camera.camera_id} feed`}
                            className="camera-stream"
                            onError={handleImageError}
                            onLoad={handleImageLoad}
                        />
                        <div className={`camera-cell-overlay ${isViolentCam ? 'overlay-alert' : ''}`}>
                            <span className="rec-dot"></span> REC
                        </div>
                        <div className="camera-cell-id-badge">
                            {camera.camera_id.replace('_', ' ').toUpperCase()}
                        </div>
                    </>
                ) : null}
            </div>
        </div>
    );
};

const LiveMonitor = () => {
    const navigate = useNavigate();
    const [cameras, setCameras] = useState([]);
    const [loading, setLoading] = useState(true);
    const [fetchError, setFetchError] = useState(false);

    useEffect(() => {
        const fetchCameras = async () => {
            try {
                const data = await apiCall('/api/config/stream-url');
                setCameras(data.cameras || []);
            } catch (err) {
                console.error('Failed to fetch camera config:', err);
                setFetchError(true);
            } finally {
                setLoading(false);
            }
        };
        fetchCameras();
    }, []);

    return (
        <div className="page-container flex-col">
            <header className="page-header">
                <button className="btn-back" onClick={() => navigate('/home')}>
                    <ArrowLeft size={20} /> Back to Hub
                </button>
                <h1><MonitorPlay className="text-primary" /> Live Surveillance Monitor</h1>
            </header>

            <div className="monitor-toolbar">
                <div className="monitor-status">
                    <span className={`dot pulse-dot ${fetchError ? 'offline' : (loading ? 'warning' : 'online')}`}></span>
                    <span>{fetchError ? 'CONNECTION ERROR' : (loading ? 'LOADING CAMERAS...' : `${cameras.length} CAMERAS ACTIVE`)}</span>
                </div>
                <div className="ai-overlay-badge">
                    <Activity size={16} /> AI Multi-Stream Active
                </div>
            </div>

            <div className="content-scrollable">
                {loading ? (
                    <div className="loader-container">
                        <div className="spinner-large"></div>
                        <p className="mt-4 text-muted">Initializing camera grid...</p>
                    </div>
                ) : fetchError ? (
                    <div className="error-container">
                        <AlertTriangle size={64} className="text-danger mb-4" />
                        <h3>Unable to Load Cameras</h3>
                        <p className="text-muted">Could not retrieve camera configuration from the server.</p>
                        <button className="btn btn-outline-primary mt-4" onClick={() => window.location.reload()}>Retry</button>
                    </div>
                ) : (
                    <div className="camera-grid">
                        {cameras.map((cam, idx) => (
                            <CameraFeed key={cam.camera_id} camera={cam} index={idx} />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default LiveMonitor;
