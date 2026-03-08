import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, UserPlus, ShieldPlus, ShieldAlert } from 'lucide-react';
import { apiCall } from '../services/api';
import { useTranslation } from 'react-i18next';

const UserAccessManagement = () => {
    const { t } = useTranslation();
    const [username, setUsername] = useState('');
    const [users, setUsers] = useState([]);
    const [status, setStatus] = useState({ type: '', message: '' });
    const [loading, setLoading] = useState(false);
    const [fetchLoading, setFetchLoading] = useState(true);
    const navigate = useNavigate();

    const fetchUsers = async () => {
        setFetchLoading(true);
        try {
            const data = await apiCall('/api/users/');
            setUsers(data);
        } catch (err) {
            setStatus({ type: 'error', message: 'Failed to fetch users: ' + err.message });
        } finally {
            setFetchLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, []);

    const handleAddUser = async (e) => {
        e.preventDefault();
        if (!username.trim()) return;

        setLoading(true);
        setStatus({ type: '', message: '' });

        try {
            const data = await apiCall('/api/users/add', {
                method: 'POST',
                body: JSON.stringify({ username: username.trim() }),
            });
            setStatus({ type: 'success', message: data.message });
            setUsername('');
            fetchUsers();
        } catch (err) {
            setStatus({ type: 'error', message: err.message });
        } finally {
            setLoading(false);
        }
    };

    const handleRoleUpdate = async (userId, newRole) => {
        setStatus({ type: '', message: '' });
        try {
            const data = await apiCall(`/api/users/${userId}/role`, {
                method: 'PUT',
                body: JSON.stringify({ role: newRole })
            });
            setStatus({ type: 'success', message: data.message });
            fetchUsers();
        } catch (err) {
            setStatus({ type: 'error', message: err.message });
        }
    }

    return (
        <div className="page-container flex-col">
            <header className="page-header">
                <button className="btn-back" onClick={() => navigate('/home')}>
                    <ArrowLeft size={20} /> {t('user_management.back')}
                </button>
                <h1><ShieldPlus className="text-info" /> {t('user_management.title')}</h1>
            </header>

            {status.message && (
                <div className={`alert ${status.type === 'success' ? 'alert-success' : 'alert-error'}`}>
                    {status.message}
                </div>
            )}

            <div className="management-layout" style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
                <div className="management-card glass-panel animate-fade-in flex-1" style={{ minWidth: '300px' }}>
                    <h2>{t('user_management.add_user')}</h2>
                    <p className="text-muted mb-4">
                        {t('user_management.add_desc')}
                    </p>

                    <form onSubmit={handleAddUser} className="auth-form mt-4">
                        <div className="input-group">
                            <UserPlus className="input-icon" size={20} />
                            <input
                                type="text"
                                placeholder={t('user_management.username_placeholder')}
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                required
                            />
                        </div>

                        <button type="submit" className="btn btn-info btn-block mt-4" disabled={loading}>
                            {loading ? <span className="spinner"></span> : t('user_management.add_btn')}
                        </button>
                    </form>
                </div>

                <div className="management-card glass-panel animate-fade-in flex-2" style={{ flex: '2', minWidth: '400px' }}>
                    <h2><ShieldAlert className="text-warning" /> {t('user_management.roster')}</h2>
                    {fetchLoading ? (
                        <div className="loader-container"><div className="spinner"></div></div>
                    ) : (
                        <div className="user-table-container mt-4" style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                                        <th style={{ padding: '0.75rem' }}>{t('user_management.th_username')}</th>
                                        <th style={{ padding: '0.75rem' }}>{t('user_management.th_role')}</th>
                                        <th style={{ padding: '0.75rem' }}>{t('user_management.th_actions')}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {users.map(u => (
                                        <tr key={u.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                            <td style={{ padding: '0.75rem' }}>{u.username}</td>
                                            <td style={{ padding: '0.75rem' }}>
                                                <span className={`confidence-badge ${u.role === 'ADMIN' ? 'high' : (u.role === 'VIEWER' ? 'medium' : '')}`}>
                                                    {u.role}
                                                </span>
                                            </td>
                                            <td style={{ padding: '0.75rem', display: 'flex', gap: '0.5rem' }}>
                                                {u.role !== 'VIEWER' && (
                                                    <button onClick={() => handleRoleUpdate(u.id, 'VIEWER')} className="btn btn-outline-primary" style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}>{t('user_management.set_viewer')}</button>
                                                )}
                                                {u.role !== 'ADMIN' && (
                                                    <button onClick={() => handleRoleUpdate(u.id, 'ADMIN')} className="btn btn-outline-danger" style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}>{t('user_management.set_admin')}</button>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default UserAccessManagement;
