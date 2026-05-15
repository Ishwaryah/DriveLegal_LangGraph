import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Platform,
  Image,
  SafeAreaView,
  useWindowDimensions
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useSettings } from '../../hooks/useSettings';
import { useGeoFineAlert, FLAG_EMOJI } from '../../hooks/useGeoFineAlert';
import { useLocalDB, Fine } from '../../hooks/useLocalDB';

export default function HomeScreen() {
  const router = useRouter();
  const { t, profile, notificationsEnabled, highContrast } = useSettings();
  const { stateCode, countryCode, isOffline, permissionDenied } = useGeoFineAlert();
  const { getTopViolations } = useLocalDB();
  const { width: windowWidth } = useWindowDimensions();
  const width = Math.min(windowWidth, 420);
  const fontScale = width / 375;
  const fs = (size: number) => size * fontScale;

  const [topViolations, setTopViolations] = useState<Fine[]>([]);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  useEffect(() => {
    const loadData = async () => {
      const violations = await getTopViolations(stateCode || 'ALL');
      setTopViolations(violations);

      const savedSearches = await AsyncStorage.getItem('recentSearches');
      if (savedSearches) {
        setRecentSearches(JSON.parse(savedSearches));
      }
    };
    loadData();
  }, [stateCode]);

  const bg = highContrast ? '#000' : '#FAF8F5';
  const textPrimary = highContrast ? '#FFF' : '#1c1c1c';
  const textSecondary = highContrast ? '#FFF' : '#6b7280';
  const accent = highContrast ? '#FFD700' : '#d97706';
  const borderStyle = highContrast ? { borderWidth: 2, borderColor: '#FFF' } : {};

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: bg }]}>
      <StatusBar style={highContrast ? "light" : "dark"} />
      <ScrollView style={[styles.container, { backgroundColor: bg }]} contentContainerStyle={styles.content}>
        
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <View style={[styles.logoContainer, borderStyle, highContrast && {backgroundColor: '#000'}]}>
              <Text style={[styles.logoText, { color: accent, fontSize: fs(14) }]}>DL</Text>
            </View>
            <Text style={[styles.greeting, { color: textSecondary, fontSize: fs(12) }]}>{t('greeting')}</Text>
          </View>
          <TouchableOpacity 
            style={[styles.notificationBtn, borderStyle, highContrast && {backgroundColor: '#000'}]} 
            onPress={() => router.push('/(tabs)/settings')}
            accessibilityLabel="Notifications and Settings"
            accessibilityHint="Navigates to the settings screen"
          >
            <Ionicons name="notifications-outline" size={fs(22)} color={textPrimary} />
            {notificationsEnabled && <View style={styles.notificationDot} />}
          </TouchableOpacity>
        </View>

        {/* Location Card */}
        <TouchableOpacity 
          style={styles.locationCardContainer} 
          activeOpacity={0.9}
          accessibilityLabel="Location Status Card"
          accessibilityHint="Shows your current location and active rules"
        >
          <LinearGradient
            colors={['#1c1c1c', '#2d2d2d']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.locationCard}
          >
            <View style={styles.locationHeader}>
              <View style={[styles.liveIndicator, highContrast && {backgroundColor: accent}]}>
                <View style={[styles.liveDot, highContrast && {backgroundColor: '#000'}]} />
                <Text style={[styles.liveText, highContrast && {color: '#000'}, {fontSize: fs(9)}]}>LIVE</Text>
              </View>
              <Text style={[styles.locationLabel, {fontSize: fs(12)}]}>{t('location_label')}</Text>
            </View>
            <Text style={[styles.locationTitle, {fontSize: fs(22)}]}>Anna Salai, Chennai</Text>
            <Text style={[styles.locationSubtitle, {fontSize: fs(13)}]}>Tamil Nadu • Urban arterial road</Text>
            
            <View style={styles.pillsRow}>
              <View style={[styles.pill, borderStyle]}>
                <Text style={[styles.pillLabel, {fontSize: fs(10)}]}>{t('speed')}</Text>
                <Text style={[styles.pillValueOrange, { color: accent, fontSize: fs(14) }]}>50 <Text style={[styles.pillUnitOrange, {fontSize: fs(11)}]}>kmph</Text></Text>
              </View>
              <View style={[styles.pill, borderStyle, { backgroundColor: highContrast ? '#000' : 'rgba(239, 68, 68, 0.15)' }]}>
                <Text style={[styles.pillLabel, { color: highContrast ? '#FFF' : '#fca5a5', fontSize: fs(10) }]}>{t('fine_zone')}</Text>
                <Text style={[styles.pillValue, { color: highContrast ? accent : '#f87171', fontSize: fs(14) }]}>School</Text>
              </View>
              <View style={[styles.pill, borderStyle]}>
                <Text style={[styles.pillLabel, {fontSize: fs(10)}]}>{t('helmet')}</Text>
                <Text style={[styles.pillValue, {fontSize: fs(14)}]}>{t('mandatory')}</Text>
              </View>
            </View>
          </LinearGradient>
        </TouchableOpacity>

        {/* Location Fine Context Card */}
        <TouchableOpacity
          style={[styles.fineContextCard, borderStyle, highContrast && {backgroundColor: '#000'}]}
          activeOpacity={0.85}
          onPress={() => router.push('/(tabs)/fines')}
          accessibilityLabel="Local Fines"
          accessibilityHint="Navigates to the fines schedule for your area"
        >
          <View style={styles.fineContextLeft}>
            <Text style={[styles.fineContextFlag, {fontSize: fs(24)}]}>
              {countryCode ? FLAG_EMOJI[countryCode] ?? '📍' : '📍'}
            </Text>
            <View>
              <Text style={[styles.fineContextTitle, { color: textPrimary, fontSize: fs(14) }]}>
                {stateCode
                  ? `You're in ${stateCode} — Tap to see local fines`
                  : permissionDenied
                  ? 'Enable location to see local fines'
                  : 'Detecting your location…'}
              </Text>
              {isOffline && stateCode && (
                <Text style={[styles.fineContextOffline, {fontSize: fs(11)}]}>Using last known location</Text>
              )}
            </View>
          </View>
          <Ionicons name="chevron-forward" size={fs(18)} color={textSecondary} />
        </TouchableOpacity>

        {/* Action Grid */}
        <View style={styles.gridContainer}>
          <View style={styles.gridRow}>
            <TouchableOpacity 
              style={[styles.gridItem, styles.askItem, borderStyle, highContrast && {backgroundColor: accent}]} 
              onPress={() => router.push('/(tabs)/ask')}
              accessibilityLabel="Ask DriveLegal"
              accessibilityHint="Navigates to the AI chatbot assistant"
            >
              <View style={[styles.iconContainerWhite, highContrast && {backgroundColor: '#000'}]}>
                <Ionicons name="chatbubble-ellipses-outline" size={fs(20)} color={highContrast ? accent : "#fff"} />
              </View>
              <Text style={[styles.askItemTitle, highContrast && {color: '#000'}, {fontSize: fs(16)}]}>{t('ask_title')}</Text>
              <Text style={[styles.askItemSubtitle, highContrast && {color: '#000'}, {fontSize: fs(12)}]}>{t('ask_subtitle')}</Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={[styles.gridItem, borderStyle, highContrast && {backgroundColor: '#000'}]} 
              onPress={() => router.push('/(tabs)/fines')}
              accessibilityLabel="Challan Calculator"
              accessibilityHint="Navigates to the fines schedule and calculator"
            >
              <View style={[styles.iconContainerBrown, highContrast && {backgroundColor: accent}]}>
                <Ionicons name="document-text-outline" size={fs(20)} color={highContrast ? '#000' : "#d97706"} />
              </View>
              <Text style={[styles.gridItemTitle, { color: textPrimary, fontSize: fs(16) }]}>{t('challan_title')}</Text>
              <Text style={[styles.gridItemSubtitle, { color: textSecondary, fontSize: fs(12) }]}>{t('challan_subtitle')}</Text>
            </TouchableOpacity>
          </View>
          
          <View style={styles.gridRow}>
            <TouchableOpacity 
              style={[styles.gridItem, borderStyle, highContrast && {backgroundColor: '#000'}]} 
              onPress={() => router.push('/settings/documents')}
              accessibilityLabel="Document Vault"
              accessibilityHint="Navigates to your saved documents"
            >
              <View style={[styles.iconContainerBrown, highContrast && {backgroundColor: accent}]}>
                <Ionicons name="folder-outline" size={fs(20)} color={highContrast ? '#000' : "#d97706"} />
              </View>
              <Text style={[styles.gridItemTitle, { color: textPrimary, fontSize: fs(16) }]}>{t('vault_title')}</Text>
              <Text style={[styles.gridItemSubtitle, { color: textSecondary, fontSize: fs(12) }]}>{t('vault_subtitle')}</Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={[styles.gridItem, borderStyle, highContrast && {backgroundColor: '#000'}]} 
              onPress={() => router.push('/sos')}
              accessibilityLabel="SOS Emergency"
              accessibilityHint="Navigates to emergency contacts and assistance"
            >
              <View style={[styles.iconContainerBrown, { backgroundColor: highContrast ? '#EF4444' : '#fee2e2' }]}>
                <Ionicons name="alert-circle-outline" size={fs(20)} color={highContrast ? '#FFF' : "#ef4444"} />
              </View>
              <Text style={[styles.gridItemTitle, { color: textPrimary, fontSize: fs(16) }]}>{t('sos_title')}</Text>
              <Text style={[styles.gridItemSubtitle, { color: textSecondary, fontSize: fs(12) }]}>{t('sos_subtitle')}</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Recent Searches */}
        {recentSearches.length > 0 && (
          <>
            <View style={styles.briefHeader}>
              <Text style={[styles.briefTitle, { color: textPrimary, fontSize: fs(18) }]}>Recent Searches</Text>
            </View>
            <View style={styles.recentSearchesContainer}>
              {recentSearches.map((s, i) => (
                <TouchableOpacity 
                  key={i} 
                  style={[styles.recentSearchChip, borderStyle, highContrast && {backgroundColor: '#000'}]}
                  onPress={() => router.push(`/(tabs)/ask?q=${encodeURIComponent(s)}` as any)}
                  accessibilityLabel={`Recent search: ${s}`}
                  accessibilityHint="Repeats this search in the assistant"
                >
                  <Ionicons name="time-outline" size={fs(14)} color={textSecondary} />
                  <Text style={[styles.recentSearchText, { color: textPrimary, fontSize: fs(13) }]}>{s}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </>
        )}

        {/* Top Violations */}
        <View style={styles.briefHeader}>
          <Text style={[styles.briefTitle, { color: textPrimary, fontSize: fs(18) }]}>Most Common Violations in {stateCode || 'Your Area'}</Text>
          <TouchableOpacity accessibilityLabel="See all violations" accessibilityHint="Goes to violations list">
            <Text style={[styles.seeAllText, { color: accent, fontSize: fs(14) }]}>{t('see_all')}</Text>
          </TouchableOpacity>
        </View>

        {topViolations.length > 0 ? topViolations.map((v, i) => (
          <View key={v.id} style={[styles.briefCard, borderStyle, highContrast && {backgroundColor: '#000'}]}>
            <View style={[styles.briefIconContainer, { backgroundColor: highContrast ? accent : '#fef3c7' }]}>
              <MaterialCommunityIcons name="alert" size={fs(20)} color={highContrast ? '#000' : "#d97706"} />
            </View>
            <View style={styles.briefContent}>
              <Text style={[styles.briefCardTitle, { color: textPrimary, fontSize: fs(15) }]}>{v.offence_code}</Text>
              <Text style={[styles.briefCardDesc, { color: textSecondary, fontSize: fs(13) }]}>₹{v.amount_inr} - {v.vehicle_class}</Text>
            </View>
          </View>
        )) : (
          <View style={[styles.briefCard, borderStyle, highContrast && {backgroundColor: '#000'}]}>
            <View style={[styles.briefIconContainer, { backgroundColor: '#e0f2fe' }]}>
              <Ionicons name="information-circle-outline" size={fs(20)} color="#0284c7" />
            </View>
            <View style={styles.briefContent}>
              <Text style={[styles.briefCardTitle, { color: textPrimary, fontSize: fs(15) }]}>No common violations found</Text>
              <Text style={[styles.briefCardDesc, { color: textSecondary, fontSize: fs(13) }]}>Ensure your local rules are synced.</Text>
            </View>
          </View>
        )}
        
      </ScrollView>
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
    backgroundColor: '#FAF8F5',
  },
  content: {
    padding: 20,
    paddingTop: Platform.OS === 'android' ? 40 : 20,
    paddingBottom: 40,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  logoContainer: {
    width: 32,
    height: 32,
    backgroundColor: '#1c1c1c',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  logoText: {
    color: '#d97706',
    fontWeight: 'bold',
    fontSize: 14,
  },
  greeting: {
    fontSize: 12,
    fontWeight: '600',
    color: '#6b7280',
    letterSpacing: 0.5,
  },
  notificationBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#f3f0ea',
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  notificationDot: {
    position: 'absolute',
    top: 10,
    right: 10,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#ef4444',
    borderWidth: 1,
    borderColor: '#f3f0ea',
  },
  locationCardContainer: {
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.15,
    shadowRadius: 20,
    elevation: 8,
  },
  locationCard: {
    borderRadius: 24,
    padding: 20,
  },
  liveIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(217, 119, 6, 0.2)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    marginRight: 8,
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#d97706',
    marginRight: 4,
  },
  liveText: {
    color: '#d97706',
    fontSize: 9,
    fontWeight: 'bold',
  },
  locationHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  locationLabel: {
    color: '#9ca3af',
    fontSize: 12,
    fontWeight: '600',
    marginLeft: 6,
  },
  locationTitle: {
    color: '#fff',
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  locationSubtitle: {
    color: '#9ca3af',
    fontSize: 13,
    marginBottom: 20,
  },
  pillsRow: {
    flexDirection: 'row',
    gap: 8,
  },
  pill: {
    flex: 1,
    backgroundColor: '#2e2e2e',
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  pillLabel: {
    color: '#9ca3af',
    fontSize: 10,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  pillValue: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  pillValueOrange: {
    color: '#d97706',
    fontSize: 14,
    fontWeight: 'bold',
  },
  pillUnitOrange: {
    fontSize: 11,
    fontWeight: 'normal',
  },
  gridContainer: {
    gap: 12,
    marginBottom: 24,
  },
  gridRow: {
    flexDirection: 'row',
    gap: 12,
  },
  gridItem: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  askItem: {
    backgroundColor: '#d97706',
  },
  iconContainerWhite: {
    width: 40,
    height: 40,
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  iconContainerBrown: {
    width: 40,
    height: 40,
    backgroundColor: '#fef3c7',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  askItemTitle: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  askItemSubtitle: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 12,
  },
  gridItemTitle: {
    color: '#1c1c1c',
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  gridItemSubtitle: {
    color: '#6b7280',
    fontSize: 12,
  },
  briefHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  briefTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1c1c1c',
  },
  seeAllText: {
    color: '#b45309',
    fontSize: 14,
    fontWeight: '600',
  },
  briefCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    flexDirection: 'row',
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  briefIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  briefContent: {
    flex: 1,
  },
  briefCardTitle: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#1c1c1c',
    marginBottom: 4,
  },
  briefCardDesc: {
    fontSize: 13,
    color: '#4b5563',
    lineHeight: 18,
  },
  fineContextCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 16,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#F3F4F6',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 2,
  },
  fineContextLeft: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  fineContextFlag: {
    fontSize: 24,
  },
  fineContextTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1c1c1c',
  },
  fineContextOffline: {
    fontSize: 11,
    color: '#92400e',
    marginTop: 2,
  },
  recentSearchesContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 24,
  },
  recentSearchChip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    gap: 6,
  },
  recentSearchText: {
    fontSize: 13,
    color: '#4b5563',
  },
});

