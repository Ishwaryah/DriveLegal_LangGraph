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
  TouchableWithoutFeedback,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import {
  useGeoFineAlert,
  STATE_FINE_INFO,
  FLAG_EMOJI,
  GeoAlert,
} from '../../../hooks/useGeoFineAlert';

const MANUAL_COUNTRIES = ['India', 'United Arab Emirates', 'Singapore', 'United Kingdom'];
const MANUAL_STATES: Record<string, string[]> = {
  India: ['Tamil Nadu', 'Maharashtra', 'Karnataka', 'Delhi', 'Gujarat', 'Telangana'],
  'United Arab Emirates': [],
  Singapore: [],
  'United Kingdom': [],
};

export default function LiveNearYouScreen() {
  const router = useRouter();
  const {
    country,
    countryCode,
    stateCode,
    locationName,
    activeAlerts,
    isOffline,
    permissionDenied,
    speedZoneLimit,
    dismissAlert,
    setManualLocation,
  } = useGeoFineAlert();

  const [manualCountry, setManualCountry] = useState('India');
  const [manualState, setManualState] = useState('Tamil Nadu');
  const [showManualModal, setShowManualModal] = useState(false);

  const stateBoundaryAlert = activeAlerts.find(a => a.type === 'state_boundary') ?? null;
  const fineInfo = stateCode ? STATE_FINE_INFO[stateCode] : null;
  const flag = countryCode ? FLAG_EMOJI[countryCode] : '📍';

  const handleManualSubmit = () => {
    setManualLocation(manualCountry, manualState);
    setShowManualModal(false);
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>

        {/* HEADER */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Live near you</Text>
          <View style={[styles.liveBadge, isOffline && styles.liveBadgeOffline]}>
            <View style={[styles.liveDot, isOffline && styles.liveDotOffline]} />
            <Text style={[styles.liveText, isOffline && styles.liveTextOffline]}>
              {isOffline ? 'Cached' : 'Live'}
            </Text>
          </View>
        </View>

        {/* OFFLINE BANNER */}
        {isOffline && locationName && (
          <View style={styles.offlineBanner}>
            <Ionicons name="cloud-offline-outline" size={14} color="#92400e" />
            <Text style={styles.offlineText}>
              Using last known location: {locationName}
            </Text>
          </View>
        )}

        {/* STATE BOUNDARY ALERT BANNER */}
        {stateBoundaryAlert && (
          <StateBanner alert={stateBoundaryAlert} onDismiss={dismissAlert} />
        )}

        {/* PERMISSION DENIED BANNER */}
        {permissionDenied && !locationName && (
          <View style={styles.permDeniedBanner}>
            <Ionicons name="location-outline" size={16} color="#1d4ed8" />
            <Text style={styles.permDeniedText}>
              Location access denied.{' '}
              <Text style={styles.permDeniedLink} onPress={() => setShowManualModal(true)}>
                Enter location manually →
              </Text>
            </Text>
          </View>
        )}

        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>

          {/* MAP SECTION */}
          <View style={styles.mapContainer}>
            <View style={styles.mapGridLineV} />
            <View style={[styles.mapGridLineV, { left: '70%' }]} />

            <Text style={styles.mapZoneText}>
              {locationName ? locationName.split(',')[0].toUpperCase() : 'LOCATING...'}
            </Text>

            {/* Radar */}
            <View style={styles.radarCircleLarge}>
              <View style={styles.radarCircleMedium}>
                <View style={styles.radarCircleSmall}>
                  <View style={styles.radarDot} />
                </View>
              </View>
            </View>
            <View style={styles.radarSecondary} />

            {/* Location Card */}
            <TouchableOpacity
              style={styles.locationCard}
              onPress={permissionDenied ? () => setShowManualModal(true) : undefined}
              activeOpacity={permissionDenied ? 0.7 : 1}
            >
              <View style={styles.locationIconContainer}>
                <Ionicons name="location" size={18} color="#fff" />
              </View>
              <View style={styles.locationTextContainer}>
                <Text style={styles.locationTitle}>
                  {locationName ?? (permissionDenied ? 'Tap to set location' : 'Acquiring GPS…')}
                </Text>
                <Text style={styles.locationSubtitle}>
                  {isOffline
                    ? 'Last known • GPS inactive'
                    : locationName
                    ? `${flag} ${country ?? ''} • GPS active`
                    : 'Waiting for signal…'}
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
            </TouchableOpacity>
          </View>

          {/* RULES SECTION */}
          <View style={styles.rulesContainer}>
            <Text style={styles.sectionTitle}>RULES IN FORCE HERE</Text>

            <TouchableOpacity style={styles.ruleCard}>
              <View style={[styles.ruleIconContainer, { backgroundColor: '#FFEDD5' }]}>
                <Ionicons name="flash" size={20} color="#C2410C" />
              </View>
              <View style={styles.ruleTextContainer}>
                <Text style={styles.ruleTitle}>
                  Speed limit · <Text style={styles.ruleTitleBold}>50 km/h</Text>
                </Text>
                <Text style={styles.ruleSubtitle}>Urban arterial · TN Rule §125</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
            </TouchableOpacity>

            <TouchableOpacity style={styles.ruleCard}>
              <View style={[styles.ruleIconContainer, { backgroundColor: '#FEF3C7' }]}>
                <Ionicons name="business" size={20} color="#B45309" />
              </View>
              <View style={styles.ruleTextContainer}>
                <Text style={styles.ruleTitle}>
                  School zone in <Text style={styles.ruleTitleBold}>240m</Text>
                </Text>
                <Text style={styles.ruleSubtitle}>Limit drops to 25 km/h</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
            </TouchableOpacity>

            <TouchableOpacity style={styles.ruleCard}>
              <View style={[styles.ruleIconContainer, { backgroundColor: '#E0F2FE' }]}>
                <Ionicons name="megaphone" size={20} color="#0369A1" />
              </View>
              <View style={styles.ruleTextContainer}>
                <Text style={styles.ruleTitleBold}>No-honking corridor</Text>
                <Text style={styles.ruleSubtitle}>Hospital - 24/7 - ₹1,000 fine</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
            </TouchableOpacity>

            <TouchableOpacity style={styles.ruleCard}>
              <View style={[styles.ruleIconContainer, { backgroundColor: '#F3F4F6' }]}>
                <Ionicons name="car" size={20} color="#4B5563" />
              </View>
              <View style={styles.ruleTextContainer}>
                <Text style={styles.ruleTitleBold}>Parking allowed (paid)</Text>
                <Text style={styles.ruleSubtitle}>₹20/hr · 8AM–8PM</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#9ca3af" />
            </TouchableOpacity>
          </View>

          {/* Bottom padding for speed zone card */}
          {speedZoneLimit !== null && <View style={{ height: 100 }} />}
        </ScrollView>

        {/* SPEED ZONE PERSISTENT BOTTOM CARD */}
        {speedZoneLimit !== null && fineInfo && (
          <View style={styles.speedZoneCard}>
            <View style={styles.speedZoneLeft}>
              <Text style={styles.speedZoneIcon}>🚦</Text>
              <View>
                <Text style={styles.speedZoneTitle}>Speed Zone: {speedZoneLimit} km/h</Text>
                <Text style={styles.speedZoneSubtitle}>
                  Overspeed fine in {fineInfo.name}: {fineInfo.speedFine}
                </Text>
              </View>
            </View>
          </View>
        )}

        {/* MANUAL LOCATION MODAL */}
        <Modal
          visible={showManualModal}
          transparent
          animationType="slide"
          onRequestClose={() => setShowManualModal(false)}
        >
          <TouchableWithoutFeedback onPress={() => setShowManualModal(false)}>
            <View style={styles.modalOverlay}>
              <TouchableWithoutFeedback>
                <View style={styles.modalSheet}>
                  <View style={styles.modalHandle} />
                  <Text style={styles.modalTitle}>Set your location</Text>
                  <Text style={styles.modalSubtitle}>
                    Location access is required to detect local traffic laws.
                    You can manually pick your region below.
                  </Text>

                  <Text style={styles.pickerLabel}>Country</Text>
                  <View style={styles.pickerRow}>
                    {MANUAL_COUNTRIES.map(c => (
                      <TouchableOpacity
                        key={c}
                        style={[styles.pickerChip, manualCountry === c && styles.pickerChipActive]}
                        onPress={() => {
                          setManualCountry(c);
                          setManualState(MANUAL_STATES[c]?.[0] ?? '');
                        }}
                      >
                        <Text style={[styles.pickerChipText, manualCountry === c && styles.pickerChipTextActive]}>
                          {c}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>

                  {MANUAL_STATES[manualCountry]?.length > 0 && (
                    <>
                      <Text style={styles.pickerLabel}>State / Province</Text>
                      <View style={styles.pickerRow}>
                        {MANUAL_STATES[manualCountry].map(s => (
                          <TouchableOpacity
                            key={s}
                            style={[styles.pickerChip, manualState === s && styles.pickerChipActive]}
                            onPress={() => setManualState(s)}
                          >
                            <Text style={[styles.pickerChipText, manualState === s && styles.pickerChipTextActive]}>
                              {s}
                            </Text>
                          </TouchableOpacity>
                        ))}
                      </View>
                    </>
                  )}

                  <TouchableOpacity style={styles.modalConfirmBtn} onPress={handleManualSubmit}>
                    <Text style={styles.modalConfirmText}>Confirm Location</Text>
                  </TouchableOpacity>
                </View>
              </TouchableWithoutFeedback>
            </View>
          </TouchableWithoutFeedback>
        </Modal>

      </View>
    </SafeAreaView>
  );
}

function StateBanner({ alert, onDismiss }: { alert: GeoAlert; onDismiss: (id: string) => void }) {
  return (
    <TouchableOpacity style={styles.alertBanner} activeOpacity={0.9} onPress={() => onDismiss(alert.id)}>
      <Text style={styles.alertText}>{alert.message}</Text>
      <Ionicons name="close" size={18} color="#065f46" />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#fff',
  },
  container: {
    flex: 1,
    backgroundColor: '#FAF8F5',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: Platform.OS === 'android' ? 40 : 10,
    paddingBottom: 16,
    backgroundColor: '#fff',
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
    zIndex: 10,
  },
  backButton: {
    padding: 4,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1f2937',
    marginLeft: -16,
  },
  liveBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ECFDF5',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#D1FAE5',
  },
  liveBadgeOffline: {
    backgroundColor: '#FEF3C7',
    borderColor: '#FDE68A',
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#10B981',
    marginRight: 6,
  },
  liveDotOffline: {
    backgroundColor: '#D97706',
  },
  liveText: {
    color: '#059669',
    fontSize: 12,
    fontWeight: '700',
  },
  liveTextOffline: {
    color: '#92400e',
  },
  offlineBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FEF3C7',
    paddingHorizontal: 16,
    paddingVertical: 8,
    gap: 8,
  },
  offlineText: {
    fontSize: 12,
    color: '#92400e',
    fontWeight: '500',
    flex: 1,
  },
  alertBanner: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#D1FAE5',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#A7F3D0',
    gap: 10,
  },
  alertText: {
    flex: 1,
    fontSize: 13,
    color: '#065f46',
    fontWeight: '500',
    lineHeight: 18,
  },
  permDeniedBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#EFF6FF',
    paddingHorizontal: 16,
    paddingVertical: 10,
    gap: 8,
  },
  permDeniedText: {
    fontSize: 13,
    color: '#1e40af',
    flex: 1,
  },
  permDeniedLink: {
    fontWeight: '700',
    textDecorationLine: 'underline',
  },
  scrollContent: {
    paddingBottom: 40,
  },
  mapContainer: {
    height: 280,
    backgroundColor: '#F3EDE4',
    position: 'relative',
    overflow: 'hidden',
  },
  mapGridLineV: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: '45%',
    width: 24,
    backgroundColor: '#fff',
    transform: [{ skewX: '-10deg' }],
    opacity: 0.6,
  },
  mapZoneText: {
    position: 'absolute',
    top: 30,
    left: 40,
    fontSize: 12,
    fontWeight: '800',
    color: '#78350F',
    letterSpacing: 0.5,
  },
  radarCircleLarge: {
    position: 'absolute',
    top: '20%',
    left: '30%',
    width: 200,
    height: 200,
    borderRadius: 100,
    borderWidth: 1,
    borderColor: '#D97706',
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(217, 119, 6, 0.05)',
  },
  radarCircleMedium: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: 'rgba(217, 119, 6, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  radarCircleSmall: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#D97706',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: 'rgba(217, 119, 6, 0.3)',
  },
  radarDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#fff',
  },
  radarSecondary: {
    position: 'absolute',
    bottom: 20,
    right: -20,
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 1,
    borderColor: '#D97706',
    borderStyle: 'dashed',
    backgroundColor: 'rgba(217, 119, 6, 0.08)',
  },
  locationCard: {
    position: 'absolute',
    bottom: 20,
    left: 20,
    right: 20,
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 5,
  },
  locationIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#D97706',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  locationTextContainer: {
    flex: 1,
  },
  locationTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#1f2937',
    marginBottom: 4,
  },
  locationSubtitle: {
    fontSize: 12,
    color: '#6b7280',
  },
  rulesContainer: {
    padding: 20,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#9CA3AF',
    letterSpacing: 1,
    marginBottom: 16,
    marginTop: 8,
  },
  ruleCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#F3F4F6',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.02,
    shadowRadius: 6,
    elevation: 1,
  },
  ruleIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 14,
  },
  ruleTextContainer: {
    flex: 1,
  },
  ruleTitle: {
    fontSize: 15,
    color: '#1F2937',
    marginBottom: 4,
    fontWeight: '500',
  },
  ruleTitleBold: {
    fontWeight: '700',
    color: '#1F2937',
    fontSize: 15,
  },
  ruleSubtitle: {
    fontSize: 13,
    color: '#6B7280',
  },
  // Speed zone bottom card
  speedZoneCard: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#1c1c1c',
    paddingHorizontal: 20,
    paddingVertical: 16,
    paddingBottom: Platform.OS === 'ios' ? 28 : 16,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 10,
  },
  speedZoneLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  speedZoneIcon: {
    fontSize: 28,
  },
  speedZoneTitle: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 2,
  },
  speedZoneSubtitle: {
    color: '#9ca3af',
    fontSize: 12,
    lineHeight: 16,
  },
  // Manual location modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'flex-end',
  },
  modalSheet: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    padding: 24,
    paddingBottom: Platform.OS === 'ios' ? 40 : 24,
  },
  modalHandle: {
    width: 40,
    height: 4,
    backgroundColor: '#e5e7eb',
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 20,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1c1c1c',
    marginBottom: 8,
  },
  modalSubtitle: {
    fontSize: 14,
    color: '#6b7280',
    lineHeight: 20,
    marginBottom: 24,
  },
  pickerLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#9ca3af',
    letterSpacing: 0.5,
    marginBottom: 10,
  },
  pickerRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 20,
  },
  pickerChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#f3f4f6',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  pickerChipActive: {
    backgroundColor: '#d97706',
    borderColor: '#d97706',
  },
  pickerChipText: {
    fontSize: 13,
    color: '#374151',
    fontWeight: '500',
  },
  pickerChipTextActive: {
    color: '#fff',
    fontWeight: '700',
  },
  modalConfirmBtn: {
    backgroundColor: '#1c1c1c',
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 4,
  },
  modalConfirmText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
});
