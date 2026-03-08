import React, { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';

const LanguageSwitcher = () => {
  const { t, i18n } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'he' : 'en';
    i18n.changeLanguage(newLang);
  };

  useEffect(() => {
    // Update direction when language changes
    document.documentElement.dir = i18n.language === 'he' ? 'rtl' : 'ltr';
    document.documentElement.lang = i18n.language;
  }, [i18n.language]);

  return (
    <button 
      onClick={toggleLanguage}
      className="btn-icon flex items-center justify-center transition-all duration-300 hover:text-primary"
      title={t('nav.language', 'Language')}
      style={{ width: 'auto', padding: '0 12px', borderRadius: '20px', gap: '6px', fontWeight: '600', fontSize: '14px' }}
    >
      <Globe size={18} />
      <span>{i18n.language === 'en' ? 'EN' : 'HE'}</span>
    </button>
  );
};

export default LanguageSwitcher;
