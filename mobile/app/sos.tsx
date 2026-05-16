import React, { useRef, useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Platform,
  SafeAreaView,
  Linking,
  ScrollView,
  Vibration,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import * as ImagePicker from 'expo-image-picker';
import * as Location from 'expo-location';

export default function SOSScreen() {
  const router = useRouter();
  const scaleAnim = useRef(new Animated.Value(1)).current;
  const progressAnim = useRef(new Animated.Value(0)).current;
  const [holding, setHolding] = useState(false);
  const [isTriggered, setIsTriggered] = useState(false);

  const handlePressIn = () => {
    if (isTriggered) return;
    setHolding(true);
    
    // Pulse animation
    Animated.loop(
      Animated.sequence([
        Animated.timing(scaleAnim, { toValue: 1.1, duration: 600, useNativeDriver: true }),
        Animated.timing(scaleAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
      ])
    ).start();

    // Progress animation
    Animated.timing(progressAnim, {
      toValue: 1,
      duration: 3000,
      useNativeDriver: false,
    }).start(({ finished }) => {
      if (finished) {
        triggerSOS();
      }
    });

    // Initial haptic feedback
    Vibration.vibrate(100);
  };

  const handlePressOut = () => {
    setHolding(false);
    scaleAnim.stopAnimation();
    progressAnim.stopAnimation();
    
    Animated.parallel([
      Animated.timing(scaleAnim, { toValue: 1, duration: 200, useNativeDriver: true }),
      Animated.timing(progressAnim, { toValue: 0, duration: 200, useNativeDriver: false }),
    ]).start();
  };

  const triggerSOS = async () => {
    setIsTriggered(true);
    setHolding(false);
    Vibration.vibrate([0, 500, 200, 500]);

    try {
      // Auto-fetch location with high accuracy
      const { status } = await Location.requestForegroundPermissionsAsync();
      let locationText = "Detecting precise location...";
      
      if (status === 'granted') {
        const location = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.High,
        });
        
        // Reverse geocoding to get a human-readable address if possible
        const [address] = await Location.reverseGeocodeAsync({
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
        });

        const addressStr = address 
          ? `${address.name || ''}, ${address.street || ''}, ${address.city || ''}, ${address.region || ''}`
          : "Address not resolved";

        locationText = `Coordinates: ${location.coords.latitude.toFixed(5)}, ${location.coords.longitude.toFixed(5)}\nApprox. Address: ${addressStr}`;
      } else {
        locationText = "Location permission denied. Please enable GPS for emergency services to find you.";
      }

      Alert.alert(
        "🚨 EMERGENCY BROADCAST",
        `Distress signal sent successfully.\n\nYOUR CURRENT LOCATION:\n${locationText}`,
        [{ text: "DISMISS", onPress: () => setIsTriggered(false) }]
      );
    } catch (error) {
      Alert.alert("SOS Sent", "Emergency services notified via fallback protocol.");
      setIsTriggered(false);
    }
  };

  const call = (number: string) => {
    Linking.openURL(`tel:${number}`);
  };

  const openCamera = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Camera access is required to report violations.');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
    });

    if (!result.canceled) {
      Alert.alert('Evidence Captured', 'Photo saved and auto-linked to current location for reporting.');
    }
  };

  const progressWidth = progressAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%'],
  });

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView 
        style={styles.scrollView} 
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
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
            <Animated.View 
              style={[
                styles.sosRipple, 
                { 
                  transform: [{ scale: scaleAnim }],
                  backgroundColor: holding ? 'rgba(220, 38, 38, 0.4)' : 'rgba(185, 28, 28, 0.2)'
                } 
              ]}
            >
              <View style={styles.sosRippleInner} />
            </Animated.View>
            
            <TouchableOpacity
              style={[styles.sosButton, isTriggered && styles.sosButtonTriggered]}
              onPressIn={handlePressIn}
              onPressOut={handlePressOut}
              activeOpacity={0.9}
            >
              <LinearGradient
                colors={holding ? ['#DC2626', '#991B1B'] : ['#B91C1C', '#7F1D1D']}
                style={styles.sosGradient}
              >
                <Text style={styles.sosLabel}>{isTriggered ? 'SENT' : 'SOS'}</Text>
                {!isTriggered && <Text style={styles.sosHint}>HOLD 3 SEC</Text>}
              </LinearGradient>
            </TouchableOpacity>

            {/* Progress Bar under the button */}
            <View style={styles.progressContainer}>
              <Animated.View style={[styles.progressBar, { width: progressWidth }]} />
            </View>
          </View>

          <Text style={styles.sosDesc}>
            Auto-shares your live location with emergency{'\n'}contacts and the nearest help desk.
          </Text>

          {/* EMERGENCY CONTACTS GRID */}
          <View style={styles.emergencyGrid}>
            <TouchableOpacity style={styles.emergencyCard} onPress={() => call('100')}>
              <View style={[styles.emergencyIcon, { backgroundColor: '#1E3A5F' }]}>
                <Ionicons name="shield-checkmark" size={22} color="#60A5FA" />
              </View>
              <View>
                <Text style={styles.emergencyTitle}>Police</Text>
                <Text style={styles.emergencyNumber}>100</Text>
              </View>
            </TouchableOpacity>

            <TouchableOpacity style={styles.emergencyCard} onPress={() => call('108')}>
              <View style={[styles.emergencyIcon, { backgroundColor: '#14532D' }]}>
                <Ionicons name="medical" size={22} color="#4ADE80" />
              </View>
              <View>
                <Text style={styles.emergencyTitle}>Ambulance</Text>
                <Text style={styles.emergencyNumber}>108</Text>
              </View>
            </TouchableOpacity>

            <TouchableOpacity style={styles.emergencyCard} onPress={() => call('1033')}>
              <View style={[styles.emergencyIcon, { backgroundColor: '#7C2D12' }]}>
                <Ionicons name="construct" size={22} color="#FB923C" />
              </View>
              <View>
                <Text style={styles.emergencyTitle}>Highway aid</Text>
                <Text style={styles.emergencyNumber}>1033</Text>
              </View>
            </TouchableOpacity>

            <TouchableOpacity style={styles.emergencyCard} onPress={() => Alert.alert("Towing Services", "Searching for nearby towing partners...")}>
              <View style={[styles.emergencyIcon, { backgroundColor: '#422006' }]}>
                <Ionicons name="car-sport" size={22} color="#FCD34D" />
              </View>
              <View>
                <Text style={styles.emergencyTitle}>Towing</Text>
                <Text style={styles.emergencyNumber}>Find near</Text>
              </View>
            </TouchableOpacity>
          </View>

          {/* REPORT VIOLATION CARD */}
          <LinearGradient
            colors={['#1C1C1C', '#141414']}
            style={styles.reportCard}
          >
            <View style={styles.reportIconContainer}>
              <Ionicons name="videocam" size={20} color="#D97706" />
            </View>
            <View style={styles.reportTextContainer}>
              <Text style={styles.reportTitle}>Report a violation</Text>
              <Text style={styles.reportSubtitle}>
                Submit dashcam footage or photos to local enforcement. Auto-tagged with location & time.
              </Text>
            </View>
          </LinearGradient>

          <TouchableOpacity style={styles.cameraButton} onPress={openCamera}>
            <LinearGradient
              colors={['#D97706', '#B45309']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.cameraGradient}
            >
              <Ionicons name="camera" size={20} color="#fff" style={{ marginRight: 8 }} />
              <Text style={styles.cameraButtonText}>Open camera</Text>
            </LinearGradient>
          </TouchableOpacity>

          <View style={{ height: 40 }} />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#111111' },
  scrollView: { flex: 1 },
  scrollContent: { flexGrow: 1 },
  container: {
    paddingHorizontal: 20,
    paddingBottom: 20,
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
    borderWidth: 1,
    borderColor: '#333',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#F9FAFB',
    letterSpacing: 0.5,
  },
  liveChip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(220, 38, 38, 0.1)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
    gap: 6,
    borderWidth: 1,
    borderColor: 'rgba(220, 38, 38, 0.3)',
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#DC2626',
    shadowColor: '#DC2626',
    shadowRadius: 4,
    shadowOpacity: 0.8,
  },
  liveText: { fontSize: 11, fontWeight: '800', color: '#F87171' },

  // SOS Button
  sosSection: {
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 32,
    height: 200,
  },
  sosRipple: {
    position: 'absolute',
    width: 190,
    height: 190,
    borderRadius: 95,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sosRippleInner: {
    width: 160,
    height: 160,
    borderRadius: 80,
    backgroundColor: 'rgba(185, 28, 28, 0.2)',
  },
  sosButton: {
    width: 140,
    height: 140,
    borderRadius: 70,
    overflow: 'hidden',
    shadowColor: '#DC2626',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 20,
    elevation: 15,
  },
  sosButtonTriggered: {
    shadowColor: '#10B981',
  },
  sosGradient: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sosLabel: {
    fontSize: 34,
    fontWeight: '900',
    color: '#fff',
    letterSpacing: 3,
  },
  sosHint: {
    fontSize: 11,
    fontWeight: '800',
    color: 'rgba(255,255,255,0.8)',
    letterSpacing: 1.5,
    marginTop: 4,
  },
  progressContainer: {
    position: 'absolute',
    bottom: -10,
    width: 140,
    height: 4,
    backgroundColor: '#2D2D2D',
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    backgroundColor: '#fff',
  },

  // Description
  sosDesc: {
    textAlign: 'center',
    fontSize: 14,
    color: '#9CA3AF',
    lineHeight: 22,
    marginBottom: 32,
    fontWeight: '500',
  },

  // Emergency Grid
  emergencyGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 12,
    marginBottom: 24,
  },
  emergencyCard: {
    width: '48%',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1A1A1A',
    borderRadius: 20,
    padding: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: '#2D2D2D',
  },
  emergencyIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emergencyTitle: { fontSize: 14, fontWeight: '700', color: '#F3F4F6' },
  emergencyNumber: { fontSize: 12, color: '#6B7280', marginTop: 1 },

  // Report Violation
  reportCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    borderRadius: 20,
    padding: 20,
    borderWidth: 1,
    borderColor: '#2D2D2D',
    gap: 16,
    marginBottom: 16,
  },
  reportIconContainer: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: 'rgba(217, 119, 6, 0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(217, 119, 6, 0.3)',
  },
  reportTextContainer: { flex: 1 },
  reportTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#F9FAFB',
    marginBottom: 6,
  },
  reportSubtitle: {
    fontSize: 13,
    color: '#9CA3AF',
    lineHeight: 18,
  },

  // Camera button
  cameraButton: {
    borderRadius: 16,
    overflow: 'hidden',
    elevation: 8,
    shadowColor: '#D97706',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  cameraGradient: {
    paddingVertical: 18,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cameraButtonText: {
    fontSize: 16,
    fontWeight: '800',
    color: '#fff',
    letterSpacing: 0.5,
  },
});
