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

export default function DocumentVaultScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>

        {/* HEADER */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Document vault</Text>
          <TouchableOpacity style={styles.addButton}>
            <Text style={styles.addButtonText}>+ Add</Text>
          </TouchableOpacity>
        </View>

        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>

          {/* DRIVING LICENSE CARD */}
          <View style={styles.licenseCard}>
            {/* Top Row */}
            <View style={styles.licenseTopRow}>
              <View>
                <Text style={styles.licenseType}>DRIVING LICENSE</Text>
                <Text style={styles.licenseCountry}>Republic of India - Tamil Nadu</Text>
              </View>
              <View style={styles.verifiedBadge}>
                <Ionicons name="checkmark" size={12} color="#4ADE80" />
                <Text style={styles.verifiedText}>Verified</Text>
              </View>
            </View>

            {/* License Number */}
            <Text style={styles.licenseNumber}>TN09 20210034567</Text>

            {/* Bottom Row */}
            <View style={styles.licenseBottomRow}>
              <View>
                <Text style={styles.licenseFieldLabel}>HOLDER</Text>
                <Text style={styles.licenseFieldValue}>Arjun Krishnan</Text>
              </View>
              <View>
                <Text style={styles.licenseFieldLabel}>VALID TILL</Text>
                <Text style={styles.licenseFieldValue}>14 Jun 2027</Text>
              </View>
              {/* QR Code placeholder */}
              <View style={styles.qrPlaceholder}>
                {[...Array(4)].map((_, i) => (
                  <View key={i} style={styles.qrRow}>
                    {[...Array(4)].map((__, j) => (
                      <View
                        key={j}
                        style={[
                          styles.qrDot,
                          { opacity: Math.random() > 0.4 ? 1 : 0.2 },
                        ]}
                      />
                    ))}
                  </View>
                ))}
              </View>
            </View>
          </View>

          {/* OTHER DOCUMENTS */}
          <Text style={styles.sectionTitle}>OTHER DOCUMENTS</Text>

          <View style={styles.docList}>

            {/* Vehicle RC */}
            <DocItem
              icon="document-outline"
              iconBg="#DCFCE7"
              iconColor="#15803D"
              title="Vehicle RC"
              subtitle="TN 09 BX 4421 · Maruti Swift"
              status="Expires 03 Jul 2032"
              statusColor="#16A34A"
            />

            {/* Insurance */}
            <DocItem
              icon="shield-outline"
              iconBg="#FEF3C7"
              iconColor="#B45309"
              title="Insurance"
              subtitle="Bajaj Allianz · Comprehensive"
              status="Expires in 23 days"
              statusColor="#D97706"
            />

            {/* PUC Certificate */}
            <DocItem
              icon="leaf-outline"
              iconBg="#FCE7F3"
              iconColor="#BE185D"
              title="PUC Certificate"
              subtitle="Pollution under control"
              status="Expired 4 days ago"
              statusColor="#DC2626"
            />

            {/* FasTag */}
            <DocItem
              icon="cellular-outline"
              iconBg="#E0F2FE"
              iconColor="#0369A1"
              title="FasTag"
              subtitle="HDFC · Linked"
              status="Active"
              statusColor="#16A34A"
              isLast
            />

          </View>

        </ScrollView>
      </View>
    </SafeAreaView>
  );
}

interface DocItemProps {
  icon: string;
  iconBg: string;
  iconColor: string;
  title: string;
  subtitle: string;
  status: string;
  statusColor: string;
  isLast?: boolean;
}

function DocItem({ icon, iconBg, iconColor, title, subtitle, status, statusColor, isLast }: DocItemProps) {
  return (
    <>
      <TouchableOpacity style={styles.docItem}>
        <View style={[styles.docIconWrapper, { backgroundColor: iconBg }]}>
          <Ionicons name={icon as any} size={20} color={iconColor} />
        </View>
        <View style={styles.docTextContainer}>
          <Text style={styles.docTitle}>{title}</Text>
          <Text style={styles.docSubtitle}>{subtitle}</Text>
          <Text style={[styles.docStatus, { color: statusColor }]}>{status}</Text>
        </View>
        <Ionicons name="chevron-forward" size={20} color="#D1D5DB" />
      </TouchableOpacity>
      {!isLast && <View style={styles.docDivider} />}
    </>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#fff' },
  container: { flex: 1, backgroundColor: '#FAF8F5' },

  // Header
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: Platform.OS === 'android' ? 40 : 10,
    paddingBottom: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  backButton: { padding: 4 },
  headerTitle: { fontSize: 18, fontWeight: '700', color: '#1f2937' },
  addButton: { padding: 4 },
  addButtonText: { fontSize: 15, fontWeight: '700', color: '#D97706' },

  scrollContent: { paddingBottom: 40, paddingHorizontal: 20, paddingTop: 24 },

  // Driving License Card
  licenseCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 20,
    padding: 20,
    gap: 16,
    marginBottom: 32,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.3,
    shadowRadius: 16,
    elevation: 8,
  },
  licenseTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  licenseType: {
    fontSize: 11,
    fontWeight: '700',
    color: '#9CA3AF',
    letterSpacing: 1,
    marginBottom: 4,
  },
  licenseCountry: { fontSize: 12, color: '#6B7280' },
  verifiedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(74,222,128,0.15)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
    borderWidth: 1,
    borderColor: 'rgba(74,222,128,0.3)',
  },
  verifiedText: { fontSize: 11, fontWeight: '700', color: '#4ADE80' },

  licenseNumber: {
    fontSize: 26,
    fontWeight: '800',
    color: '#F9FAFB',
    letterSpacing: 2,
  },

  licenseBottomRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 24,
  },
  licenseFieldLabel: {
    fontSize: 10,
    color: '#6B7280',
    fontWeight: '700',
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  licenseFieldValue: { fontSize: 14, fontWeight: '700', color: '#F9FAFB' },

  // QR Code visual
  qrPlaceholder: {
    marginLeft: 'auto',
    gap: 3,
  },
  qrRow: { flexDirection: 'row', gap: 3 },
  qrDot: {
    width: 7,
    height: 7,
    borderRadius: 1,
    backgroundColor: '#9CA3AF',
  },

  // Section title
  sectionTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#9CA3AF',
    letterSpacing: 1,
    marginBottom: 16,
  },

  // Doc list
  docList: {
    backgroundColor: '#fff',
    borderRadius: 16,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: '#F3F4F6',
  },
  docItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    gap: 14,
  },
  docIconWrapper: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  docTextContainer: { flex: 1, gap: 2 },
  docTitle: { fontSize: 15, fontWeight: '700', color: '#1F2937' },
  docSubtitle: { fontSize: 13, color: '#6B7280' },
  docStatus: { fontSize: 12, fontWeight: '600', marginTop: 2 },
  docDivider: { height: 1, backgroundColor: '#F9FAFB', marginLeft: 58 },
});
