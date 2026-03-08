import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import LoginRegistration from './pages/LoginRegistration';
import Home from './pages/Home';
import SuspectedVideos from './pages/SuspectedVideos';
import VideoPlayer from './pages/VideoPlayer';
import UserAccessManagement from './pages/UserAccessManagement';
import LiveMonitor from './pages/LiveMonitor';
import AccessPending from './pages/AccessPending';
import ProtectedRoute from './components/ProtectedRoute';
import { useAuth } from './context/AuthContext';
import './index.css';

const PublicRoute = ({ children }) => {
  const { user } = useAuth();
  if (user) {
    if (user.role === 'UNASSIGNED') {
      return <Navigate to="/pending" replace />;
    }
    return <Navigate to="/home" replace />;
  }
  return children;
};

function App() {
  return (
    <div className="app-root">
      <div className="ambient-background"></div>

      <Routes>
        <Route path="/" element={<PublicRoute><LoginRegistration /></PublicRoute>} />

        {/* UNASSIGNED role only hits pending */}
        <Route path="/pending" element={<AccessPending />} />

        {/* Both VIEWER and ADMIN can access these */}
        <Route path="/home" element={
          <ProtectedRoute allowedRoles={['ADMIN', 'VIEWER']}>
            <Home />
          </ProtectedRoute>
        } />
        <Route path="/suspected-videos" element={
          <ProtectedRoute allowedRoles={['ADMIN', 'VIEWER']}>
            <SuspectedVideos />
          </ProtectedRoute>
        } />
        <Route path="/video-player" element={
          <ProtectedRoute allowedRoles={['ADMIN', 'VIEWER']}>
            <VideoPlayer />
          </ProtectedRoute>
        } />
        <Route path="/live-monitor" element={
          <ProtectedRoute allowedRoles={['ADMIN', 'VIEWER']}>
            <LiveMonitor />
          </ProtectedRoute>
        } />

        {/* ADMIN exclusively */}
        <Route path="/access-management" element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <UserAccessManagement />
          </ProtectedRoute>
        } />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default App;
