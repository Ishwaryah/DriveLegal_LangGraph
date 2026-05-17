import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, TextInput, ScrollView, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useSettings } from '../hooks/useSettings';

const VEHICLES = [
  { id: '2w', title: 'Two-wheeler', subtitle: 'Bike, scooter', icon: 'motorbike' as const },
  { id: '4w', title: 'Car', subtitle: 'Personal, taxi', icon: 'car' as const },
  { id: 'cv', title: 'Commercial', subtitle: 'Truck, bus, fleet', icon: 'truck' as const },
];

export default function VehicleScreen() {
  const router = useRouter();
  const { selectedVehicleId, setSelectedVehicleId, addSavedVehicle } = useSettings();
  const [selectedId, setSelectedId] = useState(selectedVehicleId || '4w');
  const [vehicleNumber, setVehicleNumber] = useState('');

  useEffect(() => {
    if (selectedVehicleId) setSelectedId(selectedVehicleId);
    AsyncStorage.getItem('vehicle_number').then(saved => {
      if (saved) setVehicleNumber(saved);
    });
  }, [selectedVehicleId]);

  // Format vehicle number on change (simple formatting for display)
  const handleVehicleNumberChange = (text: string) => {
    setVehicleNumber(text.toUpperCase());
  };

  const handleContinue = async () => {
    setSelectedVehicleId(selectedId);
    if (vehicleNumber.trim()) {
      await AsyncStorage.setItem('vehicle_number', vehicleNumber.trim());
    } else {
      await AsyncStorage.removeItem('vehicle_number');
    }
    
    // Auto-create garage entry on onboarding completion
    const nick = selectedId === '2w' ? 'My Two-wheeler' : selectedId === 'cv' ? 'My Truck' : 'My Car';
    await addSavedVehicle({
      type: selectedId,
      plateNumber: vehicleNumber.trim().toUpperCase(),
      nickName: nick,
    });

    router.push('/(tabs)');
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />
      
      {/* Header with Progress */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#1B1A17" />
        </TouchableOpacity>
        
        <View style={styles.progressContainer}>
          <View style={styles.progressBarBg}>
            <View style={styles.progressBarFill} />
          </View>
        </View>
        <Text style={styles.progressText}>3/5</Text>
      </View>

      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Title & Subtitle */}
        <Text style={styles.headline}>What do you drive?</Text>
        <Text style={styles.subheadline}>
          We'll tailor fines and rules to your vehicle.
        </Text>

        {/* Vehicle List */}
        <View style={styles.listContainer}>
          {VEHICLES.map((v) => {
            const isSelected = selectedId === v.id;
            return (
              <TouchableOpacity
                key={v.id}
                style={[styles.vehicleCard, isSelected && styles.vehicleCardSelected]}
                onPress={() => setSelectedId(v.id)}
                activeOpacity={0.7}
              >
                <View style={styles.cardLeft}>
                  <View style={[styles.iconContainer, isSelected && styles.iconContainerSelected]}>
                    <MaterialCommunityIcons 
                      name={v.icon} 
                      size={20} 
                      color={isSelected ? "#fff" : "#1B1A17"} 
                    />
                  </View>
                  <View style={styles.cardTextContainer}>
                    <Text style={styles.titleText}>{v.title}</Text>
                    <Text style={styles.subtitleText}>{v.subtitle}</Text>
                  </View>
                </View>
                
                {/* Radio Button */}
                <View style={[styles.radioOuter, isSelected && styles.radioOuterSelected]}>
                  {isSelected && <View style={styles.radioInner} />}
                </View>
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Vehicle Number Input */}
        <View style={styles.inputCard}>
          <Text style={styles.inputLabel}>VEHICLE NUMBER (optional)</Text>
          <TextInput
            style={[styles.numberInput, Platform.OS === 'web' && { outlineStyle: 'none' } as any]}
            value={vehicleNumber}
            onChangeText={handleVehicleNumberChange}
            placeholder="e.g. MH 01 AB 1234"
            placeholderTextColor="#9ca3af"
            autoCapitalize="characters"
          />
        </View>

      </ScrollView>

      {/* Bottom Pinned Continue Button */}
      <View style={styles.footer}>
        <TouchableOpacity 
          style={styles.primaryButton}
          onPress={handleContinue}
        >
          <Text style={styles.primaryButtonText}>Continue</Text>
          <Ionicons name="arrow-forward" size={18} color="#fff" style={styles.buttonIcon} />
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FBF7F0',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: Platform.OS === 'android' ? 40 : 20,
    paddingBottom: 16,
  },
  backButton: {
    padding: 4,
  },
  progressContainer: {
    flex: 1,
    marginHorizontal: 16,
  },
  progressBarBg: {
    height: 4,
    backgroundColor: '#E5E7EB',
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    width: '60%', // 3/5 = 60%
    backgroundColor: '#C9621D',
  },
  progressText: {
    fontSize: 14,
    color: '#6b7280',
    fontWeight: '500',
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 40,
  },
  headline: {
    fontSize: 32,
    color: '#1B1A17',
    fontFamily: Platform.OS === 'web' ? '"Playfair Display", serif' : 'serif',
    marginBottom: 8,
    letterSpacing: -0.5,
  },
  subheadline: {
    fontSize: 15,
    lineHeight: 22,
    color: '#4b5563',
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
    marginBottom: 24,
  },
  listContainer: {
    gap: 12,
    marginBottom: 24,
  },
  vehicleCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 16,
    padding: 16,
  },
  vehicleCardSelected: {
    borderColor: '#C9621D',
    backgroundColor: '#FFF7ED',
  },
  cardLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#F3F4F6',
    justifyContent: 'center',
    alignItems: 'center',
  },
  iconContainerSelected: {
    backgroundColor: '#C9621D',
  },
  cardTextContainer: {
    marginLeft: 16,
  },
  titleText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1B1A17',
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
  },
  subtitleText: {
    fontSize: 13,
    color: '#6b7280',
    marginTop: 2,
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
  },
  radioOuter: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: '#D1D5DB',
    justifyContent: 'center',
    alignItems: 'center',
  },
  radioOuterSelected: {
    borderColor: '#C9621D',
  },
  radioInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#C9621D',
  },
  inputCard: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 16,
    padding: 16,
  },
  inputLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: '#9ca3af',
    marginBottom: 12,
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
    letterSpacing: 0.5,
  },
  numberInput: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1B1A17',
    fontFamily: Platform.OS === 'web' ? 'monospace' : 'System',
    letterSpacing: 4,
  },
  footer: {
    backgroundColor: '#fff',
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: Platform.OS === 'ios' ? 24 : 16,
    borderTopWidth: 1,
    borderTopColor: '#f3f4f6',
  },
  primaryButton: {
    backgroundColor: '#C9621D',
    borderRadius: 24,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 16,
  },
  primaryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
  },
  buttonIcon: {
    marginLeft: 8,
  },
});
