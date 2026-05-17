import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Platform,
  SafeAreaView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';

export default function BrowseRulesScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>

        {/* HEADER */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.canGoBack() ? router.back() : router.replace('/')}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Browse rules</Text>
          <TouchableOpacity style={styles.searchButton}>
            <Ionicons name="search" size={20} color="#4B5563" />
          </TouchableOpacity>
        </View>

        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>

          {/* QUICK ANSWER BANNER */}
          <View style={styles.bannerContainer}>
            <View style={styles.bannerIconContainer}>
              <Ionicons name="sparkles" size={20} color="#9A3412" />
            </View>
            <View style={styles.bannerTextContainer}>
              <Text style={styles.bannerTitle}>Want a quick answer?</Text>
              <Text style={styles.bannerSubtitle}>Ask the assistant — it knows your local rules.</Text>
            </View>
            <TouchableOpacity
              style={styles.bannerButton}
              onPress={() => router.push('/ask')}
            >
              <Ionicons name="chatbubble-outline" size={16} color="#fff" style={{ marginRight: 6 }} />
              <Text style={styles.bannerButtonText}>Ask</Text>
            </TouchableOpacity>
          </View>

          {/* BROWSE BY CATEGORY */}
          <View style={styles.sectionContainer}>
            <Text style={styles.sectionTitle}>BROWSE BY CATEGORY</Text>

            <View style={styles.gridContainer}>
              {/* Category 1 */}
              <TouchableOpacity
                style={styles.categoryCard}
                onPress={() => router.push('/zones/speed-limits')}
              >
                <View style={[styles.iconWrapper, { backgroundColor: '#FFEDD5' }]}>
                  <Ionicons name="flash" size={20} color="#C2410C" />
                </View>
                <Text style={styles.categoryTitle}>Speed & limits</Text>
                <Text style={styles.categorySubtitle}>14 rules</Text>
              </TouchableOpacity>

              {/* Category 2 */}
              <TouchableOpacity style={styles.categoryCard}>
                <View style={[styles.iconWrapper, { backgroundColor: '#FEF3C7' }]}>
                  <Ionicons name="car-sport" size={20} color="#B45309" />
                </View>
                <Text style={styles.categoryTitle}>Safety gear</Text>
                <Text style={styles.categorySubtitle}>8 rules</Text>
              </TouchableOpacity>

              {/* Category 3 */}
              <TouchableOpacity style={styles.categoryCard}>
                <View style={[styles.iconWrapper, { backgroundColor: '#E0F2FE' }]}>
                  <Ionicons name="car" size={20} color="#0369A1" />
                </View>
                <Text style={styles.categoryTitle}>Lane & overtaking</Text>
                <Text style={styles.categorySubtitle}>12 rules</Text>
              </TouchableOpacity>

              {/* Category 4 */}
              <TouchableOpacity style={styles.categoryCard}>
                <View style={[styles.iconWrapper, { backgroundColor: '#DCFCE7' }]}>
                  <Ionicons name="medical" size={20} color="#15803D" />
                </View>
                <Text style={styles.categoryTitle}>Signal & signage</Text>
                <Text style={styles.categorySubtitle}>9 rules</Text>
              </TouchableOpacity>

              {/* Category 5 */}
              <TouchableOpacity style={styles.categoryCard}>
                <View style={[styles.iconWrapper, { backgroundColor: '#F3F4F6' }]}>
                  <Ionicons name="document-text" size={20} color="#4B5563" />
                </View>
                <Text style={styles.categoryTitle}>Documents</Text>
                <Text style={styles.categorySubtitle}>6 rules</Text>
              </TouchableOpacity>

              {/* Category 6 */}
              <TouchableOpacity style={styles.categoryCard}>
                <View style={[styles.iconWrapper, { backgroundColor: '#FCE7F3' }]}>
                  <Ionicons name="eye-off" size={20} color="#BE185D" />
                </View>
                <Text style={styles.categoryTitle}>Distraction & DUI</Text>
                <Text style={styles.categorySubtitle}>7 rules</Text>
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>

        {/* FLOATING MAP BUTTON */}
        <TouchableOpacity
          style={styles.floatingMapButton}
          onPress={() => router.push('/zones/live')}
        >
          <Ionicons name="map" size={20} color="#fff" style={{ marginRight: 8 }} />
          <Text style={styles.floatingMapButtonText}>Live Map</Text>
        </TouchableOpacity>

      </View>
    </SafeAreaView>
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
  },
  backButton: {
    padding: 4,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1f2937',
  },
  searchButton: {
    padding: 8,
    backgroundColor: '#F3F4F6',
    borderRadius: 20,
  },
  scrollContent: {
    paddingBottom: 100, // Leave space for floating button
  },
  bannerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF7ED',
    marginHorizontal: 20,
    marginTop: 20,
    padding: 16,
    borderRadius: 16,
  },
  bannerIconContainer: {
    marginRight: 12,
  },
  bannerTextContainer: {
    flex: 1,
    marginRight: 12,
  },
  bannerTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#9A3412',
    marginBottom: 4,
  },
  bannerSubtitle: {
    fontSize: 12,
    color: '#57534E',
    lineHeight: 16,
  },
  bannerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#D97706',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
  },
  bannerButtonText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '700',
  },
  sectionContainer: {
    paddingHorizontal: 20,
    marginTop: 32,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#9CA3AF',
    letterSpacing: 1,
    marginBottom: 16,
  },
  gridContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  categoryCard: {
    width: '48%',
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#F3F4F6',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.02,
    shadowRadius: 4,
    elevation: 1,
  },
  iconWrapper: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  categoryTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#1F2937',
    marginBottom: 4,
  },
  categorySubtitle: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  floatingMapButton: {
    position: 'absolute',
    bottom: 24,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1f2937',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderRadius: 30,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 6,
  },
  floatingMapButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
});
