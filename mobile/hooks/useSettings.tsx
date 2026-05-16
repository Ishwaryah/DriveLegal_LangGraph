import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import strings from '../i18n/strings';

type Language = 'en' | 'hi' | 'ta' | 'te' | 'kn';

interface UserProfile {
  name: string;
  avatar: string;
  drivingSince: string;
}

// Translations are centralised in i18n/strings.ts (5 languages incl. Kannada).
const _PLACEHOLDER: any = {
  // Common
  'back': { en: 'Back', ta: 'பின்னால்', hi: 'पीछे', te: 'వెనుకకు' },
  'save': { en: 'Save', ta: 'சேமி', hi: 'சहेजें', te: 'సేవ్' },
  'cancel': { en: 'Cancel', ta: 'ரத்து செய்', hi: 'ரद्द करें', te: 'రద్దు చేయి' },
  'add': { en: 'Add', ta: 'சேர்', hi: 'जोड़ें', te: 'జోడించు' },
  'on': { en: 'On', ta: 'ஆன்', hi: 'चालू', te: 'ఆన్' },
  'off': { en: 'Off', ta: 'ஆஃப்', hi: 'बंद', te: 'ఆఫ్' },

  // Tabs
  'home': { en: 'Home', ta: 'முகப்பு', hi: 'होम', te: 'హోమ్' },
  'ask': { en: 'Ask', ta: 'கேட்க', hi: 'पूछें', te: 'అడగండి' },
  'fines': { en: 'Fines', ta: 'அபராதங்கள்', hi: 'जुर्माना', te: 'జరిమానాలు' },
  'rules': { en: 'Rules', ta: 'விதிகள்', hi: 'नियम', te: 'నియమాలు' },
  'you': { en: 'You', ta: 'நீங்கள்', hi: 'आप', te: 'మీరు' },

  // Home
  'greeting': { en: 'GOOD MORNING, {name}', ta: 'காலை வணக்கம், {name}', hi: 'सुप्रभात, {name}', te: 'శుభోదయం, {name}' },
  'location_label': { en: 'You are in', ta: 'நீங்கள் இருப்பது', hi: 'आप यहाँ हैं', te: 'మీరు ఇక్కడ ఉన్నారు' },
  'speed': { en: 'SPEED', ta: 'வேகம்', hi: 'गति', te: 'వేగం' },
  'fine_zone': { en: 'FINE ZONE', ta: 'அபராத மண்டலம்', hi: 'जुर्माना क्षेत्र', te: 'జరిమానా ప్రాంతం' },
  'helmet': { en: 'HELMET', ta: 'தலைக்கவசம்', hi: 'हेல்மெட்', te: 'హెల్మెట్' },
  'mandatory': { en: 'Mandatory', ta: 'கட்டாயம்', hi: 'अनिवार्य', te: 'తప్పనిసరి' },
  'ask_title': { en: 'Ask DriveLegal', ta: 'டிரைவ்லீகலிடம் கேளுங்கள்', hi: 'DriveLegal से पूछें', te: 'DriveLegal ని అడగండి' },
  'ask_subtitle': { en: 'Plain-language Q&A', ta: 'எளிய மொழி கேள்வி பதில்', hi: 'सरल भाषा प्रश्नोत्तर', te: 'సరళ భాషా ప్రశ్నోత్తరాలు' },
  'challan_title': { en: 'Challan calculator', ta: 'சலான் கால்குலேட்டர்', hi: 'चालान कैलकुलेटर', te: 'చలాన్ కాలిక్యులేటర్' },
  'challan_subtitle': { en: 'Estimate fines', ta: 'அபராதங்களை மதிப்பிடவும்', hi: 'जुर्माने का अनुमान लगाएं', te: 'జరిమానాలను అంచనా వేయండి' },
  'vault_title': { en: 'Document vault', ta: 'ஆவண பெட்டகம்', hi: 'दस्तावेज़ तिजोरी', te: 'డాక్యుమెంట్ వాల్ట్' },
  'vault_subtitle': { en: '3 documents', ta: '3 ஆவணங்கள்', hi: '3 दस्तावेज़', te: '3 పత్రాలు' },
  'sos_title': { en: 'Report / SOS', ta: 'அறிக்கை / SOS', hi: 'रिपोर्ट / SOS', te: 'రిపోర్ట్ / SOS' },
  'sos_subtitle': { en: 'Roadside help', ta: 'சாலை உதவி', hi: 'सड़क के किनारे सहायता', te: 'రోడ్డు పక్కన సహాయం' },
  'todays_brief': { en: "Today's brief", ta: 'இன்றைய சுருக்கம்', hi: 'आज का विवरण', te: 'నేటి సంక్షిప్త సమాచారం' },
  'see_all': { en: 'See all', ta: 'அனைத்தையும் பார்', hi: 'सभी देखें', te: 'అన్నీ చూడండి' },

  // Ask
  'assistant_name': { en: 'DriveLegal Assistant', ta: 'டிரைவ்லீகல் உதவியாளர்', hi: 'DriveLegal सहायक', te: 'DriveLegal సహాయకుడు' },
  'assistant_status': { en: 'Online · Location-aware', ta: 'ஆன்லைன் · இருப்பிட விழிப்புணர்வு', hi: 'ऑनलाइन · स्थान-जागरूक', te: 'ఆన్‌లైన్ · స్థాన-అవగాహన' },
  'input_placeholder': { en: 'Ask about a rule, fine, or docu...', ta: 'விதி, அபராதம் அல்லது ஆவணம் பற்றி கேளுங்கள்...', hi: 'नियम, जुर्माने या दस्तावेज़ के बारे में पूछें...', te: 'నియమం, జరిమానా లేదా పత్రం గురించి అడగండి...' },

  // Settings
  'your_profile': { en: 'Your profile', ta: 'உங்கள் சுயவிவரம்', hi: 'आपकी प्रोफाइल', te: 'మీ ప్రొఫైల్' },
  'open_violations': { en: 'Open violations', ta: 'திறந்த மீறல்கள்', hi: 'खुले उल्लंघन', te: 'బహిరంగ ఉల్లంఘనలు' },
  'outstanding_fines': { en: 'Outstanding fines', ta: 'நிலுவையில் உள்ள அபராதங்கள்', hi: 'बकाया जुर्माना', te: 'బకాయి జరిమానాలు' },
  'license_points': { en: 'License points', ta: 'உரிம புள்ளிகள்', hi: 'लाइसेंस अंक', te: 'లైసెన్స్ పాయింట్లు' },
  'country_state': { en: 'Country & state', ta: 'நாடு மற்றும் மாநிலம்', hi: 'देश और राज्य', te: 'దేశం మరియు రాష్ట్రం' },
  'language': { en: 'Language', ta: 'மொழி', hi: 'भाषा', te: 'భాష' },
  'vehicles': { en: 'Vehicles', ta: 'வாகனங்கள்', hi: 'वाहन', te: 'వాహనాలు' },
  'notifications': { en: 'Notifications', ta: 'அறிவிப்புகள்', hi: 'सूचनाएं', te: 'నోటిఫికేషన్లు' },
  'offline_pack': { en: 'Offline pack', ta: 'ஆஃப்லைன் பேக்', hi: 'ऑफ़लाइन पैक', te: 'ఆఫ్‌లైన్ ప్యాక్' },
  'privacy_data': { en: 'Privacy & data', ta: 'தனியுரிமை மற்றும் தரவு', hi: 'गोपनीयता और डेटा', te: 'గోప్యత మరియు డేటా' },
  'driving_since': { en: 'Personal · Driving since {year}', ta: 'தனிப்பட்ட · {year} முதல் ஓட்டுதல்', hi: 'व्यक्तिगत · {year} से ड्राइविंग', te: 'వ్యక్తిగత · {year} నుండి డ్రైవింగ్' },
  'safe_driver': { en: 'Safe driver', ta: 'பாதுகாப்பான ஓட்டுநர்', hi: 'सुरक्षित ड्राइवर', te: 'సురక్షిత డ్రైవర్' },
}; // _PLACEHOLDER kept only to preserve git diff readability — unused at runtime

interface SettingsContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  profile: UserProfile;
  updateProfile: (updates: Partial<UserProfile>) => void;
  notificationsEnabled: boolean;
  setNotificationsEnabled: (enabled: boolean) => void;
  selectedVehicleId: string | null;
  setSelectedVehicleId: (id: string | null) => void;
  t: (key: string, params?: Record<string, string>) => string;
  initialized: boolean;
  highContrast: boolean;
  setHighContrast: (enabled: boolean) => void;
  defaultCountry: string;
  setDefaultCountry: (code: string) => void;
  defaultVehicleType: string;
  setDefaultVehicleType: (type: string) => void;
  vehicleNumber: string;
  setVehicleNumber: (num: string) => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>('en');
  const [profile, setProfileState] = useState<UserProfile>({ name: '', avatar: 'G', drivingSince: '---' });
  const [notificationsEnabled, setNotificationsEnabledState] = useState(true);
  const [selectedVehicleId, setSelectedVehicleIdState] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);
  const [highContrastState, setHighContrastState] = useState(false);
  const [defaultCountryState, setDefaultCountryState] = useState('IN');
  const [defaultVehicleTypeState, setDefaultVehicleTypeState] = useState('2W');
  const [vehicleNumberState, setVehicleNumberState] = useState('');

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const savedLang = await AsyncStorage.getItem('user_language');
      const savedProfile = await AsyncStorage.getItem('user_profile');
      const savedNotifications = await AsyncStorage.getItem('notifications_enabled');
      const savedVehicle = await AsyncStorage.getItem('selected_vehicle_id');
      const savedHighContrast = await AsyncStorage.getItem('highContrast');
      const savedDefaultCountry = await AsyncStorage.getItem('defaultCountry');
      const savedDefaultVehicle = await AsyncStorage.getItem('defaultVehicleType');
      const savedVehicleNumber = await AsyncStorage.getItem('vehicle_number');

      const SUPPORTED: Language[] = ['en', 'hi', 'ta', 'te', 'kn'];
      if (savedLang && SUPPORTED.includes(savedLang as Language)) {
        setLanguageState(savedLang as Language);
      } else if (!savedLang) {
        // First launch: auto-detect from device locale
        try {
          const { getLocales } = await import('expo-localization');
          const deviceLang = (getLocales()[0]?.languageCode || 'en').toLowerCase();
          const match = SUPPORTED.find(l => l !== 'en' && deviceLang.startsWith(l));
          if (match) setLanguageState(match);
        } catch { /* expo-localization unavailable — stay on 'en' */ }
      }
      if (savedProfile) {
        setProfileState(JSON.parse(savedProfile));
      }
      if (savedNotifications !== null) {
        setNotificationsEnabledState(savedNotifications === 'true');
      }
      if (savedVehicle) {
        setSelectedVehicleIdState(savedVehicle);
      }
      if (savedHighContrast !== null) {
        setHighContrastState(savedHighContrast === 'true');
      }
      if (savedDefaultCountry) {
        setDefaultCountryState(savedDefaultCountry);
      }
      if (savedDefaultVehicle) {
        setDefaultVehicleTypeState(savedDefaultVehicle);
      }
      if (savedVehicleNumber) {
        setVehicleNumberState(savedVehicleNumber);
      }
    } catch (e) {
      console.error('Failed to load settings', e);
    } finally {
      setInitialized(true);
    }
  };

  const setLanguage = async (lang: Language) => {
    setLanguageState(lang);
    await AsyncStorage.setItem('user_language', lang);
  };

  const updateProfile = async (updates: Partial<UserProfile>) => {
    const newProfile = { ...profile, ...updates };
    setProfileState(newProfile);
    await AsyncStorage.setItem('user_profile', JSON.stringify(newProfile));
  };

  const setNotificationsEnabled = async (enabled: boolean) => {
    setNotificationsEnabledState(enabled);
    await AsyncStorage.setItem('notifications_enabled', enabled ? 'true' : 'false');
  };

  const setSelectedVehicleId = async (id: string | null) => {
    setSelectedVehicleIdState(id);
    if (id) {
      await AsyncStorage.setItem('selected_vehicle_id', id);
    } else {
      await AsyncStorage.removeItem('selected_vehicle_id');
    }
  };

  const setHighContrast = async (enabled: boolean) => {
    setHighContrastState(enabled);
    await AsyncStorage.setItem('highContrast', enabled ? 'true' : 'false');
  };

  const setDefaultCountry = async (code: string) => {
    setDefaultCountryState(code);
    await AsyncStorage.setItem('defaultCountry', code);
  };

  const setDefaultVehicleType = async (type: string) => {
    setDefaultVehicleTypeState(type);
    await AsyncStorage.setItem('defaultVehicleType', type);
  };

  const setVehicleNumber = async (num: string) => {
    setVehicleNumberState(num);
    await AsyncStorage.setItem('vehicle_number', num);
  };

  const t = (key: string, params?: Record<string, string>) => {
    let text = strings[key]?.[language as keyof typeof strings[string]] || strings[key]?.['en'] || key;
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        text = text.replace(`{${k}}`, v);
      });
    }
    // Handle global params like profile name
    text = text.replace('{name}', profile.name || 'User');
    return text;
  };

  return (
    <SettingsContext.Provider value={{ 
      language, setLanguage, 
      profile, updateProfile, 
      notificationsEnabled, setNotificationsEnabled,
      selectedVehicleId, setSelectedVehicleId,
      t, initialized,
      highContrast: highContrastState, setHighContrast,
      defaultCountry: defaultCountryState, setDefaultCountry,
      defaultVehicleType: defaultVehicleTypeState, setDefaultVehicleType,
      vehicleNumber: vehicleNumberState, setVehicleNumber
    }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}
