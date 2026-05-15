import React, { useState, useEffect, useMemo } from 'react';
import { 
  View, Text, StyleSheet, SafeAreaView, ScrollView, TouchableOpacity,
  TextInput, Switch, Modal, Share, ActivityIndicator, Platform 
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useNetInfo } from '@react-native-community/netinfo';
// SQLite is loaded conditionally
import { Violation, CalculateResponse } from '../../types/challan';
import { API_BASE } from '../../config/api';
import { LinearGradient } from 'expo-linear-gradient';

const db = Platform.OS !== 'web' ? require('expo-sqlite').openDatabase('fines.db') : null;

const COUNTRIES = [
  { code: 'IN', name: 'India', flag: '🇮🇳' },
  { code: 'AE', name: 'UAE', flag: '🇦🇪' },
  { code: 'SG', name: 'Singapore', flag: '🇸🇬' },
  { code: 'GB', name: 'UK', flag: '🇬🇧' },
];

const STATES = [
  'Tamil Nadu', 'Maharashtra', 'Karnataka', 'Delhi', 'Gujarat', 'Telangana', 'Other'
];

const VEHICLE_TYPES = [
  { id: 'two_wheeler', label: 'Two Wheeler', icon: 'motorbike' },
  { id: 'three_wheeler', label: 'Three Wheeler', icon: 'taxi' },
  { id: 'lmv', label: 'LMV', icon: 'car' },
  { id: 'hmv', label: 'HMV', icon: 'truck' },
  { id: 'commercial', label: 'Commercial', icon: 'bus' },
];

const getCategory = (name: string) => {
  const lower = name.toLowerCase();
  if (lower.includes('speed') || lower.includes('race')) return 'Speed';
  if (lower.includes('license') || lower.includes('rc') || lower.includes('document')) return 'Documentation';
  if (lower.includes('helmet') || lower.includes('seatbelt') || lower.includes('light')) return 'Safety Equipment';
  if (lower.includes('drunk') || lower.includes('alcohol') || lower.includes('substance')) return 'Substance';
  return 'Other';
};

export default function ChallanCalculatorScreen() {
  const { isConnected } = useNetInfo();
  
  const [selectedCountry, setSelectedCountry] = useState('IN');
  const [selectedState, setSelectedState] = useState('Tamil Nadu');
  const [selectedVehicle, setSelectedVehicle] = useState('two_wheeler');
  const [isRepeatOffense, setIsRepeatOffense] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  const [violations, setViolations] = useState<Violation[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [errorState, setErrorState] = useState(false);
  
  const [showResultModal, setShowResultModal] = useState(false);
  const [calcResult, setCalcResult] = useState<CalculateResponse | null>(null);

  const fetchViolations = async () => {
    setLoading(true);
    setErrorState(false);
    if (isConnected) {
      try {
        const stateQuery = selectedCountry === 'IN' ? `&state_province=${encodeURIComponent(selectedState)}` : '';
        const vType = selectedCountry === 'IN' ? selectedVehicle : 'all';
        const res = await fetch(`${API_BASE}/api/v1/fines/country/${selectedCountry}?vehicle_type=${vType}${stateQuery}`);
        const data = await res.json();
        
        if (Array.isArray(data)) {
          setViolations(data);
          // Sync to SQLite for offline use
          if (db) db.transaction(tx => {
            tx.executeSql('DELETE FROM fines WHERE country = ?', [selectedCountry]);
            data.forEach((v: Violation) => {
              tx.executeSql(`
                INSERT INTO fines (country, state_province, violation_code, violation_name, vehicle_type, min_fine_local, max_fine_local, currency, mv_act_section, compounding_eligible, compounding_fee)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
              `, [
                selectedCountry, selectedCountry === 'IN' ? selectedState : 'ALL', 
                v.violation_code, v.violation_name, v.vehicle_type || 'all',
                v.min_fine_local, v.max_fine_local, v.currency, v.mv_act_section,
                v.compounding_eligible ? 1 : 0, v.compounding_fee
              ]);
            });
          });
        }
      } catch (err) {
        console.error('API Error:', err);
        setErrorState(true);
        loadOfflineViolations();
      }
    } else {
      loadOfflineViolations();
    }
    setLoading(false);
  };

  const loadOfflineViolations = () => {
    if (!db) return;
    db.transaction(tx => {
      tx.executeSql(
        'SELECT * FROM fines WHERE country = ?',
        [selectedCountry],
        (_, { rows }) => {
          // @ts-ignore
          let data = rows._array as Violation[];
          if (selectedCountry === 'IN') {
             data = data.filter(v => v.state_province === selectedState || v.state_province === 'ALL');
             data = data.filter(v => v.vehicle_type === selectedVehicle || v.vehicle_type === 'all');
          }
          setViolations(data);
        }
      );
    });
  };

  useEffect(() => {
    fetchViolations();
    setSelectedIds(new Set()); // reset selection on filters change
  }, [selectedCountry, selectedState, selectedVehicle, isConnected]);

  const filteredAndGroupedViolations = useMemo(() => {
    let filtered = violations;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(v => 
        v.violation_name.toLowerCase().includes(q) || 
        (v.mv_act_section && v.mv_act_section.toLowerCase().includes(q))
      );
    }
    
    const groups: Record<string, Violation[]> = {};
    filtered.forEach(v => {
      const cat = getCategory(v.violation_name);
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(v);
    });
    return groups;
  }, [violations, searchQuery]);

  const toggleSelection = (code: string) => {
    const next = new Set(selectedIds);
    if (next.has(code)) next.delete(code);
    else next.add(code);
    setSelectedIds(next);
  };

  const calculateFine = async () => {
    if (selectedIds.size === 0) return;
    
    const codes = Array.from(selectedIds);
    
    if (isConnected) {
      try {
        const payload = {
          violation_codes: codes,
          vehicle_type: selectedCountry === 'IN' ? selectedVehicle : 'all',
          country: selectedCountry,
          state_province: selectedCountry === 'IN' ? selectedState : undefined,
          is_repeat_offense: isRepeatOffense
        };
        const res = await fetch(`${API_BASE}/api/v1/challan/calculate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        setCalcResult(data);
        setShowResultModal(true);
        return;
      } catch (e) {
        console.error(e);
      }
    }
    
    // Offline Calculation
    let total = 0;
    let totalCompounding = 0;
    let allCompoundable = true;
    const resultViols: any[] = [];
    const currency = violations[0]?.currency || 'INR';

    codes.forEach(code => {
      const v = violations.find(vi => vi.violation_code === code);
      if (v) {
        // Fallback calculation logic based on repeat offense
        const amount = isRepeatOffense ? (v.max_fine_local || v.min_fine_local || 0) : (v.min_fine_local || v.max_fine_local || 0);
        total += amount;
        if (v.compounding_eligible && v.compounding_fee) {
          totalCompounding += v.compounding_fee;
        } else {
          allCompoundable = false;
        }
        resultViols.push({
          violation_code: v.violation_code,
          violation_name: v.violation_name,
          fine_amount: amount,
          compounding_fee: v.compounding_fee,
          is_compoundable: !!v.compounding_eligible
        });
      }
    });

    setCalcResult({
      currency,
      total_fine: total,
      compounding_available: allCompoundable && totalCompounding > 0,
      total_compounding_fee: totalCompounding,
      violations: resultViols
    });
    setShowResultModal(true);
  };

  const shareSummary = async () => {
    if (!calcResult) return;
    const items = calcResult.violations.map(v => `- ${v.violation_name}: ${calcResult.currency} ${v.fine_amount}`).join('\n');
    const text = `Challan Summary:\n${items}\n\nTotal Fine: ${calcResult.currency} ${calcResult.total_fine}\n${calcResult.compounding_available ? `Compoundable for: ${calcResult.currency} ${calcResult.total_compounding_fee}` : 'Not Compoundable'}`;
    await Share.share({ message: text });
  };

  const showHMV = selectedCountry === 'IN';

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />
      
      {/* Header & Connectivity Badge */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Challan Calculator</Text>
        <View style={[styles.badge, { backgroundColor: isConnected ? '#dcfce7' : '#fee2e2' }]}>
          <Text style={[styles.badgeText, { color: isConnected ? '#166534' : '#991b1b' }]}>
            {isConnected ? '🟢 Online' : '🔴 Offline – Cached'}
          </Text>
        </View>
      </View>

      <ScrollView style={styles.content} contentContainerStyle={styles.scrollContent}>
        
        {/* Country Selector */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.countryScroll}>
          {COUNTRIES.map(c => (
            <TouchableOpacity 
              key={c.code}
              style={[styles.pillBtn, selectedCountry === c.code && styles.pillBtnActive]}
              onPress={() => {
                setSelectedCountry(c.code);
                if (c.code !== 'IN') setSelectedVehicle('lmv');
              }}
            >
              <Text style={[styles.pillText, selectedCountry === c.code && styles.pillTextActive]}>
                {c.flag} {c.name}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* State Selector (India Only) */}
        {selectedCountry === 'IN' && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>State/Province</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {STATES.map(s => (
                <TouchableOpacity 
                  key={s}
                  style={[styles.stateBtn, selectedState === s && styles.stateBtnActive]}
                  onPress={() => setSelectedState(s)}
                >
                  <Text style={[styles.stateText, selectedState === s && styles.stateTextActive]}>{s}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        )}

        {/* Vehicle Selector */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Vehicle Type</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.vehicleRow}>
            {VEHICLE_TYPES.filter(v => showHMV || (v.id !== 'hmv' && v.id !== 'commercial')).map(v => (
              <TouchableOpacity 
                key={v.id}
                style={[styles.vehicleCard, selectedVehicle === v.id && styles.vehicleCardActive]}
                onPress={() => setSelectedVehicle(v.id)}
              >
                <MaterialCommunityIcons 
                  name={v.icon as any} 
                  size={28} 
                  color={selectedVehicle === v.id ? '#6366f1' : '#64748b'} 
                />
                <Text style={[styles.vehicleText, selectedVehicle === v.id && styles.vehicleTextActive]}>
                  {v.label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* Search */}
        <View style={styles.searchBox}>
          <Ionicons name="search" size={20} color="#94a3b8" />
          <TextInput 
            style={styles.searchInput}
            placeholder="Search violations..."
            placeholderTextColor="#94a3b8"
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
        </View>

        {/* Repeat Offense Toggle */}
        <View style={styles.toggleRow}>
          <Text style={styles.toggleText}>First Offense</Text>
          <Switch 
            value={isRepeatOffense} 
            onValueChange={setIsRepeatOffense}
            trackColor={{ false: '#cbd5e1', true: '#a5b4fc' }}
            thumbColor={isRepeatOffense ? '#4f46e5' : '#f8fafc'}
          />
          <Text style={[styles.toggleText, isRepeatOffense && styles.toggleTextActive]}>Repeat Offense</Text>
        </View>

        {/* Violations List */}
        {loading ? (
          <View style={{ marginTop: 20 }}>
            {[1, 2, 3, 4, 5].map(i => (
              <View key={i} style={{ backgroundColor: '#e2e8f0', height: 60, borderRadius: 12, marginBottom: 10, opacity: 0.5 }} />
            ))}
          </View>
        ) : errorState && violations.length === 0 ? (
          <View style={{ alignItems: 'center', marginTop: 60 }}>
            <Ionicons name="cloud-offline" size={60} color="#94a3b8" />
            <Text style={{ fontSize: 18, color: '#475569', marginTop: 16 }}>Network Error</Text>
            <TouchableOpacity style={{ marginTop: 16, padding: 12, backgroundColor: '#4f46e5', borderRadius: 8 }} onPress={fetchViolations}>
              <Text style={{ color: '#fff', fontWeight: 'bold' }}>Retry Connection</Text>
            </TouchableOpacity>
          </View>
        ) : Object.keys(filteredAndGroupedViolations).length === 0 ? (
          <View style={{ alignItems: 'center', marginTop: 60 }}>
            <Ionicons name="document-text-outline" size={60} color="#cbd5e1" />
            <Text style={{ fontSize: 16, color: '#475569', marginTop: 16, fontWeight: 'bold' }}>No violations found</Text>
            <Text style={{ fontSize: 14, color: '#94a3b8', marginTop: 8, textAlign: 'center' }}>Try searching with different keywords or changing the selected state.</Text>
          </View>
        ) : (
          Object.entries(filteredAndGroupedViolations).map(([category, items]) => (
            <View key={category} style={styles.categoryGroup}>
              <Text style={styles.categoryTitle}>{category}</Text>
              <View style={styles.listContainer}>
                {items.map((item, idx) => {
                  const isSelected = selectedIds.has(item.violation_code);
                  return (
                    <TouchableOpacity 
                      key={`${item.violation_code}-${idx}`} 
                      style={[styles.itemRow, isSelected && styles.itemRowSelected]}
                      onPress={() => toggleSelection(item.violation_code)}
                      activeOpacity={0.7}
                      accessibilityLabel={item.violation_name}
                      accessibilityHint="Selects this violation to add to calculation"
                    >
                      <View style={[styles.checkbox, isSelected && styles.checkboxSelected]}>
                        {isSelected && <Ionicons name="checkmark" size={14} color="#fff" />}
                      </View>
                      <View style={styles.itemTextContainer}>
                        <Text style={styles.itemTitle}>{item.violation_name}</Text>
                        {item.mv_act_section && (
                          <Text style={styles.itemSubtitle}>{item.mv_act_section}</Text>
                        )}
                      </View>
                      <Text style={styles.itemAmount}>
                        {item.currency} {item.min_fine_local}
                        {item.max_fine_local && item.max_fine_local !== item.min_fine_local ? `–${item.max_fine_local}` : ''}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>
          ))
        )}

      </ScrollView>

      {/* Calculate Sticky Button */}
      {selectedIds.size > 0 && (
        <View style={styles.bottomBar}>
          <TouchableOpacity style={styles.calcBtn} onPress={calculateFine}>
            <LinearGradient colors={['#4f46e5', '#4338ca']} style={styles.calcBtnGradient}>
              <Text style={styles.calcBtnText}>Calculate {selectedIds.size} Violations</Text>
              <Ionicons name="calculator" size={20} color="#fff" />
            </LinearGradient>
          </TouchableOpacity>
        </View>
      )}

      {/* Result Modal */}
      <Modal visible={showResultModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Calculation Result</Text>
              <TouchableOpacity onPress={() => setShowResultModal(false)}>
                <Ionicons name="close-circle" size={28} color="#94a3b8" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalScroll}>
              {calcResult?.violations.map((v, i) => (
                <View key={i} style={styles.resultCard}>
                  <Text style={styles.resultVioName}>{v.violation_name}</Text>
                  <Text style={styles.resultVioAmt}>{calcResult.currency} {v.fine_amount}</Text>
                </View>
              ))}

              <View style={styles.totalBox}>
                <Text style={styles.totalLabel}>Total Fine</Text>
                <Text style={styles.totalValue}>{calcResult?.currency} {calcResult?.total_fine}</Text>
              </View>

              {calcResult?.compounding_available && (
                <View style={styles.compoundingBox}>
                  <Ionicons name="shield-checkmark" size={20} color="#10b981" />
                  <Text style={styles.compoundingText}>
                    Pay <Text style={styles.boldText}>{calcResult.currency} {calcResult.total_compounding_fee}</Text> to compound (settle without court)
                  </Text>
                </View>
              )}

              <Text style={styles.disclaimerText}>
                Disclaimer: Amounts shown are estimates and subject to change based on actual traffic police jurisdiction and latest amendments.
              </Text>
            </ScrollView>

            <TouchableOpacity style={styles.shareBtn} onPress={shareSummary}>
              <Ionicons name="share-social" size={20} color="#fff" />
              <Text style={styles.shareBtnText}>Share Summary</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

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
  countryScroll: {
    marginBottom: 20,
  },
  pillBtn: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: '#fff',
    marginRight: 10,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  pillBtnActive: {
    backgroundColor: '#eff6ff',
    borderColor: '#6366f1',
  },
  pillText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#64748b',
  },
  pillTextActive: {
    color: '#4f46e5',
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1e293b',
    marginBottom: 12,
  },
  stateBtn: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: '#f1f5f9',
    marginRight: 8,
  },
  stateBtnActive: {
    backgroundColor: '#1e293b',
  },
  stateText: {
    fontSize: 14,
    color: '#475569',
    fontWeight: '500',
  },
  stateTextActive: {
    color: '#fff',
  },
  vehicleRow: {
    gap: 12,
  },
  vehicleCard: {
    width: 80,
    height: 80,
    borderRadius: 16,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#e2e8f0',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  vehicleCardActive: {
    borderColor: '#6366f1',
    backgroundColor: '#e0e7ff',
  },
  vehicleText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#64748b',
    marginTop: 6,
  },
  vehicleTextActive: {
    color: '#4f46e5',
  },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingHorizontal: 16,
    height: 50,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    marginBottom: 20,
  },
  searchInput: {
    flex: 1,
    marginLeft: 10,
    fontSize: 16,
    color: '#0f172a',
  },
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    paddingVertical: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    marginBottom: 24,
  },
  toggleText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#64748b',
    marginHorizontal: 12,
  },
  toggleTextActive: {
    color: '#1e293b',
  },
  categoryGroup: {
    marginBottom: 24,
  },
  categoryTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 10,
    marginLeft: 4,
  },
  listContainer: {
    backgroundColor: '#fff',
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  itemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  itemRowSelected: {
    backgroundColor: '#e0e7ff',
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: '#cbd5e1',
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxSelected: {
    backgroundColor: '#6366f1',
    borderColor: '#6366f1',
  },
  itemTextContainer: {
    flex: 1,
    marginLeft: 14,
    marginRight: 10,
  },
  itemTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 2,
  },
  itemSubtitle: {
    fontSize: 12,
    color: '#64748b',
  },
  itemAmount: {
    fontSize: 15,
    fontWeight: '800',
    color: '#4f46e5',
  },
  bottomBar: {
    position: 'absolute',
    bottom: 20,
    left: 20,
    right: 20,
  },
  calcBtn: {
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: '#4f46e5',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 8,
  },
  calcBtnGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 18,
    gap: 10,
  },
  calcBtnText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.6)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    maxHeight: '85%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: '#0f172a',
  },
  modalScroll: {
    marginBottom: 20,
  },
  resultCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  resultVioName: {
    fontSize: 15,
    fontWeight: '500',
    color: '#334155',
    flex: 1,
    paddingRight: 10,
  },
  resultVioAmt: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0f172a',
  },
  totalBox: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#f8fafc',
    padding: 20,
    borderRadius: 16,
    marginTop: 20,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  totalLabel: {
    fontSize: 18,
    fontWeight: '700',
    color: '#64748b',
  },
  totalValue: {
    fontSize: 28,
    fontWeight: '800',
    color: '#4f46e5',
  },
  compoundingBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ecfdf5',
    padding: 16,
    borderRadius: 12,
    marginTop: 16,
    borderWidth: 1,
    borderColor: '#a7f3d0',
    gap: 12,
  },
  compoundingText: {
    flex: 1,
    fontSize: 14,
    color: '#065f46',
    lineHeight: 20,
  },
  boldText: {
    fontWeight: '800',
    fontSize: 16,
  },
  disclaimerText: {
    fontSize: 11,
    color: '#94a3b8',
    marginTop: 24,
    textAlign: 'center',
    lineHeight: 16,
  },
  shareBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1e293b',
    paddingVertical: 16,
    borderRadius: 16,
    gap: 8,
  },
  shareBtnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  }
});
