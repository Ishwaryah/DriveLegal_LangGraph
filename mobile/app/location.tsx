import { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView, TextInput, ScrollView, Platform, ActivityIndicator, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';
import * as Location from 'expo-location';
import { useSettings } from '../hooks/useSettings';

const LOCATIONS = [
  { id: 'IN', country: 'India',          region: 'Select state in-app', code: 'IN', flag: '🇮🇳' },
  { id: 'GB', country: 'United Kingdom', region: 'England',             code: 'GB', flag: '🇬🇧' },
  { id: 'AE', country: 'UAE',            region: 'Dubai',               code: 'AE', flag: '🇦🇪' },
  { id: 'SG', country: 'Singapore',      region: '',                    code: 'SG', flag: '🇸🇬' },
];

function detectCountryFromCoords(lat: number, lon: number): string {
  if (lat >= 8 && lat <= 37 && lon >= 68 && lon <= 97)          return 'IN';
  if (lat >= 49 && lat <= 61 && lon >= -8 && lon <= 2)          return 'GB';
  if (lat >= 22 && lat <= 26 && lon >= 51 && lon <= 56)         return 'AE';
  if (lat >= 1.1 && lat <= 1.5 && lon >= 103 && lon <= 104.5)  return 'SG';
  return 'IN';
}

export default function LocationScreen() {
  const router = useRouter();
  const { defaultCountry, setDefaultCountry } = useSettings();
  const [selectedId, setSelectedId] = useState(defaultCountry || 'IN');
  const [searchQuery, setSearchQuery] = useState('');
  const [locating, setLocating] = useState(false);

  const handleUseMyLocation = async () => {
    setLocating(true);
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Denied', 'Location access is required to auto-detect your country.');
        setLocating(false);
        return;
      }
      const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Low });
      const detected = detectCountryFromCoords(loc.coords.latitude, loc.coords.longitude);
      setSelectedId(detected);
    } catch {
      Alert.alert('Location Error', 'Could not detect your location. Please select manually.');
    }
    setLocating(false);
  };

  const handleContinue = async () => {
    await setDefaultCountry(selectedId);
    router.push('/vehicle');
  };

  const filtered = LOCATIONS.filter(loc =>
    searchQuery === '' ||
    loc.country.toLowerCase().includes(searchQuery.toLowerCase()) ||
    loc.region.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
        <Text style={styles.headline}>Where do you drive?</Text>
        <Text style={styles.subheadline}>
          Rules and fines vary by country. Pick yours so we get it right.
        </Text>

        {/* Search Bar */}
        <View style={styles.searchContainer}>
          <Ionicons name="search" size={20} color="#6b7280" style={styles.searchIcon} />
          <TextInput
            style={[styles.searchInput, Platform.OS === 'web' && { outlineStyle: 'none' } as any]}
            placeholder="Search country..."
            placeholderTextColor="#9ca3af"
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
        </View>

        {/* Quick Actions */}
        <View style={styles.quickActions}>
          <TouchableOpacity style={styles.locationButton} onPress={handleUseMyLocation} disabled={locating}>
            {locating
              ? <ActivityIndicator size="small" color="#C9621D" style={styles.locationIcon} />
              : <Ionicons name="location" size={14} color="#C9621D" style={styles.locationIcon} />
            }
            <Text style={styles.locationButtonText}>{locating ? 'Detecting…' : 'Use my location'}</Text>
          </TouchableOpacity>
        </View>

        {/* Location List */}
        <View style={styles.listContainer}>
          {filtered.map((loc) => {
            const isSelected = selectedId === loc.id;
            return (
              <TouchableOpacity
                key={loc.id}
                style={[styles.locationCard, isSelected && styles.locationCardSelected]}
                onPress={() => setSelectedId(loc.id)}
                activeOpacity={0.7}
              >
                <View style={styles.cardLeft}>
                  <Text style={styles.flagEmoji}>{loc.flag}</Text>
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
        <TouchableOpacity style={styles.primaryButton} onPress={handleContinue}>
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
    width: '40%',
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
  },
  locationButtonText: {
    color: '#C9621D',
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
  flagEmoji: {
    fontSize: 24,
    width: 36,
  },
  cardTextContainer: {
    marginLeft: 8,
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
