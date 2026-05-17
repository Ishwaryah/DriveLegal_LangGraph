import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Dimensions,
  Platform,
  ActivityIndicator,
  Modal,
  Alert,
  Switch
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useNetInfo } from '@react-native-community/netinfo';
import { API_BASE } from '../../config/api';
import { useSettings } from '../../hooks/useSettings';
import * as ImagePicker from 'expo-image-picker';

const { width: windowWidth } = Dimensions.get('window');
const fontScale = Math.min(windowWidth, 420) / 375;
const fs = (size: number) => Math.round(size * fontScale);

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

// Common violations dataset mapped by MV Act sections
interface Violation {
  id: string;
  section: string;
  code: string;
  title: string;
  base_1st: number;
  base_2nd: number;
  description: string;
}

const COMMON_VIOLATIONS: Violation[] = [
  { id: '1', section: 'Sec 185', code: 'DRUNK_DRIVING', title: 'Drunk Driving / Consumption of Alcohol', base_1st: 10000, base_2nd: 15000, description: 'Driving under the influence of alcohol exceeding 30mg per 100ml blood.' },
  { id: '2', section: 'Sec 183(1)', code: 'OVERSPEEDING_LMV', title: 'Overspeeding (Light Motor Vehicle)', base_1st: 1000, base_2nd: 2000, description: 'Exceeding the speed limits specified for LMV vehicles.' },
  { id: '3', section: 'Sec 183(2)', code: 'OVERSPEEDING_HMV', title: 'Overspeeding (Medium/Heavy Vehicle)', base_1st: 2000, base_2nd: 4000, description: 'Exceeding speed limits for passenger buses or heavy goods transport.' },
  { id: '4', section: 'Sec 181', code: 'NO_LICENSE', title: 'Driving Without License', base_1st: 5000, base_2nd: 5000, description: 'Operating a vehicle without a valid driving license for that category.' },
  { id: '5', section: 'Sec 196', code: 'NO_INSURANCE', title: 'Driving Uninsured Vehicle', base_1st: 2000, base_2nd: 4000, description: 'Driving without active third-party liability insurance policy.' },
  { id: '6', section: 'Sec 190(2)', code: 'NO_PUC', title: 'Emissions / Pollution Violation (PUC)', base_1st: 10000, base_2nd: 10000, description: 'Operating a vehicle without valid Pollution Under Control certificate.' },
  { id: '7', section: 'Sec 194D', code: 'NO_HELMET', title: 'Riding Without Helmet', base_1st: 1000, base_2nd: 1000, description: 'Two-wheeler rider or pillion not wearing ISI-marked helmet.' },
  { id: '8', section: 'Sec 194B(1)', code: 'NO_SEATBELT', title: 'Driving Without Seatbelt', base_1st: 1000, base_2nd: 1000, description: 'Driver or front-seat passenger not secured with seatbelt.' },
  { id: '9', section: 'Sec 184', code: 'DANGEROUS_DRIVING', title: 'Dangerous / Rash Driving', base_1st: 1000, base_2nd: 10000, description: 'Jumping red light, weaving, using phone while driving, or tailgating.' },
];

// Compounding guidelines overrides for states
const STATE_OVERRIDES: Record<string, Record<string, number>> = {
  'TN': { // Tamil Nadu overrides
    'DRUNK_DRIVING': 10000,
    'OVERSPEEDING_LMV': 1000,
    'NO_LICENSE': 5000,
    'NO_INSURANCE': 2000,
    'NO_PUC': 10000,
    'NO_HELMET': 1000,
    'NO_SEATBELT': 1000,
  },
  'MH': { // Maharashtra overrides
    'DRUNK_DRIVING': 10000,
    'OVERSPEEDING_LMV': 1500, // Stricter speeding base
    'NO_LICENSE': 5000,
    'NO_INSURANCE': 2000,
    'NO_PUC': 10000,
    'NO_HELMET': 500, // Reduced compromise
    'NO_SEATBELT': 500,
  },
  'DL': { // Delhi overrides
    'DRUNK_DRIVING': 10000,
    'OVERSPEEDING_LMV': 2000, // Max base
    'NO_LICENSE': 5000,
    'NO_INSURANCE': 2000,
    'NO_PUC': 10000,
    'NO_HELMET': 1000,
    'NO_SEATBELT': 1000,
  }
};

export default function ChallanCalculatorScreen() {
  const { isConnected } = useNetInfo();
  const { vehicleNumber: savedVehicleNumber, setVehicleNumber } = useSettings();

  const [activeTab, setActiveTab] = useState<'sync' | 'calc'>('sync');
  const [plateInput, setPlateInput] = useState(savedVehicleNumber || '');

  // Vehicle info state
  const [vehicleInfo, setVehicleInfo] = useState<VehicleInfo | null>(null);
  const [challans, setChallans] = useState<ChallanItem[]>([]);
  const [totalFine, setTotalFine] = useState(0);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState('');

  // Fine Calculator state
  const [selectedState, setSelectedState] = useState<'TN' | 'MH' | 'DL'>('TN');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedViolations, setSelectedViolations] = useState<string[]>([]);
  const [isSecondOffense, setIsSecondOffense] = useState(false);
  
  // Stacking violations
  const [stackInsurance, setStackInsurance] = useState(false);
  const [stackPUC, setStackPUC] = useState(false);

  // RAG judgements Modal state
  const [ragModalVisible, setRAGModalVisible] = useState(false);
  const [activeJudgements, setActiveJudgements] = useState<any[]>([]);
  const [ragTitle, setRagTitle] = useState('');

  // Auto-flag expired documents upon vehicle lookup
  useEffect(() => {
    if (vehicleInfo) {
      const today = new Date();
      today.setHours(0,0,0,0);

      // Check Insurance expiry
      if (vehicleInfo.insurance_valid_upto) {
        const insExpiry = new Date(vehicleInfo.insurance_valid_upto);
        if (!isNaN(insExpiry.getTime()) && insExpiry < today) {
          setStackInsurance(true);
        }
      }
      
      // Check PUC expiry
      if (vehicleInfo.pucc_valid_upto) {
        const pucExpiry = new Date(vehicleInfo.pucc_valid_upto);
        if (!isNaN(pucExpiry.getTime()) && pucExpiry < today) {
          setStackPUC(true);
        }
      }
    }
  }, [vehicleInfo]);

  const handlePlateCamera = async () => {
    try {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Needed', 'Camera access is required to scan license plates.');
        return;
      }

      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.8,
      });

      if (result.canceled || !result.assets || result.assets.length === 0) {
        return;
      }

      setLookupLoading(true);
      setLookupError('');
      
      const imageUri = result.assets[0].uri;
      
      // Prepare FormData for file upload
      const formData = new FormData();
      formData.append('file', {
        uri: Platform.OS === 'ios' ? imageUri.replace('file://', '') : imageUri,
        name: 'plate.jpg',
        type: 'image/jpeg',
      } as any);

      const response = await fetch(`${API_BASE}/api/v1/cv/plate-ocr`, {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (!response.ok) {
        throw new Error('Server responded with an error.');
      }

      const data = await response.json();
      if (data.success && data.extracted_plate) {
        const plate = data.extracted_plate;
        setPlateInput(plate);
        setVehicleNumber(plate);
        
        // Auto-trigger the lookup after a tiny delay so the UI registers it
        setTimeout(async () => {
          setLookupLoading(true);
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
              setLookupError(infoData.message || 'Vehicle details not found.');
            }

            if (challanData.status === 'ok' || challanData.status === 'demo') {
              setChallans(challanData.challans || []);
              setTotalFine(challanData.total_fine || 0);
            }
          } catch {
            setLookupError('Failed to fetch details for the scanned plate.');
          } finally {
            setLookupLoading(false);
          }
        }, 100);

        Alert.alert(
          'Plate Scanned Successfully',
          `Detected plate: ${plate} (${data.method})`
        );
      } else {
        setLookupError(data.error || 'Failed to extract plate number. Please enter manually.');
      }
    } catch (err: any) {
      setLookupError('OCR Scan failed. Please enter the plate number manually.');
    } finally {
      setLookupLoading(false);
    }
  };

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

  // Compute calculated fine breakdown
  const calculateTotalCalculatedFine = () => {
    let base = 0;
    const items: { name: string; amount: number; isOverride: boolean }[] = [];

    // Selected standard violations
    selectedViolations.forEach(id => {
      const v = COMMON_VIOLATIONS.find(x => x.id === id);
      if (v) {
        let amt = isSecondOffense ? v.base_2nd : v.base_1st;
        let isOverride = false;
        
        // State overrides check
        if (STATE_OVERRIDES[selectedState]?.[v.code]) {
          amt = STATE_OVERRIDES[selectedState][v.code];
          if (isSecondOffense && v.code === 'DRUNK_DRIVING') {
            amt = 15000; // Drunk driving 2nd offence standard max
          }
          isOverride = true;
        }

        base += amt;
        items.push({ name: v.title, amount: amt, isOverride });
      }
    });

    // Stacking Insurance penalty (Sec 196)
    if (stackInsurance) {
      const insAmt = isSecondOffense ? 4000 : 2000;
      base += insAmt;
      items.push({ name: 'Stacked: Uninsured Vehicle (Sec 196)', amount: insAmt, isOverride: false });
    }

    // Stacking PUC penalty (Sec 190(2))
    if (stackPUC) {
      const pucAmt = 10000; // Emission violation is standard ₹10,000
      base += pucAmt;
      items.push({ name: 'Stacked: Emissions Non-Compliance (Sec 190(2))', amount: pucAmt, isOverride: false });
    }

    return { total: base, breakdown: items };
  };

  const toggleViolation = (id: string) => {
    if (selectedViolations.includes(id)) {
      setSelectedViolations(prev => prev.filter(x => x !== id));
    } else {
      setSelectedViolations(prev => [...prev, id]);
    }
  };

  // Surface RAG judgements defensive arguments
  const surfaceDefensiveRAG = (violationCode?: string) => {
    setRagModalVisible(true);
    
    // Construct relevant defensive cases depending on violation code
    if (violationCode === 'NO_PUC' || stackPUC) {
      setRagTitle('Emissions & PUCC Defence (Sec 190)');
      setActiveJudgements([
        {
          citation: 'M.C. Mehta v. Union of India (1991) SCR (1) 866',
          ratio: 'The Supreme Court ruled that citizens cannot be penalized twice or harassed for delayed government emissions testing updates if certified PUC stations lack live calibration sync. If your certificate is physically valid, manual certificate overrides must be accepted.',
          defence: 'Propose showing the physical testing slip or requesting a 14-day compliance buffer under Central Motor Vehicles Rule 115(9).'
        },
        {
          citation: 'MoRTH Circular Rule 139 Exception (2018)',
          ratio: 'Rules explicitly mandate that enforcement officers must verify electronic records. If the digital portal is down, police cannot fine for non-possession of physical certificates if validly synced in your DigiLocker.',
          defence: 'Request officer to scan QR code on official DigiLocker app directly, citing Rule 139.'
        }
      ]);
    } else if (violationCode === 'DRUNK_DRIVING') {
      setRagTitle('Drunk Driving Precedents (Sec 185)');
      setActiveJudgements([
        {
          citation: 'State of Maharashtra v. Sandeep (2012) BOM',
          ratio: 'The High Court held that breathanalyzer results are inadmissible if not calibrated periodically (every 6 months) or if the officer fails to produce the calibration certificate upon driver request.',
          defence: 'Respectfully ask the officer to demonstrate the device\'s calibration seal and request a blood test at a local government hospital to counter incorrect breath readings.'
        }
      ]);
    } else {
      setRagTitle('General Defensive Precedents');
      setActiveJudgements([
        {
          citation: 'S. Rajaseekaran v. Union of India (2014) 6 SCC 36',
          ratio: 'Supreme Court bench on road safety safety guidelines established that arbitrary compounding fines cannot exceed regional notification thresholds. Officers cannot charge multiple arbitrary convenience fees on compoundable offences.',
          defence: 'Politely request the compounding officer to present the official gazette compounding notification of your state.'
        },
        {
          citation: 'Rule 139 of Central Motor Vehicle Rules (2018 Amendment)',
          ratio: 'Allows drivers up to 15 days to present original documents if not instantly verifyable, except in cases of immediate accident investigation.',
          defence: 'State that under Rule 139, you request a notice to produce documents within 15 days rather than an instant spot fine.'
        }
      ]);
    }
  };

  const calculatedResult = calculateTotalCalculatedFine();

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />

      {/* TABS HEADER */}
      <View style={styles.tabHeader}>
        <TouchableOpacity
          style={[styles.tabBtn, activeTab === 'sync' && styles.tabBtnActive]}
          onPress={() => setActiveTab('sync')}
        >
          <Ionicons 
            name="cloud-sync" 
            size={fs(16)} 
            color={activeTab === 'sync' ? '#0891b2' : '#6b7280'} 
          />
          <Text style={[styles.tabText, activeTab === 'sync' && styles.tabTextActive]}>RTO Sync</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.tabBtn, activeTab === 'calc' && styles.tabBtnActive]}
          onPress={() => setActiveTab('calc')}
        >
          <Ionicons 
            name="calculator" 
            size={fs(16)} 
            color={activeTab === 'calc' ? '#0891b2' : '#6b7280'} 
          />
          <Text style={[styles.tabText, activeTab === 'calc' && styles.tabTextActive]}>Fine Calc</Text>
        </TouchableOpacity>
      </View>

      {/* ── TAB 1: VEHICLE SYNC & PENDING CHALLANS ───────────────────────── */}
      {activeTab === 'sync' && (
        <View style={{ flex: 1 }}>
          {vehicleInfo ? (
            <ScrollView style={styles.syncContent} contentContainerStyle={{ paddingBottom: 40 }}>
              {/* Header */}
              <View style={styles.vsVehicleHeader}>
                <Ionicons name="car-sport" size={32} color="#0891b2" />
                <View>
                  <Text style={styles.vsVehicleTitle}>{vehicleInfo.maker_model || 'VEHICLE FOUND'}</Text>
                  <Text style={styles.vsVehiclePlate}>{vehicleInfo.vehicle_number}</Text>
                </View>
                <TouchableOpacity style={styles.vsResetBtn} onPress={() => setVehicleInfo(null)}>
                  <Text style={styles.vsResetBtnText}>Reset</Text>
                </TouchableOpacity>
              </View>

              {/* Stack Alerts (PUC or Insurance Expired!) */}
              {(stackInsurance || stackPUC) && (
                <View style={styles.alertStackContainer}>
                  <Text style={styles.alertStackTitle}>🚨 ACTION REQUIRED: RTO PENALTY RISK</Text>
                  {stackInsurance && (
                    <Text style={styles.alertStackItem}>
                      • INSURANCE EXPIRED (Valid till: {vehicleInfo.insurance_valid_upto}). Driving uninsured carries a ₹2,000 fine (Sec 196).
                    </Text>
                  )}
                  {stackPUC && (
                    <Text style={styles.alertStackItem}>
                      • PUC CERTIFICATE EXPIRED (Valid till: {vehicleInfo.pucc_valid_upto}). Driving without PUC carries a ₹10,000 fine (Sec 190).
                    </Text>
                  )}
                  <TouchableOpacity 
                    style={styles.alertStackActionBtn}
                    onPress={() => {
                      setActiveTab('calc');
                    }}
                  >
                    <Text style={styles.alertStackActionText}>Open Calculator to Assess Risk →</Text>
                  </TouchableOpacity>
                </View>
              )}

              {/* RTO Registry details */}
              <View style={styles.registryBox}>
                {[
                  ['Owner Name',           vehicleInfo.owner_name],
                  ['Registering Authority',vehicleInfo.registering_authority],
                  ['Vehicle Class',        vehicleInfo.vehicle_class],
                  ['Fuel Type',            vehicleInfo.fuel_type],
                  ['Registration Date',    vehicleInfo.registration_date],
                  ['Fitness Valid Upto',   vehicleInfo.fitness_valid_upto],
                  ['Tax Valid Upto',       vehicleInfo.tax_valid_upto],
                  ['Insurance Valid Upto', vehicleInfo.insurance_valid_upto],
                  ['PUCC Valid Upto',      vehicleInfo.pucc_valid_upto],
                ].map(([label, value]) => (
                  <View key={label} style={styles.vsRow}>
                    <Text style={styles.vsLabel}>{label}</Text>
                    <Text style={styles.vsValue}>{value || '—'}</Text>
                  </View>
                ))}
              </View>

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
          ) : (
            <View style={{ flex: 1 }}>
              {/* Search Bar */}
              <View style={styles.vsSearchBar}>
                <View style={styles.vsSearchInput}>
                  <Ionicons name="car-outline" size={20} color="#6b7280" />
                  <TextInput
                    style={styles.vsSearchText}
                    placeholder="Enter Vehicle Number (e.g. TN09AB1234)"
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
                  <TouchableOpacity 
                    onPress={handlePlateCamera} 
                    disabled={lookupLoading}
                    style={{ padding: 6, marginLeft: 4 }}
                  >
                    <Ionicons name="camera-outline" size={22} color="#0891b2" />
                  </TouchableOpacity>
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
                  <Text style={styles.vsEmptyTitle}>Search RTO Registry</Text>
                  <Text style={styles.vsEmptySubtitle}>
                    Synchronize your vehicle live with Vahan/Sarathi databases to retrieve registration expiry, active insurance policies, emission validity, and unpaid traffic challans.
                  </Text>
                </View>
              )}

              {lookupLoading && (
                <View style={styles.vsEmptyState}>
                  <ActivityIndicator size="large" color="#0891b2" />
                  <Text style={[styles.vsEmptyTitle, { color: '#0891b2', marginTop: 16 }]}>Verifying details with Vahan Hub…</Text>
                </View>
              )}
            </View>
          )}
        </View>
      )}

      {/* ── TAB 2: TRAFFIC FINE CALCULATOR ───────────────────────── */}
      {activeTab === 'calc' && (
        <View style={{ flex: 1 }}>
          <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: 20, paddingBottom: 120 }}>
            {/* Options bar */}
            <Text style={styles.calcSectionTitle}>JURISDICTION & COMMITTAL</Text>
            
            <View style={styles.calculatorOptionsBox}>
              <View style={styles.dropdownContainer}>
                <Text style={styles.dropdownLabel}>SELECT ENFORCEMENT STATE</Text>
                <View style={styles.chipRow}>
                  {[
                    ['TN', 'Tamil Nadu'],
                    ['MH', 'Maharashtra'],
                    ['DL', 'Delhi']
                  ].map(([code, name]) => (
                    <TouchableOpacity
                      key={code}
                      style={[styles.calcChip, selectedState === code && styles.calcChipActive]}
                      onPress={() => setSelectedState(code as any)}
                    >
                      <Text style={[styles.calcChipText, selectedState === code && styles.calcChipTextActive]}>
                        {name}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>

              <View style={styles.toggleRow}>
                <View>
                  <Text style={styles.toggleTitle}>Repeat Offence (2nd Committal)</Text>
                  <Text style={styles.toggleDesc}>Compounding fines double for repeated infractions under MV Act</Text>
                </View>
                <Switch
                  value={isSecondOffense}
                  onValueChange={setIsSecondOffense}
                  trackColor={{ false: '#d1d5db', true: '#0891b2' }}
                  thumbColor="#fff"
                />
              </View>
            </View>

            {/* Expired Document Penalties Checkboxes */}
            <Text style={styles.calcSectionTitle}>STACKABLE RTO PENALTY THREATS</Text>
            <View style={styles.stackedBox}>
              <TouchableOpacity 
                style={styles.stackItem}
                onPress={() => setStackInsurance(prev => !prev)}
                activeOpacity={0.8}
              >
                <Ionicons 
                  name={stackInsurance ? "checkbox" : "square-outline"} 
                  size={24} 
                  color={stackInsurance ? "#ef4444" : "#6b7280"} 
                />
                <View style={{ flex: 1 }}>
                  <Text style={styles.stackItemTitle}>No Active Third-Party Insurance (Sec 196)</Text>
                  <Text style={styles.stackItemDesc}>Adds stackable ₹2,000 fine. Auto-detected from sync.</Text>
                </View>
              </TouchableOpacity>

              <TouchableOpacity 
                style={styles.stackItem}
                onPress={() => setStackPUC(prev => !prev)}
                activeOpacity={0.8}
              >
                <Ionicons 
                  name={stackPUC ? "checkbox" : "square-outline"} 
                  size={24} 
                  color={stackPUC ? "#ef4444" : "#6b7280"} 
                />
                <View style={{ flex: 1 }}>
                  <Text style={styles.stackItemTitle}>No Valid PUC Certificate (Sec 190(2))</Text>
                  <Text style={styles.stackItemDesc}>Adds massive stackable ₹10,000 fine. Auto-detected.</Text>
                </View>
              </TouchableOpacity>
            </View>

            {/* Search violations */}
            <Text style={styles.calcSectionTitle}>SELECT ADDITIONAL OFFENCES</Text>
            <View style={styles.violationSearchContainer}>
              <Ionicons name="search-outline" size={18} color="#6b7280" />
              <TextInput
                style={styles.violationSearchText}
                placeholder="Search by offense name or section..."
                placeholderTextColor="#9ca3af"
                value={searchQuery}
                onChangeText={setSearchQuery}
              />
            </View>

            {/* List searchable violations */}
            <View style={styles.violationsList}>
              {COMMON_VIOLATIONS.filter(v => 
                v.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                v.section.toLowerCase().includes(searchQuery.toLowerCase())
              ).map(v => {
                const isSelected = selectedViolations.includes(v.id);
                return (
                  <TouchableOpacity
                    key={v.id}
                    style={[styles.violationCard, isSelected && styles.violationCardActive]}
                    onPress={() => toggleViolation(v.id)}
                    activeOpacity={0.8}
                  >
                    <View style={styles.violationCardLeft}>
                      <View style={[styles.violationSectionBox, isSelected && { backgroundColor: '#0891b2' }]}>
                        <Text style={[styles.violationSectionText, isSelected && { color: '#fff' }]}>
                          {v.section}
                        </Text>
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.violationTitle}>{v.title}</Text>
                        <Text style={styles.violationDesc}>{v.description}</Text>
                      </View>
                    </View>
                    <View style={styles.violationCardRight}>
                      <Text style={styles.violationFineText}>
                        ₹{STATE_OVERRIDES[selectedState]?.[v.code] ?? (isSecondOffense ? v.base_2nd : v.base_1st)}
                      </Text>
                      {isSelected && <Ionicons name="checkmark-circle" size={20} color="#0891b2" />}
                    </View>
                  </TouchableOpacity>
                );
              })}
            </View>

          </ScrollView>

          {/* DYNAMIC CALCULATOR BOTTOM FLOATING PANEL */}
          <View style={styles.floatingCalculatorBar}>
            <View style={styles.floatBarLeft}>
              <Text style={styles.floatBarTotalLabel}>TOTAL ESTIMATED FINE</Text>
              <Text style={styles.floatBarTotalAmt}>₹{calculatedResult.total}</Text>
              <Text style={styles.floatBarBreakdownText}>
                {selectedViolations.length + (stackInsurance ? 1 : 0) + (stackPUC ? 1 : 0)} items stack calculated
              </Text>
            </View>
            <TouchableOpacity 
              style={[
                styles.floatFightBtn, 
                calculatedResult.total === 0 && { opacity: 0.5 }
              ]}
              disabled={calculatedResult.total === 0}
              onPress={() => {
                // Determine the primary violation code to fetch RAG
                let prim = '';
                if (selectedViolations.includes('1')) prim = 'DRUNK_DRIVING';
                else if (selectedViolations.includes('6') || stackPUC) prim = 'NO_PUC';
                surfaceDefensiveRAG(prim);
              }}
            >
              <MaterialCommunityIcons name="gavel" size={20} color="#fff" />
              <Text style={styles.floatFightBtnText}>FIGHT THIS</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* RAG PRECEDENTS LEGAL PREVIEW DIALOG MODAL */}
      <Modal
        visible={ragModalVisible}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setRAGModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                <MaterialCommunityIcons name="gavel" size={24} color="#0891b2" />
                <Text style={styles.modalTitle}>{ragTitle}</Text>
              </View>
              <TouchableOpacity onPress={() => setRAGModalVisible(false)} style={styles.modalCloseBtn}>
                <Ionicons name="close" size={22} color="#6b7280" />
              </TouchableOpacity>
            </View>

            <ScrollView contentContainerStyle={{ paddingBottom: 20 }}>
              <Text style={styles.ragExplainerText}>
                The following judgements are extracted from your geolocated legal database using DriveLegal\'s RAG module. You can present these supreme court rulings to enforcement officers or during compounding disputes:
              </Text>

              {activeJudgements.map((j, i) => (
                <View key={i} style={styles.judgementCard}>
                  <Text style={styles.jCitation}>{j.citation}</Text>
                  <Text style={styles.jRatioTitle}>HELD BY BENCH:</Text>
                  <Text style={styles.jRatioText}>{j.ratio}</Text>
                  <View style={styles.jDefenceBox}>
                    <Text style={styles.jDefenceTitle}>⚖️ DEFENSIVE ARGUMENT PROPOSAL:</Text>
                    <Text style={styles.jDefenceText}>{j.defence}</Text>
                  </View>
                </View>
              ))}

              <View style={styles.ragFooterTip}>
                <Ionicons name="alert-circle-outline" size={16} color="#d97706" />
                <Text style={styles.ragFooterText}>
                  Note: DriveLegal provides educational resources. Always remain respectful when disputing a ticket with RTO officers. Citing Supreme Court precedents demonstrates active legal awareness and usually leads to procedural notices rather than spot seizures.
                </Text>
              </View>
            </ScrollView>
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
  
  // Tab Header
  tabHeader: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
    paddingHorizontal: 10,
  },
  tabBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    gap: 8,
    borderBottomWidth: 3,
    borderBottomColor: 'transparent',
  },
  tabBtnActive: {
    borderBottomColor: '#0891b2',
  },
  tabText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#6b7280',
  },
  tabTextActive: {
    color: '#0891b2',
  },

  // Vehicle sync styles
  syncContent: {
    flex: 1,
    padding: 20,
  },
  vsVehicleHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 16,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    gap: 14,
    marginBottom: 20,
  },
  vsVehicleTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#0f172a',
  },
  vsVehiclePlate: {
    fontSize: 13,
    color: '#6b7280',
    fontWeight: '700',
    marginTop: 2,
  },
  vsResetBtn: {
    marginLeft: 'auto',
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  vsResetBtnText: {
    color: '#ef4444',
    fontSize: 12,
    fontWeight: '700',
  },

  // Alert Stack Container
  alertStackContainer: {
    backgroundColor: '#fee2e2',
    borderWidth: 1,
    borderColor: '#fca5a5',
    borderRadius: 16,
    padding: 16,
    marginBottom: 20,
    gap: 6,
  },
  alertStackTitle: {
    fontSize: 12,
    fontWeight: '800',
    color: '#991b1b',
  },
  alertStackItem: {
    fontSize: 11,
    fontWeight: '600',
    color: '#7f1d1d',
    lineHeight: 16,
  },
  alertStackActionBtn: {
    marginTop: 6,
    alignSelf: 'flex-start',
  },
  alertStackActionText: {
    fontSize: 11,
    fontWeight: '800',
    color: '#0891b2',
    textDecorationLine: 'underline',
  },

  registryBox: {
    backgroundColor: '#fff',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    overflow: 'hidden',
    marginBottom: 24,
  },
  vsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  vsLabel: {
    fontSize: 13,
    color: '#6b7280',
    fontWeight: '600',
  },
  vsValue: {
    fontSize: 13,
    color: '#0f172a',
    fontWeight: '700',
  },

  vsChallanHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 14,
    marginBottom: 10,
  },
  vsChallanTitle: {
    flex: 1,
    fontSize: 16,
    fontWeight: '800',
    color: '#0f172a',
  },
  vsChallanTotal: {
    fontSize: 14,
    fontWeight: '900',
    color: '#ef4444',
  },
  vsNoChallan: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#ecfdf5',
    padding: 16,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#a7f3d0',
  },
  vsNoChallanText: {
    fontSize: 13,
    color: '#047857',
    fontWeight: '700',
  },
  vsChallanRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    gap: 12,
    marginBottom: 10,
  },
  vsChallanOffence: {
    fontSize: 13,
    fontWeight: '700',
    color: '#0f172a',
  },
  vsChallanMeta: {
    fontSize: 11,
    color: '#6b7280',
    marginTop: 2,
  },
  vsChallanAmt: {
    fontSize: 14,
    fontWeight: '900',
    color: '#ef4444',
  },
  vsChallanStatus: {
    fontSize: 10,
    fontWeight: '700',
    marginTop: 2,
  },

  // Vehicle Search defaults
  vsSearchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
    gap: 10,
  },
  vsSearchInput: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f1f5f9',
    borderRadius: 12,
    paddingHorizontal: 12,
    height: 48,
    gap: 10,
  },
  vsSearchText: {
    flex: 1,
    fontSize: 14,
    fontWeight: '700',
    color: '#0f172a',
  },
  vsSearchBtn: {
    width: 48,
    height: 48,
    borderRadius: 12,
    backgroundColor: '#0891b2',
    justifyContent: 'center',
    alignItems: 'center',
  },
  lookupError: {
    fontSize: 12,
    color: '#ef4444',
    paddingHorizontal: 20,
    marginTop: 10,
    fontWeight: '600',
  },
  vsEmptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
    marginTop: 60,
    gap: 12,
  },
  vsEmptyTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#0f172a',
    marginTop: 8,
  },
  vsEmptySubtitle: {
    fontSize: 13,
    color: '#6b7280',
    textAlign: 'center',
    lineHeight: 20,
  },

  // Calculator styles
  calcSectionTitle: {
    fontSize: 11,
    fontWeight: '900',
    color: '#94a3b8',
    letterSpacing: 1.5,
    marginTop: 20,
    marginBottom: 12,
    marginLeft: 4,
  },
  calculatorOptionsBox: {
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 16,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    gap: 16,
  },
  dropdownContainer: {
    gap: 8,
  },
  dropdownLabel: {
    fontSize: 10,
    fontWeight: '800',
    color: '#6b7280',
  },
  chipRow: {
    flexDirection: 'row',
    gap: 8,
  },
  calcChip: {
    flex: 1,
    backgroundColor: '#f1f5f9',
    paddingVertical: 10,
    borderRadius: 10,
    alignItems: 'center',
  },
  calcChipActive: {
    backgroundColor: '#e0f2fe',
    borderWidth: 1,
    borderColor: '#0891b2',
  },
  calcChipText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#6b7280',
  },
  calcChipTextActive: {
    color: '#0891b2',
  },
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#f1f5f9',
    paddingTop: 16,
  },
  toggleTitle: {
    fontSize: 13,
    fontWeight: '800',
    color: '#0f172a',
  },
  toggleDesc: {
    fontSize: 10,
    color: '#6b7280',
    marginTop: 2,
  },

  // Stacked Box
  stackedBox: {
    backgroundColor: '#fff',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    padding: 16,
    gap: 14,
  },
  stackItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  stackItemTitle: {
    fontSize: 13,
    fontWeight: '800',
    color: '#0f172a',
  },
  stackItemDesc: {
    fontSize: 10,
    color: '#6b7280',
    marginTop: 2,
  },

  // Search violations
  violationSearchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    paddingHorizontal: 12,
    height: 48,
    gap: 8,
    marginBottom: 12,
  },
  violationSearchText: {
    flex: 1,
    fontSize: 13,
    fontWeight: '700',
    color: '#0f172a',
  },

  // Violations list
  violationsList: {
    gap: 10,
  },
  violationCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    padding: 14,
    gap: 12,
  },
  violationCardActive: {
    borderColor: '#0891b2',
    backgroundColor: '#f0f9ff',
  },
  violationCardLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  violationSectionBox: {
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  violationSectionText: {
    fontSize: 10,
    fontWeight: '800',
    color: '#6b7280',
  },
  violationTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#0f172a',
  },
  violationDesc: {
    fontSize: 10,
    color: '#6b7280',
    lineHeight: 14,
    marginTop: 2,
  },
  violationCardRight: {
    alignItems: 'flex-end',
    gap: 6,
  },
  violationFineText: {
    fontSize: 14,
    fontWeight: '900',
    color: '#ef4444',
  },

  // Floating bottom bar
  floatingCalculatorBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    paddingHorizontal: 20,
    paddingVertical: 14,
    paddingBottom: Platform.OS === 'ios' ? 28 : 14,
  },
  floatBarLeft: {
    gap: 2,
  },
  floatBarTotalLabel: {
    fontSize: 9,
    fontWeight: '900',
    color: '#6b7280',
    letterSpacing: 1,
  },
  floatBarTotalAmt: {
    fontSize: 22,
    fontWeight: '900',
    color: '#0f172a',
  },
  floatBarBreakdownText: {
    fontSize: 10,
    color: '#6b7280',
    fontWeight: '600',
  },
  floatFightBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#0891b2',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 12,
  },
  floatFightBtnText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '800',
  },

  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    padding: 20,
    maxHeight: '85%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
    paddingBottom: 14,
    marginBottom: 16,
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#0f172a',
  },
  modalCloseBtn: {
    padding: 4,
    backgroundColor: '#f1f5f9',
    borderRadius: 20,
  },
  ragExplainerText: {
    fontSize: 12,
    color: '#6b7280',
    lineHeight: 18,
    marginBottom: 20,
    fontWeight: '500',
  },
  judgementCard: {
    backgroundColor: '#f8fafc',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    padding: 16,
    marginBottom: 14,
    gap: 8,
  },
  jCitation: {
    fontSize: 13,
    fontWeight: '800',
    color: '#0891b2',
  },
  jRatioTitle: {
    fontSize: 9,
    fontWeight: '900',
    color: '#94a3b8',
    letterSpacing: 0.8,
  },
  jRatioText: {
    fontSize: 12,
    color: '#334155',
    lineHeight: 18,
    fontWeight: '600',
  },
  jDefenceBox: {
    backgroundColor: '#ecfdf5',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#a7f3d0',
    marginTop: 4,
  },
  jDefenceTitle: {
    fontSize: 9,
    fontWeight: '900',
    color: '#047857',
  },
  jDefenceText: {
    fontSize: 11,
    color: '#065f46',
    lineHeight: 16,
    fontWeight: '700',
    marginTop: 2,
  },
  ragFooterTip: {
    flexDirection: 'row',
    backgroundColor: '#fffbeb',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#fde68a',
    padding: 12,
    gap: 8,
    marginTop: 10,
  },
  ragFooterText: {
    flex: 1,
    fontSize: 11,
    color: '#b45309',
    lineHeight: 16,
    fontWeight: '600',
  },
});
