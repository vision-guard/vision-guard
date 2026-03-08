import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, UserPlus, LogIn, Mail, Phone, Lock, User } from 'lucide-react';
import { apiCall } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from '../components/LanguageSwitcher';

const LoginRegistration = () => {
    const { t } = useTranslation();
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
                setError(t('login.success'));
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
                <div className="flex justify-end w-full p-2">
                    <LanguageSwitcher />
                </div>
                <div className="auth-header">
                    <div className="logo-container">
                        <ShieldCheck size={48} className="logo-icon animate-pulse-slow" />
                    </div>
                    <h1>Vision Guard</h1>
                    <p>{isLogin ? t('login.subtitle') : t('login.register_subtitle')}</p>
                </div>

                {error && <div className={`alert ${error.includes('successful') ? 'alert-success' : 'alert-error'}`}>{error}</div>}

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="input-group">
                        <User className="input-icon" size={20} />
                        <input type="text" name="username" placeholder={t('login.username')} required value={formData.username} onChange={handleChange} />
                    </div>

                    <div className="input-group">
                        <Lock className="input-icon" size={20} />
                        <input type="password" name="password" placeholder={t('login.password')} required value={formData.password} onChange={handleChange} />
                    </div>

                    {!isLogin && (
                        <>
                            <div className="input-group animate-slide-in">
                                <Mail className="input-icon" size={20} />
                                <input type="email" name="email" placeholder={t('login.email')} value={formData.email} onChange={handleChange} />
                            </div>
                            <div className="input-group animate-slide-in" style={{ animationDelay: '0.1s' }}>
                                <Phone className="input-icon" size={20} />
                                <input type="tel" name="phone" placeholder={t('login.phone')} value={formData.phone} onChange={handleChange} />
                            </div>
                        </>
                    )}

                    <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                        {loading ? <span className="spinner"></span> : (isLogin ? <><LogIn size={20} /> {t('login.button')}</> : <><UserPlus size={20} /> {t('login.register_btn')}</>)}
                    </button>
                </form>

                <div className="auth-footer">
                    <button type="button" className="btn-link" onClick={() => { setIsLogin(!isLogin); setError(''); }}>
                        {isLogin ? t('login.switch_to_register') : t('login.switch_to_login')}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default LoginRegistration;
