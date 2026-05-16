import { useState } from 'react';
import {
  View, Text, StyleSheet, SafeAreaView, ScrollView, TouchableOpacity,
  TextInput
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { useNetInfo } from '@react-native-community/netinfo';
import { API_BASE } from '../../config/api';
import { useSettings } from '../../hooks/useSettings';



interface VehicleInfo {
  vehicle_number: string;
  owner_name: string;
  registering_authority: string;
  vehicle_class: string;
  fuel_type: string;
  emission_norm: string;
  vehicle_age: string;
  hypothecated: string;
  vehicle_status: string;
  registration_date: string;
  fitness_valid_upto: string;
  tax_valid_upto: string;
  insurance_valid_upto: string;
  pucc_valid_upto: string;
  maker_model: string;
  color: string;
}

interface ChallanItem {
  challan_no: string;
  offence: string;
  amount: number;
  status: string;
  date: string;
}

export default function ChallanCalculatorScreen() {
  const { isConnected } = useNetInfo();
  const { vehicleNumber: savedVehicleNumber, setVehicleNumber } = useSettings();

  const [plateInput, setPlateInput] = useState(savedVehicleNumber || '');

  // Vehicle info state
  const [vehicleInfo, setVehicleInfo] = useState<VehicleInfo | null>(null);
  const [challans, setChallans] = useState<ChallanItem[]>([]);
  const [totalFine, setTotalFine] = useState(0);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState('');

  const lookupVehicle = async () => {
    const plate = plateInput.replace(/[\s-]/g, '').toUpperCase();
    if (plate.length < 6) {
      setLookupError('Enter a valid vehicle number (e.g. TN09AB1234)');
      return;
    }
    setLookupLoading(true);
    setLookupError('');
    setVehicleInfo(null);
    setChallans([]);
    setTotalFine(0);

    try {
      const [infoRes, challanRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/vehicle/info/${plate}`),
        fetch(`${API_BASE}/api/v1/vehicle/challans/${plate}`),
      ]);
      const infoData = await infoRes.json();
      const challanData = await challanRes.json();

      if (infoData.status === 'success') {
        setVehicleInfo(infoData.vehicle_info);
      } else {
        setLookupError(infoData.message || 'Vehicle not found. Check the registration number.');
      }

      if (challanData.status === 'ok' || challanData.status === 'demo') {
        setChallans(challanData.challans || []);
        setTotalFine(challanData.total_fine || 0);
      }
    } catch {
      setLookupError('Could not reach the server. Make sure the backend is running.');
    } finally {
      setLookupLoading(false);
    }
  };

  // ── mParivahan-style Vehicle Search Result screen ─────────────────────────
  if (vehicleInfo) {
    const isActive = vehicleInfo.vehicle_status?.toUpperCase() === 'ACTIVE';
    const fields: [string, string][] = [
      ['Vehicle Number',       vehicleInfo.vehicle_number],
      ['Owner Name',           vehicleInfo.owner_name],
      ['Registering Authority',vehicleInfo.registering_authority],
      ['Vehicle Class',        vehicleInfo.vehicle_class],
      ['Fuel Type',            vehicleInfo.fuel_type],
      ['Emission Norm',        vehicleInfo.emission_norm],
      ['Vehicle Age',          vehicleInfo.vehicle_age],
      ['Hypothecated',         vehicleInfo.hypothecated],
    ];
    const dateFields: [string, string][] = [
      ['Vehicle Status',       vehicleInfo.vehicle_status],
      ['Registration Date',    vehicleInfo.registration_date],
      ['Fitness Valid Upto',   vehicleInfo.fitness_valid_upto],
      ['Tax Valid Upto',       vehicleInfo.tax_valid_upto],
      ['Insurance Valid Upto', vehicleInfo.insurance_valid_upto],
      ['PUCC Valid Upto',      vehicleInfo.pucc_valid_upto],
    ];

    return (
      <SafeAreaView style={styles.container}>
        <StatusBar style="dark" />

        {/* Header */}
        <View style={styles.vsHeader}>
          <TouchableOpacity style={styles.vsBack} onPress={() => setVehicleInfo(null)}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <Text style={styles.vsHeaderTitle}>Vehicle Search</Text>
          <View style={{ width: 40 }} />
        </View>

        <ScrollView style={{ flex: 1, backgroundColor: '#fff' }} contentContainerStyle={{ paddingBottom: 110 }}>
          {/* Top info fields */}
          {fields.map(([label, value]) => (
            <View key={label} style={styles.vsRow}>
              <Text style={styles.vsLabel}>{label}</Text>
              <Text style={styles.vsValue}>{value || '—'}</Text>
            </View>
          ))}

          {/* Impound check link */}
          <TouchableOpacity style={styles.vsLinkRow}>
            <Text style={styles.vsLinkText}>
              Tap to Check the impound/seizure document status
            </Text>
          </TouchableOpacity>

          {/* Date / status fields */}
          {dateFields.map(([label, value]) => (
            <View key={label} style={styles.vsRow}>
              <Text style={styles.vsLabel}>{label}</Text>
              <Text style={[
                styles.vsValue,
                label === 'Vehicle Status' && { color: isActive ? '#16a34a' : '#dc2626', fontWeight: '700' }
              ]}>
                {value || '—'}
              </Text>
            </View>
          ))}

          {/* Pending Challans */}
          <View style={styles.vsChallanHeader}>
            <Ionicons name="receipt-outline" size={18} color="#0891b2" />
            <Text style={styles.vsChallanTitle}>Pending Challans</Text>
            {totalFine > 0 && <Text style={styles.vsChallanTotal}>₹{totalFine} due</Text>}
          </View>

          {challans.length === 0 ? (
            <View style={styles.vsNoChallan}>
              <Ionicons name="checkmark-circle" size={18} color="#16a34a" />
              <Text style={styles.vsNoChallanText}>No pending challans found</Text>
            </View>
          ) : challans.map((c, i) => (
            <View key={i} style={styles.vsChallanRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.vsChallanOffence}>{c.offence}</Text>
                <Text style={styles.vsChallanMeta}>{c.challan_no} · {c.date}</Text>
              </View>
              <View style={{ alignItems: 'flex-end' }}>
                <Text style={styles.vsChallanAmt}>₹{c.amount}</Text>
                <Text style={[styles.vsChallanStatus, { color: c.status === 'Pending' ? '#ef4444' : '#16a34a' }]}>
                  {c.status}
                </Text>
              </View>
            </View>
          ))}
        </ScrollView>

        {/* Bottom action buttons */}
        <View style={styles.vsBottomBar}>
          <TouchableOpacity style={styles.vsBtn}>
            <Text style={styles.vsBtnText}>Create Virtual RC</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.vsBtn, { backgroundColor: '#0369a1' }]}>
            <Text style={styles.vsBtnText}>View Challan</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // ── Vehicle Search — default screen ───────────────────────────────────────
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />

      {/* Header */}
      <View style={styles.vsHeader}>
        <View style={{ width: 40 }} />
        <Text style={styles.vsHeaderTitle}>Vehicle Search</Text>
        <View style={[styles.badge, { backgroundColor: isConnected ? '#dcfce7' : '#fee2e2' }]}>
          <Text style={[styles.badgeText, { color: isConnected ? '#166534' : '#991b1b' }]}>
            {isConnected ? 'Online' : 'Offline'}
          </Text>
        </View>
      </View>

      {/* Search bar */}
      <View style={styles.vsSearchBar}>
        <View style={styles.vsSearchInput}>
          <Ionicons name="car-outline" size={20} color="#6b7280" />
          <TextInput
            style={styles.vsSearchText}
            placeholder="Enter Vehicle Number"
            placeholderTextColor="#9ca3af"
            value={plateInput}
            autoCapitalize="characters"
            returnKeyType="search"
            onSubmitEditing={lookupVehicle}
            onChangeText={text => {
              setPlateInput(text);
              setVehicleNumber(text);
              setLookupError('');
            }}
          />
        </View>
        <TouchableOpacity style={styles.vsSearchBtn} onPress={lookupVehicle} disabled={lookupLoading}>
          <Ionicons name={lookupLoading ? 'sync' : 'search'} size={22} color="#fff" />
        </TouchableOpacity>
      </View>

      {lookupError ? (
        <Text style={styles.lookupError}>{lookupError}</Text>
      ) : null}

      {/* Empty state */}
      {!lookupLoading && (
        <View style={styles.vsEmptyState}>
          <Ionicons name="car-sport-outline" size={72} color="#d1d5db" />
          <Text style={styles.vsEmptyTitle}>Search your vehicle</Text>
          <Text style={styles.vsEmptySubtitle}>
            Enter a registration number to view RC details, insurance, fitness validity and pending challans.
          </Text>
        </View>
      )}

      {lookupLoading && (
        <View style={styles.vsEmptyState}>
          <Ionicons name="sync" size={48} color="#0891b2" />
          <Text style={[styles.vsEmptyTitle, { color: '#0891b2', marginTop: 16 }]}>Fetching vehicle details…</Text>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderColor: '#e2e8f0',
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: '#0f172a',
    letterSpacing: -0.5,
  },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: '700',
  },
  content: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 100,
  },
  plateRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 8,
  },
  plateInputBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingHorizontal: 16,
    height: 52,
    borderRadius: 14,
    borderWidth: 2,
    borderColor: '#6366f1',
    gap: 10,
  },
  plateInput: {
    flex: 1,
    fontSize: 17,
    fontWeight: '700',
    color: '#0f172a',
    letterSpacing: 1,
  },
  lookupBtn: {
    width: 52,
    height: 52,
    borderRadius: 14,
    backgroundColor: '#4f46e5',
    justifyContent: 'center',
    alignItems: 'center',
  },
  lookupError: {
    fontSize: 13,
    color: '#ef4444',
    marginBottom: 12,
    paddingHorizontal: 4,
  },
  // ── Vehicle Search result (mParivahan style) ─────────────────────────────
  vsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  vsBack: {
    width: 40,
    justifyContent: 'center',
  },
  vsHeaderTitle: {
    flex: 1,
    textAlign: 'center',
    fontSize: 17,
    fontWeight: '700',
    color: '#111827',
  },
  vsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 13,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
    backgroundColor: '#fff',
  },
  vsLabel: {
    fontSize: 14,
    color: '#6b7280',
    flex: 1,
  },
  vsValue: {
    fontSize: 14,
    color: '#111827',
    fontWeight: '500',
    flex: 1,
    textAlign: 'right',
  },
  vsLinkRow: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    backgroundColor: '#f0f9ff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0f2fe',
  },
  vsLinkText: {
    fontSize: 13,
    color: '#0284c7',
    fontWeight: '500',
  },
  vsChallanHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 20,
    paddingVertical: 14,
    backgroundColor: '#f8fafc',
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: '#e5e7eb',
    marginTop: 8,
  },
  vsChallanTitle: {
    flex: 1,
    fontSize: 15,
    fontWeight: '700',
    color: '#1e293b',
  },
  vsChallanTotal: {
    fontSize: 13,
    fontWeight: '800',
    color: '#ef4444',
  },
  vsNoChallan: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: '#fff',
  },
  vsNoChallanText: {
    fontSize: 14,
    color: '#16a34a',
    fontWeight: '600',
  },
  vsChallanRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
    backgroundColor: '#fff',
    gap: 12,
  },
  vsChallanOffence: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1e293b',
  },
  vsChallanMeta: {
    fontSize: 11,
    color: '#9ca3af',
    marginTop: 3,
  },
  vsChallanAmt: {
    fontSize: 15,
    fontWeight: '800',
    color: '#ef4444',
  },
  vsChallanStatus: {
    fontSize: 11,
    fontWeight: '600',
    marginTop: 2,
  },
  vsBottomBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    gap: 12,
    padding: 16,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  vsBtn: {
    flex: 1,
    backgroundColor: '#0891b2',
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
  },
  vsBtnText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '700',
  },
  // ── Vehicle Search default screen ─────────────────────────────────────────
  vsSearchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
    gap: 10,
  },
  vsSearchInput: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f3f4f6',
    borderRadius: 10,
    paddingHorizontal: 14,
    height: 48,
    gap: 10,
  },
  vsSearchText: {
    flex: 1,
    fontSize: 15,
    fontWeight: '600',
    color: '#111827',
    letterSpacing: 0.5,
  },
  vsSearchBtn: {
    width: 48,
    height: 48,
    borderRadius: 10,
    backgroundColor: '#0891b2',
    justifyContent: 'center',
    alignItems: 'center',
  },
  vsEmptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
    gap: 12,
  },
  vsEmptyTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#374151',
    marginTop: 12,
  },
  vsEmptySubtitle: {
    fontSize: 14,
    color: '#9ca3af',
    textAlign: 'center',
    lineHeight: 22,
  },
});
