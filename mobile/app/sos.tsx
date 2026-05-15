import React, { useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Platform,
  SafeAreaView,
  Linking,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';

export default function SOSScreen() {
  const router = useRouter();
  const scaleAnim = useRef(new Animated.Value(1)).current;
  const [holding, setHolding] = useState(false);

  const handlePressIn = () => {
    setHolding(true);
    Animated.loop(
      Animated.sequence([
        Animated.timing(scaleAnim, { toValue: 1.1, duration: 600, useNativeDriver: true }),
        Animated.timing(scaleAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
      ])
    ).start();
  };

  const handlePressOut = () => {
    setHolding(false);
    scaleAnim.stopAnimation();
    Animated.timing(scaleAnim, { toValue: 1, duration: 200, useNativeDriver: true }).start();
  };

  const call = (number: string) => {
    Linking.openURL(`tel:${number}`);
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>

        {/* HEADER */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.closeButton} onPress={() => router.back()}>
            <Ionicons name="close" size={20} color="#9CA3AF" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Roadside help</Text>
          <View style={styles.liveChip}>
            <View style={styles.liveDot} />
            <Text style={styles.liveText}>24/7</Text>
          </View>
        </View>

        {/* SOS BUTTON */}
        <View style={styles.sosSection}>
          <Animated.View style={[styles.sosRipple, { transform: [{ scale: scaleAnim }] }]}>
            <View style={styles.sosRippleInner} />
          </Animated.View>
          <TouchableOpacity
            style={styles.sosButton}
            onPressIn={handlePressIn}
            onPressOut={handlePressOut}
            activeOpacity={0.85}
          >
            <Text style={styles.sosLabel}>SOS</Text>
            <Text style={styles.sosHint}>HOLD 3 SEC</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.sosDesc}>
          Auto-shares your live location with emergency{'\n'}contacts and the nearest help desk.
        </Text>

        {/* EMERGENCY CONTACTS GRID */}
        <View style={styles.emergencyGrid}>
          <TouchableOpacity style={styles.emergencyCard} onPress={() => call('100')}>
            <View style={[styles.emergencyIcon, { backgroundColor: '#1E3A5F' }]}>
              <Ionicons name="headset" size={22} color="#60A5FA" />
            </View>
            <Text style={styles.emergencyTitle}>Police</Text>
            <Text style={styles.emergencyNumber}>100</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.emergencyCard} onPress={() => call('108')}>
            <View style={[styles.emergencyIcon, { backgroundColor: '#14532D' }]}>
              <Ionicons name="medkit" size={22} color="#4ADE80" />
            </View>
            <Text style={styles.emergencyTitle}>Ambulance</Text>
            <Text style={styles.emergencyNumber}>108</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.emergencyCard} onPress={() => call('1033')}>
            <View style={[styles.emergencyIcon, { backgroundColor: '#7C2D12' }]}>
              <Ionicons name="construct" size={22} color="#FB923C" />
            </View>
            <Text style={styles.emergencyTitle}>Highway aid</Text>
            <Text style={styles.emergencyNumber}>1033</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.emergencyCard}>
            <View style={[styles.emergencyIcon, { backgroundColor: '#713F12' }]}>
              <Ionicons name="car" size={22} color="#FCD34D" />
            </View>
            <Text style={styles.emergencyTitle}>Towing</Text>
            <Text style={styles.emergencyNumber}>Find near</Text>
          </TouchableOpacity>
        </View>

        {/* REPORT VIOLATION CARD */}
        <TouchableOpacity style={styles.reportCard}>
          <View style={styles.reportIconContainer}>
            <Ionicons name="camera" size={20} color="#D97706" />
          </View>
          <View style={styles.reportTextContainer}>
            <Text style={styles.reportTitle}>Report a violation</Text>
            <Text style={styles.reportSubtitle}>
              Submit dashcam footage to local enforcement. Auto-tagged with location, time, and applicable rule.
            </Text>
          </View>
        </TouchableOpacity>

        <TouchableOpacity style={styles.cameraButton}>
          <Text style={styles.cameraButtonText}>Open camera</Text>
        </TouchableOpacity>

      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#111111' },
  container: {
    flex: 1,
    backgroundColor: '#111111',
    paddingHorizontal: 20,
    paddingBottom: 32,
  },

  // Header
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: Platform.OS === 'android' ? 44 : 16,
    paddingBottom: 20,
  },
  closeButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#1F1F1F',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#F9FAFB',
  },
  liveChip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1F1F1F',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
    gap: 5,
    borderWidth: 1,
    borderColor: '#DC2626',
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#DC2626',
  },
  liveText: { fontSize: 11, fontWeight: '700', color: '#F87171' },

  // SOS Button
  sosSection: {
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 24,
    height: 180,
  },
  sosRipple: {
    position: 'absolute',
    width: 170,
    height: 170,
    borderRadius: 85,
    backgroundColor: 'rgba(185, 28, 28, 0.3)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  sosRippleInner: {
    width: 148,
    height: 148,
    borderRadius: 74,
    backgroundColor: 'rgba(185, 28, 28, 0.4)',
  },
  sosButton: {
    width: 130,
    height: 130,
    borderRadius: 65,
    backgroundColor: '#B91C1C',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#DC2626',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 20,
    elevation: 12,
  },
  sosLabel: {
    fontSize: 30,
    fontWeight: '900',
    color: '#fff',
    letterSpacing: 2,
  },
  sosHint: {
    fontSize: 10,
    fontWeight: '700',
    color: 'rgba(255,255,255,0.7)',
    letterSpacing: 1.5,
    marginTop: 2,
  },

  // Description
  sosDesc: {
    textAlign: 'center',
    fontSize: 13,
    color: '#6B7280',
    lineHeight: 20,
    marginBottom: 28,
  },

  // Emergency Grid
  emergencyGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 20,
  },
  emergencyCard: {
    width: '47.5%',
    backgroundColor: '#1C1C1C',
    borderRadius: 16,
    padding: 16,
    gap: 8,
    borderWidth: 1,
    borderColor: '#2D2D2D',
  },
  emergencyIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emergencyTitle: { fontSize: 14, fontWeight: '700', color: '#F9FAFB' },
  emergencyNumber: { fontSize: 13, color: '#9CA3AF' },

  // Report Violation
  reportCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#1C1C1C',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#2D2D2D',
    gap: 14,
    marginBottom: 14,
  },
  reportIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: '#2D1F00',
    alignItems: 'center',
    justifyContent: 'center',
  },
  reportTextContainer: { flex: 1 },
  reportTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#F9FAFB',
    marginBottom: 6,
  },
  reportSubtitle: {
    fontSize: 12,
    color: '#6B7280',
    lineHeight: 18,
  },

  // Camera button
  cameraButton: {
    backgroundColor: '#D97706',
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
  },
  cameraButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
  },
});
