import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Platform,
  SafeAreaView,
  Modal,
  TextInput,
  Switch,
  Alert,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useSettings } from '../../../hooks/useSettings';
import { useSync } from '../../../hooks/useSync';

export default function ProfileScreen() {
  const router = useRouter();
  const { t, language, setLanguage, profile, updateProfile, notificationsEnabled, setNotificationsEnabled, highContrast, setHighContrast, defaultCountry, setDefaultCountry, defaultVehicleType, setDefaultVehicleType } = useSettings();
  const { syncStatus, triggerSync, isSyncing } = useSync();
  
  const [langModalVisible, setLangModalVisible] = useState(false);
  const [countryModalVisible, setCountryModalVisible] = useState(false);
  const [vehicleModalVisible, setVehicleModalVisible] = useState(false);
  const [editProfileVisible, setEditProfileVisible] = useState(false);
  const [tempName, setTempName] = useState(profile.name);

  const clearCache = async () => {
    try {
      await AsyncStorage.clear();
      Alert.alert("Success", "Cache cleared successfully.");
    } catch (e) {
      Alert.alert("Error", "Failed to clear cache.");
    }
  };

  const countries = [
    { code: 'IN', label: 'India' },
    { code: 'AE', label: 'UAE' },
    { code: 'SG', label: 'Singapore' },
    { code: 'GB', label: 'UK' }
  ];

  const vehicleTypes = [
    { code: '2W', label: 'Two Wheeler (Motorcycle)' },
    { code: '4W', label: 'Four Wheeler (Car)' },
    { code: 'CV', label: 'Commercial Vehicle' }
  ];

  const languages: { code: 'en' | 'hi' | 'ta' | 'te' | 'kn'; nativeName: string; romanName: string }[] = [
    { code: 'en', nativeName: 'English',  romanName: 'English' },
    { code: 'hi', nativeName: 'हिंदी',    romanName: 'Hindi' },
    { code: 'ta', nativeName: 'தமிழ்',    romanName: 'Tamil' },
    { code: 'te', nativeName: 'తెలుగు',   romanName: 'Telugu' },
    { code: 'kn', nativeName: 'ಕನ್ನಡ',    romanName: 'Kannada' },
  ];

  const handleSaveProfile = () => {
    updateProfile({ name: tempName, avatar: tempName.charAt(0).toUpperCase() });
    setEditProfileVisible(false);
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>

        {/* HEADER */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>{t('you')}</Text>
          <View style={{ width: 32 }} />
        </View>

        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>

          {/* PROFILE CARD */}
          <TouchableOpacity style={styles.profileCard} onPress={() => {
            setTempName(profile.name);
            setEditProfileVisible(true);
          }}>
            <View style={styles.avatarContainer}>
              <Text style={styles.avatarText}>{profile.avatar}</Text>
            </View>
            <View style={styles.profileInfo}>
              <Text style={styles.profileName}>{profile.name}</Text>
              <Text style={styles.profileMeta}>{t('driving_since', { year: profile.drivingSince })}</Text>
              <View style={styles.safeDriverBadge}>
                <Ionicons name="star" size={12} color="#16A34A" />
                <Text style={styles.safeDriverText}>4.9 {t('safe_driver')}</Text>
              </View>
            </View>
            <Ionicons name="pencil-outline" size={16} color="#9CA3AF" />
          </TouchableOpacity>

          {/* STATS ROW */}
          <View style={styles.statsRow}>
            <View style={styles.statCard}>
              <Text style={styles.statValue}>0</Text>
              <Text style={styles.statLabel}>{t('open_violations')}</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statCard}>
              <Text style={styles.statValue}>₹0</Text>
              <Text style={styles.statLabel}>{t('outstanding_fines')}</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statCard}>
              <Text style={[styles.statValue, { color: '#D97706' }]}>12</Text>
              <Text style={styles.statLabel}>{t('license_points')}</Text>
            </View>
          </View>

          {/* SETTINGS LIST */}
          <View style={styles.settingsList}>

            <SettingsItem
              icon="globe-outline"
              iconBg="#E0F2FE"
              iconColor="#0369A1"
              label="Default Country"
              value={countries.find(c => c.code === defaultCountry)?.label || defaultCountry}
              onPress={() => setCountryModalVisible(true)}
            />
            <SettingsItem
              icon="car-outline"
              iconBg="#FEF3C7"
              iconColor="#B45309"
              label="Default Vehicle"
              value={vehicleTypes.find(v => v.code === defaultVehicleType)?.label || defaultVehicleType}
              onPress={() => setVehicleModalVisible(true)}
            />
            <SettingsItem
              icon="language-outline"
              iconBg="#F3F4F6"
              iconColor="#4B5563"
              label={t('language')}
              value={(() => { const l = languages.find(x => x.code === language); return l ? `${l.nativeName} · ${l.romanName}` : language; })()}
              onPress={() => setLangModalVisible(true)}
            />
            <SettingsItem
              icon="document-text-outline"
              iconBg="#DCFCE7"
              iconColor="#15803D"
              label={t('vault_title')}
              onPress={() => router.push('/settings/documents')}
            />
            <SettingsItem
              icon="notifications-outline"
              iconBg="#F3F4F6"
              iconColor="#4B5563"
              label={t('notifications')}
              value={notificationsEnabled ? t('on') : t('off')}
              onPress={() => setNotificationsEnabled(!notificationsEnabled)}
            />
            <SettingsItem
              icon="contrast-outline"
              iconBg="#F3F4F6"
              iconColor="#4B5563"
              label="High Contrast Mode"
              onPress={() => setHighContrast(!highContrast)}
              rightElement={<Switch value={highContrast} onValueChange={setHighContrast} trackColor={{ true: '#D97706', false: '#E5E7EB' }} />}
            />
            <SettingsItem
              icon="cloud-download-outline"
              iconBg="#DCFCE7"
              iconColor="#15803D"
              label={t('offline_pack')}
              value={isSyncing ? 'Syncing...' : `${syncStatus.lastSync.rules} refresh`}
              valueColor="#D97706"
              onPress={() => triggerSync()}
            />
            <SettingsItem
              icon="trash-outline"
              iconBg="#FEE2E2"
              iconColor="#EF4444"
              label="Clear Cache"
              onPress={clearCache}
            />
            <SettingsItem
              icon="document-text"
              iconBg="#F3F4F6"
              iconColor="#4B5563"
              label="Legal Disclaimer"
              onPress={() => Alert.alert("Disclaimer", "This app provides general info and is not legal advice. Use at your own risk.")}
            />
            <SettingsItem
              icon="information-circle-outline"
              iconBg="#F3F4F6"
              iconColor="#4B5563"
              label="App Version"
              value="1.0.0"
              onPress={() => {}}
              isLast
            />

          </View>

        </ScrollView>
      </View>

      {/* Language Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={langModalVisible}
        onRequestClose={() => setLangModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>{t('language')}</Text>
              <TouchableOpacity onPress={() => setLangModalVisible(false)}>
                <Ionicons name="close" size={24} color="#1f2937" />
              </TouchableOpacity>
            </View>
            {languages.map((lang) => (
              <TouchableOpacity
                key={lang.code}
                style={[
                  styles.langOption,
                  language === lang.code && styles.langOptionSelected
                ]}
                onPress={() => {
                  setLanguage(lang.code);
                  setLangModalVisible(false);
                }}
              >
                <View style={{ flex: 1 }}>
                  <Text style={[styles.langLabel, language === lang.code && styles.langLabelSelected]}>
                    {lang.nativeName}
                  </Text>
                  <Text style={{ fontSize: 12, color: '#9CA3AF', marginTop: 2 }}>
                    {lang.romanName}
                  </Text>
                </View>
                {language === lang.code && (
                  <Ionicons name="checkmark" size={20} color="#D97706" />
                )}
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </Modal>

      {/* Country Modal */}
      <Modal animationType="slide" transparent={true} visible={countryModalVisible} onRequestClose={() => setCountryModalVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Default Country</Text>
              <TouchableOpacity onPress={() => setCountryModalVisible(false)}>
                <Ionicons name="close" size={24} color="#1f2937" />
              </TouchableOpacity>
            </View>
            {countries.map((country) => (
              <TouchableOpacity
                key={country.code}
                style={[styles.langOption, defaultCountry === country.code && styles.langOptionSelected]}
                onPress={() => { setDefaultCountry(country.code); setCountryModalVisible(false); }}
              >
                <Text style={[styles.langLabel, defaultCountry === country.code && styles.langLabelSelected]}>{country.label}</Text>
                {defaultCountry === country.code && <Ionicons name="checkmark" size={20} color="#D97706" />}
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </Modal>

      {/* Vehicle Modal */}
      <Modal animationType="slide" transparent={true} visible={vehicleModalVisible} onRequestClose={() => setVehicleModalVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Default Vehicle Type</Text>
              <TouchableOpacity onPress={() => setVehicleModalVisible(false)}>
                <Ionicons name="close" size={24} color="#1f2937" />
              </TouchableOpacity>
            </View>
            {vehicleTypes.map((type) => (
              <TouchableOpacity
                key={type.code}
                style={[styles.langOption, defaultVehicleType === type.code && styles.langOptionSelected]}
                onPress={() => { setDefaultVehicleType(type.code); setVehicleModalVisible(false); }}
              >
                <Text style={[styles.langLabel, defaultVehicleType === type.code && styles.langLabelSelected]}>{type.label}</Text>
                {defaultVehicleType === type.code && <Ionicons name="checkmark" size={20} color="#D97706" />}
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </Modal>

      {/* Edit Profile Modal */}
      <Modal
        animationType="fade"
        transparent={true}
        visible={editProfileVisible}
        onRequestClose={() => setEditProfileVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Edit Profile</Text>
              <TouchableOpacity onPress={() => setEditProfileVisible(false)}>
                <Ionicons name="close" size={24} color="#1f2937" />
              </TouchableOpacity>
            </View>
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Full Name</Text>
              <TextInput
                style={styles.textInput}
                value={tempName}
                onChangeText={setTempName}
                placeholder="Enter your name"
              />
            </View>
            <TouchableOpacity style={styles.saveButton} onPress={handleSaveProfile}>
              <Text style={styles.saveButtonText}>{t('save')}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

    </SafeAreaView>
  );
}

interface SettingsItemProps {
  icon: string;
  iconBg: string;
  iconColor: string;
  label: string;
  value?: string;
  valueColor?: string;
  onPress: () => void;
  isLast?: boolean;
  rightElement?: React.ReactNode;
}

function SettingsItem({
  icon, iconBg, iconColor, label, value, valueColor, onPress, isLast, rightElement
}: SettingsItemProps) {
  return (
    <>
      <TouchableOpacity style={styles.settingsItem} onPress={onPress}>
        <View style={[styles.settingsIconWrapper, { backgroundColor: iconBg }]}>
          <Ionicons name={icon as any} size={18} color={iconColor} />
        </View>
        <Text style={styles.settingsLabel}>{label}</Text>
        <View style={styles.settingsRight}>
          {rightElement ? (
            rightElement
          ) : (
            <>
              {value ? (
                <Text style={[styles.settingsValue, valueColor ? { color: valueColor } : {}]}>
                  {value}
                </Text>
              ) : null}
              <Ionicons name="chevron-forward" size={18} color="#D1D5DB" />
            </>
          )}
        </View>
      </TouchableOpacity>
      {!isLast && <View style={styles.settingsDivider} />}
    </>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#fff' },
  container: { flex: 1, backgroundColor: '#FAF8F5' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: Platform.OS === 'android' ? 40 : 10,
    paddingBottom: 16,
    backgroundColor: '#fff',
  },
  backButton: { padding: 4 },
  headerTitle: { fontSize: 18, fontWeight: '700', color: '#1f2937' },
  scrollContent: { paddingBottom: 40, paddingHorizontal: 20 },

  // Profile Card
  profileCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 20,
    marginTop: 20,
    borderWidth: 1,
    borderColor: '#F3F4F6',
    gap: 16,
  },
  avatarContainer: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#FEF3C7',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: { fontSize: 24, fontWeight: '700', color: '#B45309' },
  profileInfo: { flex: 1, gap: 4 },
  profileName: { fontSize: 18, fontWeight: '700', color: '#1F2937' },
  profileMeta: { fontSize: 13, color: '#6B7280' },
  safeDriverBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 2,
  },
  safeDriverText: { fontSize: 13, fontWeight: '600', color: '#16A34A' },

  // Stats
  statsRow: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderRadius: 16,
    marginTop: 16,
    borderWidth: 1,
    borderColor: '#F3F4F6',
    overflow: 'hidden',
  },
  statCard: {
    flex: 1,
    paddingVertical: 16,
    alignItems: 'center',
    gap: 4,
  },
  statDivider: { width: 1, backgroundColor: '#F3F4F6', marginVertical: 12 },
  statValue: { fontSize: 22, fontWeight: '800', color: '#1F2937' },
  statLabel: { fontSize: 11, color: '#9CA3AF', textAlign: 'center' },

  // Settings List
  settingsList: {
    backgroundColor: '#fff',
    borderRadius: 16,
    marginTop: 24,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: '#F3F4F6',
  },
  settingsItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    gap: 12,
  },
  settingsIconWrapper: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  settingsLabel: { flex: 1, fontSize: 15, fontWeight: '500', color: '#1F2937' },
  settingsRight: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  settingsValue: { fontSize: 13, color: '#9CA3AF' },
  settingsDivider: { height: 1, backgroundColor: '#F9FAFB', marginLeft: 48 },

  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    minHeight: 300,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1f2937',
  },
  langOption: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
  },
  langOptionSelected: {
    backgroundColor: '#FEF3C7',
    marginHorizontal: -24,
    paddingHorizontal: 24,
  },
  langLabel: {
    fontSize: 16,
    color: '#4b5563',
  },
  langLabelSelected: {
    color: '#D97706',
    fontWeight: '700',
  },

  // Edit Profile
  inputGroup: {
    marginBottom: 20,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6b7280',
    marginBottom: 8,
  },
  textInput: {
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 12,
    padding: 12,
    fontSize: 16,
    color: '#1f2937',
  },
  saveButton: {
    backgroundColor: '#D97706',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
});
