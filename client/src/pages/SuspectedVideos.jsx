import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, PlayCircle, AlertTriangle, ShieldCheck } from 'lucide-react';
import { apiCall } from '../services/api';

const SuspectedVideos = () => {
    const [videos, setVideos] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchVideos = async () => {
            try {
                const data = await apiCall('/suspected_videos');
                setVideos(data);
            } catch (err) {
                console.error("Failed to fetch videos", err);
            } finally {
                setLoading(false);
            }
        };

        fetchVideos();
        const interval = setInterval(fetchVideos, 10000); // Poll every 10s
        return () => clearInterval(interval);
    }, []);

    const handleWatch = (video) => {
        navigate('/video-player', { state: { video } });
    };

    return (
        <div className="page-container flex-col">
            <header className="page-header">
                <button className="btn-back" onClick={() => navigate('/home')}>
                    <ArrowLeft size={20} /> Back to Hub
                </button>
                <h1><AlertTriangle className="text-danger" /> Suspected Videos Archive</h1>
            </header>

            <div className="content-scrollable">
                {loading ? (
                    <div className="loader-container"><div className="spinner-large"></div></div>
                ) : videos.length === 0 ? (
                    <div className="empty-state glass-panel">
                        <ShieldCheck size={48} className="text-success mb-2" />
                        <p>No violent incidents detected. The perimeter is secure.</p>
                    </div>
                ) : (
                    <div className="video-grid">
                        {videos.map((vid, index) => (
                            <div
                                key={vid.id}
                                className="video-card glass-panel animate-fade-in"
                                style={{ animationDelay: `${index * 0.05}s` }}
                            >
                                <div className="video-card-header">
                                    <span className={`confidence-badge ${vid.confidence > 0.85 ? 'high' : 'medium'}`}>
                                        {(vid.confidence * 100).toFixed(1)}% Match
                                    </span>
                                    <span className="camera-label">CAM: {vid.camera_id}</span>
                                </div>

                                <div className="video-card-body">
                                    <div className="timestamp-large">
                                        {new Date(vid.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                    </div>
                                    <div className="date-sub">
                                        {new Date(vid.timestamp * 1000).toLocaleDateString()}
                                    </div>
                                </div>

                                <div className="video-card-footer">
                                    <button className="btn btn-outline-primary btn-block" onClick={() => handleWatch(vid)}>
                                        <PlayCircle size={18} /> Watch Clip
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default SuspectedVideos;
