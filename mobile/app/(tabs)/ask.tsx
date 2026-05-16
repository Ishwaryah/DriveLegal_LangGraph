import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Platform,
  Animated,
  KeyboardAvoidingView,
  SafeAreaView,
  Alert,
  useWindowDimensions
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery } from '../../hooks/useQuery';
import { StatusBar } from 'expo-status-bar';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useHistory } from '../../hooks/useHistory';
import { useSettings } from '../../hooks/useSettings';
import { API_BASE } from '../../config/api';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import * as Location from 'expo-location';
import { useGeoFineAlert } from '../../hooks/useGeoFineAlert';
const localRules = require('../../assets/seed/rules.json');

export default function DriveLegalAssistant() {
  const { q, sid, new: isNew } = useLocalSearchParams<{ q: string, sid: string, new: string }>();
  const { addSession, sessions } = useHistory();
  const { t, highContrast, profile, language } = useSettings();
  const router = useRouter();
  const { isOffline, countryCode, locationName, coords } = useGeoFineAlert();
  const { width: windowWidth } = useWindowDimensions();
  const width = Math.min(windowWidth, 500);
  const fontScale = width / 375;
  const fs = (size: number) => size * fontScale;

  const [selectedCountry, setSelectedCountry] = useState(countryCode || 'IN');

  // Country keyword detector — mirrors backend country_detector.py
  const detectCountryFromText = (text: string): string | null => {
    const lower = ' ' + text.toLowerCase() + ' ';
    if (lower.includes('uae') || lower.includes('dubai') || lower.includes('abu dhabi') || lower.includes('emirates')) return 'AE';
    if (lower.includes('singapore') || lower.includes(' sg ')) return 'SG';
    if (lower.includes('united kingdom') || lower.includes('britain') || lower.includes('london') || lower.includes(' uk ')) return 'GB';
    return null;
  };

  const [queryText, setQueryText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isAttachMenuOpen, setIsAttachMenuOpen] = useState(false);
  const attachMenuAnim = useRef(new Animated.Value(0)).current;
  
  const scrollRef = useRef<ScrollView>(null);
  const lastQueryRef = useRef<string>('');
  
  interface ChatMessage {
    id: string;
    sender: 'user' | 'ai';
    text: string;
    textEn?: string;        // English version when backend auto-detected a different language
    detectedLang?: string;  // ISO code returned by the multilingual endpoint
    suggestions?: string[];
    source?: string;
  }

  // Global toggle: show native-language response vs. English fallback
  const [showEnglish, setShowEnglish] = useState(false);

  const initialMessage: ChatMessage = {
    id: '1',
    sender: 'ai',
    text: `Hi ${profile.name} 👋 I'm your DriveLegal assistant. Ask anything about traffic rules, fines, or paperwork — in plain language.`,
    suggestions: [
      "What's the fine?",
      "Are there any exceptions?",
      "Where is it allowed?"
    ]
  };

  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([initialMessage]);
  const { data, isLoading, error, submitQuery } = useQuery();

  useEffect(() => {
    if (isNew === 'true') {
      setChatHistory([initialMessage]);
      router.setParams({ new: '' });
      return;
    }

    if (sid) {
      const session = sessions.find(s => s.id === sid);
      if (session) {
        setChatHistory([
          initialMessage,
          { id: 'u' + session.id, sender: 'user', text: session.query },
          { id: 'a' + session.id, sender: 'ai', text: session.response }
        ]);
        setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
      }
    } else if (q) {
      handleSend(q);
    }
  }, [q, sid, isNew]); 

  const handleSend = async (textOverride?: string) => {
    const text = textOverride || queryText;
    if (!text.trim()) return;

    lastQueryRef.current = text;

    // Auto-detect country from query text and switch selector if found
    const detectedCountry = detectCountryFromText(text);
    if (detectedCountry && detectedCountry !== selectedCountry) {
      setSelectedCountry(detectedCountry);
    }
    const effectiveCountry = detectedCountry || selectedCountry;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: text,
    };

    setChatHistory(prev => [...prev, userMessage]);
    setQueryText('');

    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);

    // Offline fallback — keyword search against local rules.json
    if (isOffline) {
      setTimeout(() => {
        const keywords = text.toLowerCase().split(' ');
        let foundRule = null;
        for (const rule of localRules) {
          if (keywords.some(k => k.length > 3 && (rule.title.toLowerCase().includes(k) || rule.description.toLowerCase().includes(k)))) {
            foundRule = rule;
            break;
          }
        }

        const locationLabel = locationName ? `Using last known: ${locationName}` : 'offline';
        const respText = foundRule
          ? `⚠️ Limited mode — ${locationLabel}\n\n${foundRule.description}`
          : `⚠️ Limited mode — ${locationLabel}\n\nSorry, I couldn't find offline information matching your query. Connect to the internet for full results.`;

        const aiResponse: ChatMessage = {
          id: (Date.now() + 1).toString(),
          sender: 'ai',
          text: respText,
          source: foundRule ? foundRule.section : 'Local Database',
        };
        addSession(text, respText);
        setChatHistory(prev => [...prev, aiResponse]);
        setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
      }, 1000);
      return;
    }

    // Online: call multilingual endpoint
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000);
      const resp = await fetch(`${API_BASE}/api/v1/chat/multilingual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, country: effectiveCountry, preferred_lang: language, gps: coords }),
        signal: controller.signal as any,
      });
      clearTimeout(timeoutId);
      if (resp.ok) {
        const result = await resp.json();
        const nativeText   = result.response    || result.text || 'No response.';
        const englishText  = result.response_en || nativeText;
        const detectedLang = result.detected_language || 'en';
        const sectionRef   = result.fine?.section_ref || result.rule?.section;
        const aiResponse: ChatMessage = {
          id: (Date.now() + 1).toString(),
          sender: 'ai',
          text: nativeText,
          textEn: detectedLang !== 'en' ? englishText : undefined,
          detectedLang,
          source: sectionRef ? `${sectionRef}, MV Act` : 'Traffic Rules Database',
        };
        addSession(text, nativeText);
        lastQueryRef.current = '';
        setChatHistory(prev => [...prev, aiResponse]);
        setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
        return;
      }
    } catch (_) { /* fall through to legacy endpoint */ }

    // Fallback to legacy /query endpoint
    await submitQuery(text, coords, effectiveCountry);
  };

  // Handle legacy /query responses (network fallback path only)
  useEffect(() => {
    if (data) {
      const respText = data.text || data.response || 'I found some information regarding your query.';
      const aiResponse: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: respText,
        source: data.fine?.section_ref ? `Section ${data.fine.section_ref}` : 'Traffic Rules Database',
      };
      if (lastQueryRef.current) { addSession(lastQueryRef.current, respText); lastQueryRef.current = ''; }
      setChatHistory(prev => [...prev, aiResponse]);
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
    } else if (error) {
      const errorResponse: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: `Sorry, I couldn't find information for that. ${error}`,
      };
      setChatHistory(prev => [...prev, errorResponse]);
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
    }
  }, [data, error]);

  const renderFormattedText = (text: string, isUser: boolean) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <Text key={i} style={[
          isUser ? styles.userText : styles.aiText, 
          {fontWeight: 'bold', fontSize: fs(15), color: isUser || highContrast ? '#fff' : '#1c1c1c'}
        ]}>{part.slice(2, -2)}</Text>;
      }
      return <Text key={i} style={[
        isUser ? styles.userText : styles.aiText, 
        {fontSize: fs(15), color: isUser || highContrast ? '#fff' : '#1c1c1c'}
      ]}>{part}</Text>;
    });
  };

  const bg = highContrast ? '#000' : '#FAF8F5';
  const textPrimary = highContrast ? '#FFF' : '#1c1c1c';
  const textSecondary = highContrast ? '#AAA' : '#9ca3af';
  const accent = highContrast ? '#FFD700' : '#d97706';
  const borderStyle = highContrast ? { borderWidth: 2, borderColor: '#FFF' } : {};

  const toggleAttachMenu = () => {
    const toValue = isAttachMenuOpen ? 0 : 1;
    setIsAttachMenuOpen(!isAttachMenuOpen);
    Animated.spring(attachMenuAnim, {
      toValue,
      useNativeDriver: true,
      tension: 50,
      friction: 7
    }).start();
  };

  const handlePickImage = async () => {
    toggleAttachMenu();
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 1,
    });
    if (!result.canceled) {
      Alert.alert("Success", "Image uploaded for analysis.");
    }
  };

  const handlePickDocument = async () => {
    toggleAttachMenu();
    const result = await DocumentPicker.getDocumentAsync({
      type: "*/*",
    });
    if (!result.canceled) {
      Alert.alert("Success", "Document uploaded for analysis.");
    }
  };

  const handleVoiceInput = () => {
    toggleAttachMenu();
    setIsListening(true);
    setTimeout(() => {
      setIsListening(false);
      Alert.alert("Voice Input", "Listening for your query...");
    }, 2000);
  };

  const handleShareLocation = async () => {
    toggleAttachMenu();
    let { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert("Permission Denied", "Location access is required.");
      return;
    }
    let location = await Location.getCurrentPositionAsync({});
    handleSend(`I am at ${location.coords.latitude}, ${location.coords.longitude}. What rules apply here?`);
  };

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: bg }]}>
      <StatusBar style={highContrast ? "light" : "dark"} />
      
      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={[styles.container, { backgroundColor: bg }]}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
      >
        {/* Header */}
        <View style={[styles.header, borderStyle, highContrast && {backgroundColor: '#000'}]}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton} accessibilityLabel="Back" accessibilityHint="Returns to previous screen">
            <Ionicons name="arrow-back" size={fs(24)} color={textPrimary} />
          </TouchableOpacity>
          
          <View style={styles.headerTitleContainer}>
            <View style={[styles.assistantIcon, highContrast && {backgroundColor: accent}]}>
              <MaterialCommunityIcons name={"sparkles" as any} size={fs(18)} color={highContrast ? '#000' : "#fff"} />
            </View>
            <View>
              <Text style={[styles.headerTitle, { color: textPrimary, fontSize: fs(16) }]}>{t('assistant_name')}</Text>
              <View style={styles.statusRow}>
                <View style={[styles.statusDot, isOffline && { backgroundColor: '#f59e0b' }]} />
                <Text style={[styles.statusText, { fontSize: fs(11), color: isOffline ? '#f59e0b' : '#10b981' }]}>
                  {isOffline
                    ? (locationName ? `Last known: ${locationName}` : 'Offline')
                    : t('assistant_status')}
                </Text>
              </View>
            </View>
          </View>
          
          <TouchableOpacity style={styles.translateButton} onPress={() => router.push('/(tabs)/settings')} accessibilityLabel="Translate" accessibilityHint="Opens language settings">
            <MaterialCommunityIcons name="translate" size={fs(22)} color={textPrimary} />
          </TouchableOpacity>
        </View>

        {/* Country Selector */}
        <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 8, paddingVertical: 10, backgroundColor: bg }}>
          {[
            { c: 'IN', e: '🇮🇳' },
            { c: 'AE', e: '🇦🇪' },
            { c: 'SG', e: '🇸🇬' },
            { c: 'GB', e: '🇬🇧' }
          ].map(country => (
            <TouchableOpacity 
              key={country.c}
              onPress={() => setSelectedCountry(country.c)}
              style={[
                { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16, borderWidth: 1, borderColor: '#e5e7eb' },
                selectedCountry === country.c && { backgroundColor: accent, borderColor: accent },
                borderStyle, highContrast && {backgroundColor: selectedCountry === country.c ? accent : '#000'}
              ]}
              accessibilityLabel={`Select ${country.c}`}
              accessibilityHint="Changes the selected country context"
            >
              <Text style={{ fontSize: fs(16) }}>{country.e}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Chat Area */}
        <ScrollView 
          ref={scrollRef}
          style={[styles.chatArea, { backgroundColor: bg }]}
          contentContainerStyle={styles.chatContent}
        >
          <Text style={[styles.dateDivider, {fontSize: fs(11)}]}>Today</Text>
          
          {chatHistory.map((msg, index) => (
            <View key={msg.id} style={[
              styles.messageWrapper,
              msg.sender === 'user' ? styles.userWrapper : styles.aiWrapper
            ]}>
              {msg.sender === 'ai' && (
                <View style={[styles.aiAvatar, highContrast && {backgroundColor: accent}]}>
                  <MaterialCommunityIcons name={"sparkles" as any} size={fs(14)} color={highContrast ? '#000' : "#d97706"} />
                </View>
              )}
              
              <View style={styles.bubbleContainer}>
                {msg.sender === 'ai' && msg.source && (
                  <View style={[styles.sourceTag, highContrast && {backgroundColor: '#333'}]}>
                    <Ionicons name="location" size={fs(12)} color={accent} />
                    <Text style={[styles.sourceTagText, { color: accent, fontSize: fs(10) }]}>{msg.source}</Text>
                  </View>
                )}
                
                <View style={[
                  styles.messageBubble,
                  msg.sender === 'user' ? styles.userBubble : styles.aiBubble,
                  borderStyle, highContrast && {backgroundColor: msg.sender === 'user' ? '#333' : '#000'}
                ]}>
                  {renderFormattedText(showEnglish && msg.textEn ? msg.textEn : msg.text, msg.sender === 'user')}
                </View>

                {msg.sender === 'ai' && msg.textEn && msg.detectedLang && msg.detectedLang !== 'en' && (
                  <View style={styles.langToggleRow}>
                    <TouchableOpacity
                      onPress={() => setShowEnglish(false)}
                      style={[styles.langToggleBtn, !showEnglish && styles.langToggleBtnActive]}
                      accessibilityLabel="Show in original language"
                    >
                      <Text style={[styles.langToggleText, !showEnglish && styles.langToggleTextActive]}>
                        {t('show_in_native')}
                      </Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      onPress={() => setShowEnglish(true)}
                      style={[styles.langToggleBtn, showEnglish && styles.langToggleBtnActive]}
                      accessibilityLabel="Show in English"
                    >
                      <Text style={[styles.langToggleText, showEnglish && styles.langToggleTextActive]}>EN</Text>
                    </TouchableOpacity>
                  </View>
                )}

                {msg.sender === 'ai' && index === chatHistory.length - 1 && msg.suggestions && (
                  <View style={styles.suggestionsRow}>
                    {msg.suggestions.map((s, i) => (
                      <TouchableOpacity 
                        key={i} 
                        style={[styles.suggestionChip, borderStyle, highContrast && {backgroundColor: '#000'}]} 
                        onPress={() => handleSend(s)}
                        accessibilityLabel={s}
                        accessibilityHint="Sends this suggested message"
                      >
                        <Text style={[styles.suggestionText, { color: textPrimary, fontSize: fs(13) }]}>{s}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                )}
              </View>
            </View>
          ))}
          
          {isLoading && (
            <View style={[styles.loadingWrapper, { flexDirection: 'row', alignItems: 'center' }]}>
              <View style={[styles.aiAvatar, highContrast && {backgroundColor: accent}]}>
                <MaterialCommunityIcons name={"sparkles" as any} size={fs(14)} color={highContrast ? '#000' : "#d97706"} />
              </View>
              <View style={[styles.messageBubble, styles.aiBubble, borderStyle, highContrast && {backgroundColor: '#000'}]}>
                <ActivityIndicator size="small" color={accent} />
              </View>
            </View>
          )}
        </ScrollView>

        {/* Attachment Menu */}
        <Animated.View style={[
          styles.attachMenu,
          {
            transform: [{
              translateY: attachMenuAnim.interpolate({
                inputRange: [0, 1],
                outputRange: [200, 0]
              })
            }],
            opacity: attachMenuAnim
          }
        ]}>
          <View style={styles.attachRow}>
            <TouchableOpacity style={styles.attachItem} onPress={handlePickImage} accessibilityLabel="Attach Image" accessibilityHint="Opens photo library">
              <View style={[styles.attachIcon, { backgroundColor: '#E0F2FE' }]}>
                <Ionicons name="image" size={fs(24)} color="#0369A1" />
              </View>
              <Text style={[styles.attachLabel, {fontSize: fs(12)}]}>Image</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.attachItem} onPress={handlePickDocument} accessibilityLabel="Attach Document" accessibilityHint="Opens file picker">
              <View style={[styles.attachIcon, { backgroundColor: '#DCFCE7' }]}>
                <Ionicons name="document-text" size={fs(24)} color="#15803D" />
              </View>
              <Text style={[styles.attachLabel, {fontSize: fs(12)}]}>Doc</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.attachItem} onPress={handleVoiceInput} accessibilityLabel="Voice Input" accessibilityHint="Starts voice recognition">
              <View style={[styles.attachIcon, { backgroundColor: '#FEF3C7' }]}>
                <Ionicons name="mic" size={fs(24)} color="#B45309" />
              </View>
              <Text style={[styles.attachLabel, {fontSize: fs(12)}]}>Voice</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.attachItem} onPress={handleShareLocation} accessibilityLabel="Share Location" accessibilityHint="Sends your current location">
              <View style={[styles.attachIcon, { backgroundColor: '#F3F4F6' }]}>
                <Ionicons name="location" size={fs(24)} color="#4B5563" />
              </View>
              <Text style={[styles.attachLabel, {fontSize: fs(12)}]}>Location</Text>
            </TouchableOpacity>
          </View>
        </Animated.View>

        {/* Input Area */}
        <View style={[styles.inputContainer, { backgroundColor: bg }]}>
          <View style={[styles.inputWrapper, borderStyle, highContrast && {backgroundColor: '#000'}]}>
            <TouchableOpacity style={styles.attachButton} onPress={toggleAttachMenu} accessibilityLabel="Toggle Attachment Menu" accessibilityHint="Opens or closes the attachment menu">
              <Animated.View style={{ transform: [{ rotate: attachMenuAnim.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '45deg'] }) }] }}>
                <Ionicons name="add" size={fs(24)} color={isAttachMenuOpen ? accent : "#6b7280"} />
              </Animated.View>
            </TouchableOpacity>
            
            <TextInput
              style={[
                styles.input,
                { fontSize: fs(15), color: textPrimary },
                Platform.OS === 'web' && { outlineStyle: 'none' } as any
              ]}
              placeholder={t('input_placeholder')}
              placeholderTextColor={textSecondary}
              value={queryText}
              onChangeText={setQueryText}
              onSubmitEditing={() => handleSend()}
              selectionColor={accent}
              onFocus={() => isAttachMenuOpen && toggleAttachMenu()}
              accessibilityLabel="Chat input field"
            />
            
            <TouchableOpacity style={styles.micButton} onPress={handleVoiceInput} accessibilityLabel="Microphone" accessibilityHint="Starts voice input">
              <Ionicons name="mic-outline" size={fs(24)} color={isListening ? accent : "#6b7280"} />
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={[styles.sendButton, !queryText.trim() && styles.sendButtonDisabled, highContrast && {backgroundColor: accent}]}
              onPress={() => handleSend()}
              disabled={!queryText.trim() && !isLoading}
              accessibilityLabel="Send Message"
              accessibilityHint="Sends the current text to the assistant"
            >
              <Ionicons name="send" size={fs(18)} color={highContrast ? '#000' : "#fff"} />
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#FAF8F5',
  },
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f0ea',
    backgroundColor: '#fff',
  },
  backButton: {
    padding: 4,
  },
  headerTitleContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 12,
  },
  assistantIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#d97706',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1c1c1c',
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#10b981',
    marginRight: 4,
  },
  statusText: {
    fontSize: 11,
    color: '#10b981',
    fontWeight: '500',
  },
  translateButton: {
    padding: 4,
  },
  chatArea: {
    flex: 1,
  },
  chatContent: {
    padding: 16,
    paddingBottom: 32,
  },
  dateDivider: {
    textAlign: 'center',
    fontSize: 11,
    fontWeight: '700',
    color: '#9ca3af',
    textTransform: 'uppercase',
    marginBottom: 24,
    backgroundColor: '#f3f0ea',
    alignSelf: 'center',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  messageWrapper: {
    flexDirection: 'row',
    marginBottom: 24,
    maxWidth: '85%',
  },
  userWrapper: {
    alignSelf: 'flex-end',
    flexDirection: 'row-reverse',
  },
  aiWrapper: {
    alignSelf: 'flex-start',
  },
  aiAvatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#fef3c7',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
  },
  bubbleContainer: {
    flex: 1,
  },
  sourceTag: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
    backgroundColor: '#fef3c7',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    alignSelf: 'flex-start',
  },
  sourceTagText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#b45309',
    marginLeft: 4,
  },
  messageBubble: {
    padding: 14,
    borderRadius: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  aiBubble: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 4,
  },
  userBubble: {
    backgroundColor: '#1c1c1c',
    borderTopRightRadius: 4,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 22,
  },
  aiText: {
    color: '#1c1c1c',
  },
  userText: {
    color: '#fff',
  },
  sourceFooter: {
    fontSize: 10,
    fontStyle: 'italic',
    color: '#9ca3af',
    marginTop: 6,
    marginLeft: 4,
  },
  suggestionsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 12,
    gap: 8,
  },
  suggestionChip: {
    backgroundColor: '#fff',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  suggestionText: {
    fontSize: 13,
    color: '#4b5563',
    fontWeight: '500',
  },
  loadingWrapper: {
    padding: 10,
    alignSelf: 'flex-start',
    marginLeft: 36,
  },
  attachMenu: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    position: 'absolute',
    bottom: 80,
    left: 0,
    right: 0,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 10,
    zIndex: 100,
  },
  attachRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
  },
  attachItem: {
    alignItems: 'center',
    gap: 8,
  },
  attachIcon: {
    width: 50,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
  },
  attachLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#4b5563',
  },
  inputContainer: {
    padding: 16,
    backgroundColor: '#FAF8F5',
    borderTopWidth: 1,
    borderTopColor: '#f3f0ea',
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 30,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: '#f3f0ea',
  },
  attachButton: {
    padding: 4,
  },
  input: {
    flex: 1,
    paddingHorizontal: 12,
    fontSize: 15,
    color: '#1c1c1c',
    maxHeight: 100,
  },
  micButton: {
    padding: 4,
    marginRight: 4,
  },
  sendButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#d97706',
    justifyContent: 'center',
    alignItems: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: '#f3f0ea',
  },
  langToggleRow: {
    flexDirection: 'row',
    marginTop: 6,
    gap: 6,
  },
  langToggleBtn: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    backgroundColor: '#f9fafb',
  },
  langToggleBtnActive: {
    backgroundColor: '#d97706',
    borderColor: '#d97706',
  },
  langToggleText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#6b7280',
  },
  langToggleTextActive: {
    color: '#fff',
  },
});

