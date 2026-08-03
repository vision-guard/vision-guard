import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, UserPlus, LogIn, Mail, Phone, Lock, User } from 'lucide-react';
import { apiCall } from '../services/api';
import { useAuth } from '../context/AuthContext';
const LoginRegistration = () => {
    const [isLogin, setIsLogin] = useState(true);
    const [formData, setFormData] = useState({ username: '', password: '', email: '', phone: '' });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';

        try {
            const data = await apiCall(endpoint, {
                method: 'POST',
                body: JSON.stringify(formData),
            });

            if (isLogin) {
                login(data.user);
                // Navigation is handled by ProtectedRoute/PublicRoute automatically, but we can push
                if (data.user.role === 'UNASSIGNED') {
                    navigate('/pending');
                } else {
                    navigate('/home');
                }
            } else {
                setIsLogin(true);
                setError('Registration successful! Please login.');
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card glass-panel">
                <div className="auth-header">
                    <div className="logo-container">
                        <ShieldCheck size={48} className="logo-icon animate-pulse-slow" />
                    </div>
                    <h1>Vision Guard</h1>
                    <p>{isLogin ? 'Secure access to the surveillance core' : 'Register an operative account'}</p>
                </div>

                {error && <div className={`alert ${error.includes('successful') ? 'alert-success' : 'alert-error'}`}>{error}</div>}

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="input-group">
                        <User className="input-icon" size={20} />
                        <input type="text" name="username" placeholder="Username" required value={formData.username} onChange={handleChange} />
                    </div>

                    <div className="input-group">
                        <Lock className="input-icon" size={20} />
                        <input type="password" name="password" placeholder="Password" required value={formData.password} onChange={handleChange} />
                    </div>

                    {!isLogin && (
                        <>
                            <div className="input-group animate-slide-in">
                                <Mail className="input-icon" size={20} />
                                <input type="email" name="email" placeholder="Email Address (Optional)" value={formData.email} onChange={handleChange} />
                            </div>
                            <div className="input-group animate-slide-in" style={{ animationDelay: '0.1s' }}>
                                <Phone className="input-icon" size={20} />
                                <input type="tel" name="phone" placeholder="Phone Number (Optional)" value={formData.phone} onChange={handleChange} />
                            </div>
                        </>
                    )}

                    <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                        {loading ? <span className="spinner"></span> : (isLogin ? <><LogIn size={20} /> Login to System</> : <><UserPlus size={20} /> Register Account</>)}
                    </button>
                </form>

                <div className="auth-footer">
                    <button type="button" className="btn-link" onClick={() => { setIsLogin(!isLogin); setError(''); }}>
                        {isLogin ? "Don't have clearance? Request Access" : 'Already an operative? Return to Login'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default LoginRegistration;
