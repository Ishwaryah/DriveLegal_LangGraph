import React, { createContext, useContext } from 'react';
import { useSettings } from '../hooks/useSettings';
import type { LangCode } from '../i18n/strings';

interface LanguageContextType {
  lang: LangCode;
  setLang: (lang: LangCode) => void;
  t: (key: string, params?: Record<string, string>) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

/**
 * LanguageProvider must live inside SettingsProvider since it delegates
 * language state management to useSettings.
 */
export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const { language, setLanguage, t } = useSettings();

  return (
    <LanguageContext.Provider value={{
      lang: language as LangCode,
      setLang: setLanguage as (lang: LangCode) => void,
      t,
    }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextType {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider');
  return ctx;
}