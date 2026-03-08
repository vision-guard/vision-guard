import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, ShieldAlert, MonitorPlay, Calendar, Clock } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const VideoPlayer = () => {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const location = useLocation();
    const video = location.state?.video;

    if (!video) {
        navigate('/suspected-videos');
        return null;
    }

    const dateStr = new Date(video.timestamp * 1000).toLocaleDateString();
    const timeStr = new Date(video.timestamp * 1000).toLocaleTimeString();

    return (
        <div className="page-container flex-col">
            <header className="page-header">
                <button className="btn-back" onClick={() => navigate('/suspected-videos')}>
                    <ArrowLeft size={20} /> {t('video_player.back')}
                </button>
                <h1><MonitorPlay className="header-icon" /> {t('video_player.title')}</h1>
            </header>

            <div className="player-layout">
                <div className="video-viewport panel-glass">
                    {/* The video URL should be accessible directly via Minio locally */}
                    <video
                        src={video.video_url}
                        controls
                        autoPlay
                        className="incident-player animate-fade-in"
                        type="video/webm"
                        preload="metadata"
                        onError={(e) => console.error("Video Playback Error:", e.target.error, video.video_url)}
                    >
                        {t('video_player.not_supported')}
                    </video>
                </div>

                <div className="incident-details panel-glass">
                    <h2><ShieldAlert className="text-danger" /> {t('video_player.overview')}</h2>
                    <div className="detail-row">
                        <span className="detail-label">{t('video_player.cam_seq')}</span>
                        <span className="detail-value">{video.camera_id}</span>
                    </div>
                    <div className="detail-row">
                        <span className="detail-label">{t('video_player.confidence')}</span>
                        <span className={`detail-value ${video.confidence > 0.85 ? 'text-danger' : 'text-warning'}`}>
                            {(video.confidence * 100).toFixed(2)}%
                        </span>
                    </div>
                    <div className="detail-row">
                        <span className="detail-label"><Calendar size={16} /> {t('video_player.date')}</span>
                        <span className="detail-value">{dateStr}</span>
                    </div>
                    <div className="detail-row">
                        <span className="detail-label"><Clock size={16} /> {t('video_player.time')}</span>
                        <span className="detail-value">{timeStr}</span>
                    </div>

                    <div className="action-buttons mt-4">
                        <button className="btn btn-primary btn-block">{t('video_player.confirm')}</button>
                        <button className="btn btn-outline-danger btn-block">{t('video_player.dismiss')}</button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default VideoPlayer;
