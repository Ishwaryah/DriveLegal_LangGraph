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
import { useGeoFineAlert } from '../../../hooks/useGeoFineAlert';


export default function SpeedLimitsScreen() {
  const router = useRouter();
  const { state, stateCode, locationName, isOffline } = useGeoFineAlert();


  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        
        {/* OFFLINE BANNER */}
        <View style={styles.offlineBanner}>
          <Ionicons name="cloud-offline" size={16} color="#B45309" />
          <Text style={styles.offlineBannerText}>
            {isOffline ? 'Offline' : 'Live'} · Showing rules for {state || 'your region'}
          </Text>
          <Text style={styles.offlineBannerTime}>2 min ago</Text>
        </View>

        {/* HEADER */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Speed limits · {stateCode || 'Global'}</Text>
          <View style={styles.cachedBadge}>
            <Text style={styles.cachedText}>Cached</Text>
          </View>
        </View>

        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
          
          {/* OFFLINE PACK CARD */}
          <View style={styles.packCard}>
            <View style={styles.packIconContainer}>
              <Ionicons name="download-outline" size={20} color="#10B981" />
            </View>
            <View style={styles.packTextContainer}>
              <Text style={styles.packTitle}>{state || 'Local'} offline pack</Text>
              <Text style={styles.packSubtitle}>Active rules for {locationName || 'your current area'}</Text>
            </View>
            <View style={styles.syncedBadge}>
              <Ionicons name="checkmark" size={12} color="#059669" />
              <Text style={styles.syncedText}>Synced</Text>
            </View>
          </View>

          {/* LIST SECTION */}
          <View style={styles.sectionContainer}>
            <Text style={styles.sectionTitle}>SPEED LIMITS BY ROAD TYPE</Text>

            <View style={styles.listContainer}>
              
              {/* Item 1 */}
              <View style={styles.listItem}>
                <View style={styles.speedCircle}>
                  <Text style={styles.speedNumber}>50</Text>
                </View>
                <View style={styles.itemTextContainer}>
                  <Text style={styles.itemTitle}>Urban arterial</Text>
                  <Text style={styles.itemSubtitle}>{locationName || 'Current arterial road'}</Text>
                </View>
              </View>
              
              <View style={styles.divider} />

              {/* Item 2 */}
              <View style={styles.listItem}>
                <View style={styles.speedCircle}>
                  <Text style={styles.speedNumber}>30</Text>
                </View>
                <View style={styles.itemTextContainer}>
                  <Text style={styles.itemTitle}>Residential</Text>
                  <Text style={styles.itemSubtitle}>Inside layouts, lanes</Text>
                </View>
              </View>
              
              <View style={styles.divider} />

              {/* Item 3 */}
              <View style={styles.listItem}>
                <View style={styles.speedCircle}>
                  <Text style={styles.speedNumber}>25</Text>
                </View>
                <View style={styles.itemTextContainer}>
                  <Text style={styles.itemTitle}>School zone</Text>
                  <Text style={styles.itemSubtitle}>8AM–4PM, weekdays</Text>
                </View>
              </View>
              
              <View style={styles.divider} />

              {/* Item 4 */}
              <View style={styles.listItem}>
                <View style={styles.speedCircle}>
                  <Text style={[styles.speedNumber, { fontSize: 16 }]}>100</Text>
                </View>
                <View style={styles.itemTextContainer}>
                  <Text style={styles.itemTitle}>Highway (NH)</Text>
                  <Text style={styles.itemSubtitle}>Cars - 80 for trucks</Text>
                </View>
              </View>
              
              <View style={styles.divider} />

              {/* Item 5 */}
              <View style={styles.listItem}>
                <View style={styles.speedCircle}>
                  <Text style={[styles.speedNumber, { fontSize: 16 }]}>120</Text>
                </View>
                <View style={styles.itemTextContainer}>
                  <Text style={styles.itemTitle}>Expressway</Text>
                  <Text style={styles.itemSubtitle}>GST, Chennai-Bangalore</Text>
                </View>
              </View>

            </View>
            
            <Text style={styles.footerNote}>
              Offline data is read-only. Reconnect to sync the latest amendments and check live geo-fences.
            </Text>
          </View>

        </ScrollView>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#FFFBEB',
  },
  container: {
    flex: 1,
    backgroundColor: '#FAF8F5',
  },
  offlineBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFBEB',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#FEF3C7',
  },
  offlineBannerText: {
    flex: 1,
    fontSize: 12,
    fontWeight: '600',
    color: '#B45309',
    marginLeft: 8,
  },
  offlineBannerTime: {
    fontSize: 11,
    color: '#D97706',
    fontWeight: '500',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 16,
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
    flex: 1,
    fontSize: 18,
    fontWeight: '700',
    color: '#1f2937',
    marginLeft: 12,
  },
  cachedBadge: {
    backgroundColor: '#FFEDD5',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  cachedText: {
    color: '#9A3412',
    fontSize: 12,
    fontWeight: '700',
  },
  scrollContent: {
    paddingBottom: 40,
  },
  packCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    marginHorizontal: 20,
    marginTop: 24,
    padding: 16,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#F3F4F6',
  },
  packIconContainer: {
    marginRight: 12,
  },
  packTextContainer: {
    flex: 1,
    marginRight: 12,
  },
  packTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#1F2937',
    marginBottom: 4,
  },
  packSubtitle: {
    fontSize: 11,
    color: '#9CA3AF',
    lineHeight: 16,
  },
  syncedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#D1FAE5',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  syncedText: {
    color: '#059669',
    fontSize: 10,
    fontWeight: '700',
    marginLeft: 4,
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
  listContainer: {
    backgroundColor: '#fff',
    borderRadius: 16,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: '#F3F4F6',
  },
  listItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
  },
  divider: {
    height: 1,
    backgroundColor: '#F3F4F6',
    marginLeft: 56, // Align with text
  },
  speedCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 3,
    borderColor: '#DC2626',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  speedNumber: {
    fontSize: 18,
    fontWeight: '800',
    color: '#1F2937',
  },
  itemTextContainer: {
    flex: 1,
  },
  itemTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#1F2937',
    marginBottom: 4,
  },
  itemSubtitle: {
    fontSize: 13,
    color: '#6B7280',
  },
  footerNote: {
    marginTop: 20,
    fontSize: 12,
    color: '#9CA3AF',
    lineHeight: 18,
  },
});
