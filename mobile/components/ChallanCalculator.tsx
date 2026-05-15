import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Animated,
  useWindowDimensions
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';



interface Challan {
  date: string;
  violation: string;
  amount: number;
  status: string;
  location: string;
}

interface ChallanData {
  vehicle_number: string;
  owner: string;
  vehicle_type: string;
  pending_challans: Challan[];
  total_fine: number;
  last_updated: string;
  message?: string;
}

export const ChallanCalculator = ({ onClose }: { onClose: () => void }) => {
  const { width, height } = useWindowDimensions();
  const isSmallScreen = width < 480;
  const [vehicleNumber, setVehicleNumber] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ChallanData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const calculateChallan = async () => {
    if (!vehicleNumber.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://127.0.0.1:8001/challan/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vehicle_number: vehicleNumber }),
      });
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError('Failed to connect to official server.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={['#1e293b', '#0f172a']}
        style={styles.gradient}
      >
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Challan Calculator</Text>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Ionicons name="close" size={24} color="#94a3b8" />
          </TouchableOpacity>
        </View>

        <View style={styles.inputSection}>
          <Text style={styles.label}>Vehicle Registration Number</Text>
          <View style={styles.searchContainer}>
            <TextInput
              style={styles.input}
              placeholder="e.g. TN-01-AB-1234"
              placeholderTextColor="#64748b"
              value={vehicleNumber}
              onChangeText={setVehicleNumber}
              autoCapitalize="characters"
            />
            <TouchableOpacity 
              style={styles.calcButton} 
              onPress={calculateChallan}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Ionicons name="search" size={20} color="#fff" />
              )}
            </TouchableOpacity>
          </View>
        </View>

        <ScrollView style={styles.resultsArea} showsVerticalScrollIndicator={false}>
          {data && (
            <Animated.View style={styles.card}>
              <View style={styles.cardHeader}>
                <View>
                  <Text style={styles.ownerName}>{data.owner || 'Vehicle Info'}</Text>
                  <Text style={styles.vehicleType}>{data.vehicle_type || data.vehicle_number}</Text>
                </View>
                <View style={[styles.totalBadge, isSmallScreen && { alignItems: 'flex-start', marginTop: 8 }]}>
                  <Text style={styles.totalLabel}>TOTAL FINE</Text>
                  <Text style={styles.totalAmount}>₹{data.total_fine ?? 0}</Text>
                </View>
              </View>

              {(data.pending_challans?.length ?? 0) > 0 ? (
                <View style={styles.challanList}>
                  <Text style={styles.sectionTitle}>Pending Violations</Text>
                  {data.pending_challans?.map((c, i) => (
                    <View key={i} style={styles.challanItem}>
                      <View style={styles.challanInfo}>
                        <Text style={styles.violationText}>{c.violation}</Text>
                        <Text style={styles.locationText}>{c.location} • {c.date}</Text>
                      </View>
                      <Text style={styles.itemAmount}>₹{c.amount}</Text>
                    </View>
                  ))}
                </View>
              ) : (
                <View style={styles.emptyState}>
                  <Ionicons name="checkmark-circle" size={48} color="#10b981" />
                  <Text style={styles.emptyText}>{data.message || 'No pending challans found!'}</Text>
                </View>
              )}
              
              <View style={styles.footer}>
                <Text style={styles.updatedText}>Last updated from RTO: {data.last_updated ? new Date(data.last_updated).toLocaleDateString() : 'Unknown'}</Text>
              </View>
            </Animated.View>
          )}

          {error && (
            <View style={styles.errorCard}>
              <Ionicons name="alert-circle" size={20} color="#ef4444" />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}
        </ScrollView>
      </LinearGradient>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    height: 520,
    maxHeight: '90%',
    width: '100%',
    borderRadius: 24,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#334155',
    backgroundColor: '#0f172a',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.5,
    shadowRadius: 20,
    elevation: 10,
  },
  gradient: {
    flex: 1,
    padding: 24,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#f8fafc',
  },
  closeButton: {
    padding: 4,
  },
  inputSection: {
    marginBottom: 24,
  },
  label: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  searchContainer: {
    flexDirection: 'row',
    backgroundColor: '#1e293b',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#334155',
    overflow: 'hidden',
  },
  input: {
    flex: 1,
    paddingHorizontal: 16,
    paddingVertical: 12,
    color: '#fff',
    fontSize: 16,
  },
  calcButton: {
    width: 50,
    backgroundColor: '#10b981',
    justifyContent: 'center',
    alignItems: 'center',
  },
  resultsArea: {
    flex: 1,
  },
  card: {
    backgroundColor: '#1e293b',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#334155',
  },
  cardHeader: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#334155',
    paddingBottom: 16,
  },
  ownerName: {
    fontSize: 18,
    fontWeight: '700',
    color: '#f8fafc',
  },
  vehicleType: {
    fontSize: 13,
    color: '#64748b',
    marginTop: 2,
  },
  totalBadge: {
    alignItems: 'flex-end',
  },
  totalLabel: {
    fontSize: 10,
    color: '#94a3b8',
    fontWeight: '600',
  },
  totalAmount: {
    fontSize: 22,
    fontWeight: '800',
    color: '#10b981',
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#94a3b8',
    marginBottom: 12,
    textTransform: 'uppercase',
  },
  challanList: {
    gap: 12,
  },
  challanItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#0f172a',
    padding: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#1e293b',
  },
  challanInfo: {
    flex: 1,
    paddingRight: 10,
  },
  violationText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#e2e8f0',
  },
  locationText: {
    fontSize: 12,
    color: '#64748b',
    marginTop: 2,
  },
  itemAmount: {
    fontSize: 14,
    fontWeight: '700',
    color: '#ef4444',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 20,
    gap: 12,
  },
  emptyText: {
    color: '#94a3b8',
    fontSize: 14,
    textAlign: 'center',
  },
  footer: {
    marginTop: 20,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#334155',
  },
  updatedText: {
    fontSize: 11,
    color: '#64748b',
    textAlign: 'center',
  },
  errorCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.2)',
    gap: 10,
  },
  errorText: {
    color: '#ef4444',
    fontSize: 14,
  }
});
