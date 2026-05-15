export type LangCode = 'en' | 'hi' | 'ta' | 'te' | 'kn';

export interface Language {
  code: LangCode;
  name: string;
  nativeName: string;
}

export const LANGUAGES: Language[] = [
  { code: 'en', name: 'English',  nativeName: 'English' },
  { code: 'hi', name: 'Hindi',    nativeName: 'हिंदी' },
  { code: 'ta', name: 'Tamil',    nativeName: 'தமிழ்' },
  { code: 'te', name: 'Telugu',   nativeName: 'తెలుగు' },
  { code: 'kn', name: 'Kannada',  nativeName: 'ಕನ್ನಡ' },
];

type StringTable = Record<string, Record<LangCode, string>>;

const strings: StringTable = {
  // ── Common ─────────────────────────────────────────────────────────────────
  back:   { en: 'Back',   hi: 'पीछे',       ta: 'பின்னால்',   te: 'వెనుకకు',      kn: 'ಹಿಂದೆ' },
  save:   { en: 'Save',   hi: 'सहेजें',     ta: 'சேமி',       te: 'సేవ్',         kn: 'ಉಳಿಸಿ' },
  cancel: { en: 'Cancel', hi: 'रद्द करें',  ta: 'ரத்து செய்', te: 'రద్దు చేయి',  kn: 'ರದ್ದು ಮಾಡಿ' },
  add:    { en: 'Add',    hi: 'जोड़ें',      ta: 'சேர்',       te: 'జోడించు',      kn: 'ಸೇರಿಸಿ' },
  on:     { en: 'On',     hi: 'चालू',       ta: 'ஆன்',        te: 'ఆన్',          kn: 'ಆನ್' },
  off:    { en: 'Off',    hi: 'बंद',        ta: 'ஆஃப்',       te: 'ఆఫ్',          kn: 'ಆಫ್' },

  // ── Tabs ───────────────────────────────────────────────────────────────────
  home:  { en: 'Home',  hi: 'होम',    ta: 'முகப்பு',       te: 'హోమ్',        kn: 'ಮನೆ' },
  ask:   { en: 'Ask',   hi: 'पूछें',  ta: 'கேட்க',        te: 'అడగండి',      kn: 'ಕೇಳಿ' },
  fines: { en: 'Fines', hi: 'जुर्माना', ta: 'அபராதங்கள்', te: 'జరిమానాలు',  kn: 'ದಂಡಗಳು' },
  rules: { en: 'Rules', hi: 'नियम',   ta: 'விதிகள்',      te: 'నియమాలు',    kn: 'ನಿಯಮಗಳು' },
  you:   { en: 'You',   hi: 'आप',     ta: 'நீங்கள்',      te: 'మీరు',        kn: 'ನೀವು' },

  // ── Home ───────────────────────────────────────────────────────────────────
  greeting:         { en: 'GOOD MORNING, {name}', hi: 'सुप्रभात, {name}', ta: 'காலை வணக்கம், {name}', te: 'శుభోదయం, {name}', kn: 'ಶುಭೋದಯ, {name}' },
  location_label:   { en: 'You are in',            hi: 'आप यहाँ हैं',      ta: 'நீங்கள் இருப்பது',    te: 'మీరు ఇక్కడ ఉన్నారు', kn: 'ನೀವು ಇಲ್ಲಿದ್ದೀರಿ' },
  speed:            { en: 'SPEED',                  hi: 'गति',              ta: 'வேகம்',               te: 'వేగం',               kn: 'ವೇಗ' },
  fine_zone:        { en: 'FINE ZONE',              hi: 'जुर्माना क्षेत्र', ta: 'அபராத மண்டலம்',       te: 'జరిమానా ప్రాంతం',   kn: 'ದಂಡ ವಲಯ' },
  helmet:           { en: 'HELMET',                 hi: 'हेल्मेट',          ta: 'தலைக்கவசம்',          te: 'హెల్మెట్',           kn: 'ಹೆಲ್ಮೆಟ್' },
  mandatory:        { en: 'Mandatory',              hi: 'अनिवार्य',          ta: 'கட்டாயம்',            te: 'తప్పనిసరి',          kn: 'ಕಡ್ಡಾಯ' },
  ask_title:        { en: 'Ask DriveLegal',         hi: 'DriveLegal से पूछें', ta: 'டிரைவ்லீகலிடம் கேளுங்கள்', te: 'DriveLegal ని అడగండి', kn: 'DriveLegal ಕೇಳಿ' },
  ask_subtitle:     { en: 'Plain-language Q&A',     hi: 'सरल भाषा प्रश्नोत्तर', ta: 'எளிய மொழி கேள்வி பதில்', te: 'సరళ భాషా ప్రశ్నోత్తరాలు', kn: 'ಸರಳ ಭಾಷೆ ಪ್ರಶ್ನೋತ್ತರ' },
  challan_title:    { en: 'Challan calculator',     hi: 'चालान कैलकुलेटर', ta: 'சலான் கால்குலேட்டர்', te: 'చలాన్ కాలిక్యులేటర్', kn: 'ಚಲಾನ್ ಕ್ಯಾಲ್ಕುಲೇಟರ್' },
  challan_subtitle: { en: 'Estimate fines',         hi: 'जुर्माने का अनुमान', ta: 'அபராதங்களை மதிப்பிடு', te: 'జరిమానాలను అంచనా', kn: 'ದಂಡ ಅಂದಾಜು' },
  vault_title:      { en: 'Document vault',         hi: 'दस्तावेज़ तिजोरी', ta: 'ஆவண பெட்டகம்', te: 'డాక్యుమెంట్ వాల్ట్', kn: 'ದಾಖಲೆ ಸಂಗ್ರಹ' },
  vault_subtitle:   { en: '3 documents',            hi: '3 दस्तावेज़',       ta: '3 ஆவணங்கள்',     te: '3 పత్రాలు',           kn: '3 ದಾಖಲೆಗಳು' },
  sos_title:        { en: 'Report / SOS',           hi: 'रिपोर्ट / SOS',   ta: 'அறிக்கை / SOS',  te: 'రిపోర్ట్ / SOS',      kn: 'ವರದಿ / SOS' },
  sos_subtitle:     { en: 'Roadside help',          hi: 'सड़क के किनारे सहायता', ta: 'சாலை உதவி', te: 'రోడ్డు పక్కన సహాయం', kn: 'ರಸ್ತೆ ಸಹಾಯ' },
  todays_brief:     { en: "Today's brief",          hi: 'आज का विवरण',      ta: 'இன்றைய சுருக்கம்', te: 'నేటి సంక్షిప్తం',    kn: 'ಇಂದಿನ ಸಾರಾಂಶ' },
  see_all:          { en: 'See all',                hi: 'सभी देखें',        ta: 'அனைத்தையும் பார்', te: 'అన్నీ చూడండి',       kn: 'ಎಲ್ಲ ನೋಡಿ' },

  // ── Ask screen ────────────────────────────────────────────────────────────
  assistant_name:      { en: 'DriveLegal Assistant',    hi: 'DriveLegal सहायक',     ta: 'டிரைவ்லீகல் உதவியாளர்',   te: 'DriveLegal సహాయకుడు', kn: 'DriveLegal ಸಹಾಯಕ' },
  assistant_status:    { en: 'Online · Location-aware', hi: 'ऑनलाइन · स्थान-जागरूक', ta: 'ஆன்லைன் · இருப்பிட விழிப்புணர்வு', te: 'ఆన్‌లైన్ · స్థాన-అవగాహన', kn: 'ಆನ್‌ಲೈನ್ · ಸ್ಥಾನ-ಅರಿವು' },
  input_placeholder:   { en: 'Ask about a rule, fine, or docu...', hi: 'नियम, जुर्माने या दस्तावेज़ के बारे में पूछें...', ta: 'விதி, அபராதம் அல்லது ஆவணம் பற்றி கேளுங்கள்...', te: 'నియమం, జరిమానా లేదా పత్రం గురించి అడగండి...', kn: 'ನಿಯಮ, ದಂಡ ಅಥವಾ ದಾಖಲೆ ಬಗ್ಗೆ ಕೇಳಿ...' },
  chatbot_placeholder: { en: 'Ask about traffic laws...', hi: 'यातायात नियमों के बारे में पूछें...', ta: 'போக்குவரத்து சட்டங்களைப் பற்றி கேளுங்கள்...', te: 'ట్రాఫిక్ చట్టాల గురించి అడగండి...', kn: 'ಸಂಚಾರ ನಿಯಮಗಳ ಬಗ್ಗೆ ಕೇಳಿ...' },
  show_in_english:     { en: 'EN', hi: 'EN', ta: 'EN', te: 'EN', kn: 'EN' },
  show_in_native:      { en: 'EN', hi: 'हिं', ta: 'தமி', te: 'తెలు', kn: 'ಕನ್ನ' },

  // ── Settings ──────────────────────────────────────────────────────────────
  your_profile:      { en: 'Your profile',       hi: 'आपकी प्रोफाइल',      ta: 'உங்கள் சுயவிவரம்',    te: 'మీ ప్రొఫైల్',        kn: 'ನಿಮ್ಮ ಪ್ರೊಫೈಲ್' },
  open_violations:   { en: 'Open violations',    hi: 'खुले उल्लंघन',        ta: 'திறந்த மீறல்கள்',     te: 'బహిరంగ ఉల్లంఘనలు',  kn: 'ತೆರೆದ ಉಲ್ಲಂಘನೆಗಳು' },
  outstanding_fines: { en: 'Outstanding fines',  hi: 'बकाया जुर्माना',      ta: 'நிலுவை அபராதங்கள்',   te: 'బకాయి జరిమానాలు',   kn: 'ಬಾಕಿ ದಂಡಗಳು' },
  license_points:    { en: 'License points',     hi: 'लाइसेंस अंक',         ta: 'உரிம புள்ளிகள்',      te: 'లైసెన్స్ పాయింట్లు', kn: 'ಲೈಸೆನ್ಸ್ ಪಾಯಿಂಟ್‌ಗಳು' },
  country_state:     { en: 'Country & state',    hi: 'देश और राज्य',        ta: 'நாடு மற்றும் மாநிலம்', te: 'దేశం మరియు రాష్ట్రం', kn: 'ದೇಶ ಮತ್ತು ರಾಜ್ಯ' },
  language:          { en: 'Language',            hi: 'भाषा',                ta: 'மொழி',                te: 'భాష',                kn: 'ಭಾಷೆ' },
  vehicles:          { en: 'Vehicles',            hi: 'वाहन',                ta: 'வாகனங்கள்',           te: 'వాహనాలు',            kn: 'ವಾಹನಗಳು' },
  notifications:     { en: 'Notifications',       hi: 'सूचनाएं',             ta: 'அறிவிப்புகள்',        te: 'నోటిఫికేషన్లు',     kn: 'ಅಧಿಸೂಚನೆಗಳು' },
  offline_pack:      { en: 'Offline pack',        hi: 'ऑफ़लाइन पैक',        ta: 'ஆஃப்லைன் பேக்',       te: 'ఆఫ్‌లైన్ ప్యాక్',  kn: 'ಆಫ್‌ಲೈನ್ ಪ್ಯಾಕ್' },
  privacy_data:      { en: 'Privacy & data',      hi: 'गोपनीयता और डेटा',   ta: 'தனியுரிமை மற்றும் தரவு', te: 'గోప్యత మరియు డేటా', kn: 'ಗೌಪ್ಯತೆ ಮತ್ತು ಡೇಟಾ' },
  driving_since:     { en: 'Personal · Driving since {year}', hi: 'व्यक्तिगत · {year} से ड्राइविंग', ta: 'தனிப்பட்ட · {year} முதல் ஓட்டுதல்', te: 'వ్యక్తిగత · {year} నుండి డ్రైవింగ్', kn: 'ವ್ಯಕ್ತಿಗತ · {year} ರಿಂದ ಚಾಲನೆ' },
  safe_driver:       { en: 'Safe driver',         hi: 'सुरक्षित ड्राइवर',   ta: 'பாதுகாப்பான ஓட்டுநர்', te: 'సురక్షిత డ్రైవర్',   kn: 'ಸುರಕ್ಷಿತ ಚಾಲಕ' },
  settings_title:    { en: 'Settings',            hi: 'सेटिंग्स',            ta: 'அமைப்புகள்',          te: 'సెట్టింగ్స్',        kn: 'ಸೆಟ್ಟಿಂಗ್‌ಗಳು' },
  high_contrast:     { en: 'High Contrast Mode',  hi: 'उच्च कंट्रास्ट मोड', ta: 'அதிக வேறுபாடு பயன்முறை', te: 'అధిక కాంట్రాస్ట్ మోడ్', kn: 'ಹೆಚ್ಚಿನ ವ್ಯತಿರಿಕ್ತ ಮೋಡ್' },

  // ── Fines / Calculator ────────────────────────────────────────────────────
  calculator_title:  { en: 'Challan Calculator', hi: 'चालान कैलकुलेटर',    ta: 'அபராத கணிப்பான்',   te: 'చలాన్ కాలిక్యులేటర్', kn: 'ಚಲಾನ್ ಕ್ಯಾಲ್ಕುಲೇಟರ್' },
  select_violation:  { en: 'Select Violations',  hi: 'उल्लंघन चुनें',       ta: 'மீறல்களை தேர்ந்தெடுக்கவும்', te: 'ఉల్లంఘనలు ఎంచుకోండి', kn: 'ಉಲ್ಲಂಘನೆಗಳನ್ನು ಆಯ್ಕೆ ಮಾಡಿ' },
  vehicle_type:      { en: 'Vehicle Type',       hi: 'वाहन प्रकार',         ta: 'வாகன வகை',           te: 'వాహన రకం',            kn: 'ವಾಹನ ಪ್ರಕಾರ' },
  calculate:         { en: 'Calculate Fine',     hi: 'जुर्माना गणना करें',  ta: 'அபராதம் கணக்கிடு',  te: 'జరిమానా లెక్కించు',   kn: 'ದಂಡ ಲೆಕ್ಕ ಹಾಕಿ' },
  total_fine:        { en: 'Total Fine',         hi: 'कुल जुर्माना',        ta: 'மொத்த அபராதம்',      te: 'మొత్తం జరిమానా',      kn: 'ಒಟ್ಟು ದಂಡ' },
  compound_option:   { en: 'Compounding Option', hi: 'समझौता विकल्प',       ta: 'தீர்வு விருப்பம்',   te: 'రాజీ వికల్పం',        kn: 'ರಾಜಿ ಆಯ್ಕೆ' },
  offline_badge:     { en: '🔴 Offline – Cached Data', hi: '🔴 ऑफलाइन – संग्रहित डेटा', ta: '🔴 ஆஃப்லைன் – தற்காலிக தரவு', te: '🔴 ఆఫ్‌లైన్ – కాష్ చేసిన డేటా', kn: '🔴 ಆಫ್‌ಲೈನ್ – ಸಂಗ್ರಹಿತ ಡೇಟಾ' },
  online_badge:      { en: '🟢 Online',          hi: '🟢 ऑनलाइन',           ta: '🟢 ஆன்லைன்',         te: '🟢 ఆన్‌లైన్',         kn: '🟢 ಆನ್‌ಲೈನ್' },
  home_location_card: { en: "You're in",         hi: 'आप यहाँ हैं',         ta: 'நீங்கள் இருக்கும் இடம்', te: 'మీరు ఉన్న చోటు',   kn: 'ನೀವು ಇಲ್ಲಿದ್ದೀರಿ' },
  state_province:    { en: 'State/Province',     hi: 'राज्य/प्रांत',        ta: 'மாநிலம்/மாகாணம்',   te: 'రాష్ట్రం/ప్రాంతం',  kn: 'ರಾಜ್ಯ/ಪ್ರಾಂತ' },
  first_offense:     { en: 'First Offense',      hi: 'पहला अपराध',          ta: 'முதல் குற்றம்',      te: 'మొదటి నేరం',          kn: 'ಮೊದಲ ಅಪರಾಧ' },
  repeat_offense:    { en: 'Repeat Offense',     hi: 'बार-बार का अपराध',   ta: 'மீண்டும் மீண்டும் குற்றம்', te: 'పునరావృత నేరం', kn: 'ಪುನರಾವರ್ತಿತ ಅಪರಾಧ' },
  search_violations: { en: 'Search violations...', hi: 'उल्लंघन खोजें...', ta: 'மீறல்களை தேடுங்கள்...', te: 'ఉల్లంఘనలు శోధించండి...', kn: 'ಉಲ್ಲಂಘನೆಗಳನ್ನು ಹುಡುಕಿ...' },
  calculation_result: { en: 'Calculation Result', hi: 'गणना परिणाम',       ta: 'கணக்கீட்டு முடிவு', te: 'గణన ఫలితం',           kn: 'ಲೆಕ್ಕಾಚಾರದ ಫಲಿತಾಂಶ' },
  share_summary:     { en: 'Share Summary',      hi: 'सारांश साझा करें',   ta: 'சுருக்கத்தை பகிரவும்', te: 'సారాంశాన్ని పంచుకోండి', kn: 'ಸಾರಾಂಶ ಹಂಚಿಕೊಳ್ಳಿ' },
};

export default strings;