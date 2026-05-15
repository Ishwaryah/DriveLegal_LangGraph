import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, TextInput, ScrollView, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';

const LOCATIONS = [
  { id: 'IN', country: 'India', region: 'Tamil Nadu', code: 'IN' },
  { id: 'US', country: 'United States', region: 'California', code: 'US' },
  { id: 'GB', country: 'United Kingdom', region: 'England', code: 'GB' },
  { id: 'AE', country: 'UAE', region: 'Dubai', code: 'AE' },
  { id: 'SG', country: 'Singapore', region: '', code: 'SG' },
];

export default function LocationScreen() {
  const router = useRouter();
  const [selectedId, setSelectedId] = useState('IN');
  const [searchQuery, setSearchQuery] = useState('');

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
        <Text style={styles.progressText}>2/5</Text>
      </View>

      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Title & Subtitle */}
        <Text style={styles.headline}>Where do you drive?</Text>
        <Text style={styles.subheadline}>
          Rules and fines vary by state. Pick yours so we get it right.
        </Text>

        {/* Search Bar */}
        <View style={styles.searchContainer}>
          <Ionicons name="search" size={20} color="#6b7280" style={styles.searchIcon} />
          <TextInput
            style={[styles.searchInput, Platform.OS === 'web' && { outlineStyle: 'none' } as any]}
            placeholder="Search country or state..."
            placeholderTextColor="#9ca3af"
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
        </View>

        {/* Quick Actions */}
        <View style={styles.quickActions}>
          <TouchableOpacity style={styles.locationButton}>
            <Ionicons name="location" size={14} color="#ef4444" style={styles.locationIcon} />
            <Text style={styles.locationButtonText}>Use my location</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.recentButton}>
            <Text style={styles.recentButtonText}>Recent</Text>
          </TouchableOpacity>
        </View>

        {/* Location List */}
        <View style={styles.listContainer}>
          {LOCATIONS.map((loc) => {
            const isSelected = selectedId === loc.id;
            return (
              <TouchableOpacity
                key={loc.id}
                style={[styles.locationCard, isSelected && styles.locationCardSelected]}
                onPress={() => setSelectedId(loc.id)}
                activeOpacity={0.7}
              >
                <View style={styles.cardLeft}>
                  <Text style={styles.countryCode}>{loc.code}</Text>
                  <View style={styles.cardTextContainer}>
                    <Text style={styles.countryText}>{loc.country}</Text>
                    {loc.region ? <Text style={styles.regionText}>{loc.region}</Text> : null}
                  </View>
                </View>
                {isSelected && (
                  <View style={styles.checkContainer}>
                    <Ionicons name="checkmark-circle" size={24} color="#C9621D" />
                  </View>
                )}
              </TouchableOpacity>
            );
          })}
        </View>
      </ScrollView>

      {/* Bottom Pinned Continue Button */}
      <View style={styles.footer}>
        <TouchableOpacity 
          style={styles.primaryButton}
          onPress={() => router.push('/vehicle')}
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
    width: '40%', // 2/5 = 40%
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
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 24,
    paddingHorizontal: 16,
    height: 48,
    marginBottom: 16,
  },
  searchIcon: {
    marginRight: 10,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    color: '#1B1A17',
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
  },
  quickActions: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
    gap: 12,
  },
  locationButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFEDD5',
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 20,
  },
  locationIcon: {
    marginRight: 6,
    color: '#C9621D',
  },
  locationButtonText: {
    color: '#C9621D',
    fontSize: 13,
    fontWeight: '600',
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
  },
  recentButton: {
    backgroundColor: '#F3F4F6',
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 20,
  },
  recentButtonText: {
    color: '#4b5563',
    fontSize: 13,
    fontWeight: '600',
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
  },
  listContainer: {
    gap: 12,
  },
  locationCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 16,
    padding: 16,
  },
  locationCardSelected: {
    borderColor: '#C9621D',
    backgroundColor: '#FFF7ED',
  },
  cardLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  countryCode: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
    width: 32,
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
  },
  cardTextContainer: {
    marginLeft: 12,
  },
  countryText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1B1A17',
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
  },
  regionText: {
    fontSize: 13,
    color: '#6b7280',
    marginTop: 2,
    fontFamily: Platform.OS === 'web' ? 'Inter, sans-serif' : 'System',
  },
  checkContainer: {
    width: 24,
    height: 24,
    justifyContent: 'center',
    alignItems: 'center',
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
