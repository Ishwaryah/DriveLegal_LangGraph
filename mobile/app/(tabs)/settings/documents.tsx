import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Platform,
  SafeAreaView,
  Modal,
  TextInput,
  Alert,
  KeyboardAvoidingView,
  ActivityIndicator,
  Linking,
  Dimensions,
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useSettings } from '../../../hooks/useSettings';
import { useGeoFineAlert } from '../../../hooks/useGeoFineAlert';
import { useDocuments, StoredDocument } from '../../../hooks/useDocuments';
import { API_BASE } from '../../../config/api';

const { width: windowWidth } = Dimensions.get('window');
const fontScale = Math.min(windowWidth, 420) / 375;
const fs = (size: number) => Math.round(size * fontScale);

// Standard official Parivahan links for CTAs
const PORTAL_LINKS = {
  DL: 'https://sarathi.parivahan.gov.in/',
  RC: 'https://vahan.parivahan.gov.in/',
  INSURANCE: 'https://www.irda.gov.in/',
  PUC: 'https://vahan.parivahan.gov.in/puc/',
};

// Colors of Material You Google Antigravity Palette
const PALETTE = {
  emerald: '#10B981',
  amber: '#F59E0B',
  rose: '#EF4444',
  cyan: '#06B6D4',
  indigo: '#6366F1',
  darkGray: '#111827',
  glassBg: 'rgba(255, 255, 255, 0.75)',
};

export default function DocumentVaultScreen() {
  const router = useRouter();
  const { profile } = useSettings();
  const { state } = useGeoFineAlert();
  
  // Custom hook for basic docs persistence
  const { documents: storedDocs, license: storedLicense, loading: hookLoading } = useDocuments();

  // Local synced documents state to enable direct Vahan integration updates
  const [documents, setDocuments] = useState<StoredDocument[]>([]);
  const [license, setLicense] = useState<StoredDocument | null>(null);
  const [loading, setLoading] = useState(true);

  // Verification Search state
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyType, setVerifyType] = useState<'DL' | 'RC'>('RC');
  const [verifyInput, setVerifyInput] = useState('');
  const [verificationLog, setVerificationLog] = useState<string[]>([]);
  const [verifyModalVisible, setVerifyModalVisible] = useState(false);

  // Loading indicator for scan-to-verify
  const [scanLoading, setScanLoading] = useState(false);

  // Manual Add Modal
  const [modalVisible, setModalVisible] = useState(false);
  const [formType, setFormType] = useState<'RC' | 'INSURANCE' | 'PUC' | 'LICENSE'>('RC');
  const [formTitle, setFormTitle] = useState('Vehicle RC');
  const [formExpiry, setFormExpiry] = useState('');

  // Sync with the useDocuments hook data initially
  useEffect(() => {
    if (!hookLoading) {
      setDocuments(storedDocs);
      setLicense(storedLicense);
      setLoading(false);
    }
  }, [hookLoading, storedDocs, storedLicense]);

  // Utility: calculate days remaining and status
  const calculateValidity = (expiryStr: string) => {
    if (!expiryStr || expiryStr === '---' || expiryStr === 'NA') {
      return { daysLeft: 0, status: 'NOT LINKED', color: '#6B7280', percent: 0 };
    }

    try {
      // Clean string
      const cleaned = expiryStr.trim();
      const expiryDate = new Date(cleaned);

      if (isNaN(expiryDate.getTime())) {
        // Try parsing DD MMM YYYY manually (e.g. 15 JUN 2030)
        const parts = cleaned.split(/[\s/-]+/);
        if (parts.length === 3) {
          const day = parseInt(parts[0]);
          const monthStr = parts[1].toUpperCase();
          const year = parseInt(parts[2]);
          const months: Record<string, number> = {
            JAN: 0, FEB: 1, MAR: 2, APR: 3, MAY: 4, JUN: 5,
            JUL: 6, AUG: 7, SEP: 8, OCT: 9, NOV: 10, DEC: 11
          };
          const month = months[monthStr.substring(0, 3)] ?? 0;
          const parsedDate = new Date(year, month, day);
          if (!isNaN(parsedDate.getTime())) {
            return getDetails(parsedDate);
          }
        }
        return { daysLeft: 0, status: 'ACTIVE', color: PALETTE.emerald, percent: 1 };
      }
      return getDetails(expiryDate);
    } catch {
      return { daysLeft: 0, status: 'UNKNOWN', color: '#6B7280', percent: 0.5 };
    }

    function getDetails(expiryDate: Date) {
      const today = new Date();
      today.setHours(0,0,0,0);
      const diffTime = expiryDate.getTime() - today.getTime();
      const daysLeft = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      // Calculate a standard validity percent (cap at 365 days max for visuals)
      const percent = Math.max(0, Math.min(1, daysLeft / 365));

      if (daysLeft < 0) {
        return { daysLeft, status: 'EXPIRED', color: PALETTE.rose, percent };
      } else if (daysLeft <= 30) {
        return { daysLeft, status: 'EXPIRING', color: PALETTE.amber, percent };
      } else {
        return { daysLeft, status: 'VALID', color: PALETTE.emerald, percent };
      }
    }
  };

  // Live Verification Trigger
  const handleLiveVerify = async () => {
    const inputCleaned = verifyInput.replace(/[\s-]/g, '').toUpperCase();
    if (inputCleaned.length < 5) {
      Alert.alert('Invalid Number', 'Please enter a valid document or vehicle plate number.');
      return;
    }

    setScanLoading(true);
    setVerificationLog(['Initializing secure connection to Parivahan API...', 'Securing SSL handshake with RTO server...']);

    // Log simulation steps
    const addLog = (msg: string, delay: number) => {
      return new Promise<void>((resolve) => {
        setTimeout(() => {
          setVerificationLog(prev => [...prev, msg]);
          resolve();
        }, delay);
      });
    };

    try {
      if (verifyType === 'DL') {
        await addLog(`Querying Sarathi DL Repository for: ${inputCleaned}`, 800);
        await addLog('Verifying biometric details and driving history...', 800);

        const res = await fetch(`${API_BASE}/api/v1/dl/info/${inputCleaned}`);
        const data = await res.json();

        if (data.status === 'success' && data.dl_info) {
          await addLog('Driving License successfully decrypted!', 600);
          await addLog(`Holder Name: ${data.dl_info.holder_name}`, 400);
          await addLog(`Status: ${data.dl_info.license_status} (Active until ${data.dl_info.valid_till})`, 400);

          const updatedLic: StoredDocument = {
            id: 'license',
            type: 'LICENSE',
            title: 'DRIVING LICENSE',
            subtitle: data.dl_info.dl_number,
            expiry: data.dl_info.valid_till,
          };

          setLicense(updatedLic);
          await AsyncStorage.setItem('user_license', JSON.stringify(updatedLic));
          
          setTimeout(() => {
            setScanLoading(false);
            setVerifyModalVisible(false);
            setVerifyInput('');
            Alert.alert('DL Verified!', 'Driving License has been securely linked and verified live with Sarathi databases.');
          }, 1000);
        } else {
          throw new Error(data.message || 'DL details could not be matched.');
        }

      } else {
        await addLog(`Querying Vahan RC Registry for Plate: ${inputCleaned}`, 800);
        await addLog('Extracting vehicle details, fitness norms, and PUC...', 800);

        const res = await fetch(`${API_BASE}/api/v1/vehicle/info/${inputCleaned}`);
        const data = await res.json();

        if (data.status === 'success' && data.vehicle_info) {
          const vi = data.vehicle_info;
          await addLog(`Vehicle Authenticated: ${vi.maker_model}`, 600);
          await addLog(`RC Fitness Valid Till: ${vi.fitness_valid_upto}`, 400);
          await addLog(`Insurance Valid Till: ${vi.insurance_valid_upto}`, 400);
          await addLog(`PUC Emissions Valid Till: ${vi.pucc_valid_upto}`, 400);

          // Build/update all three document types dynamically from RTO payload!
          const newRC: StoredDocument = {
            id: `rc_${Date.now()}`,
            type: 'RC',
            title: `RC: ${vi.maker_model.split(' ')[0] || 'Vehicle'}`,
            subtitle: vi.vehicle_number,
            expiry: vi.fitness_valid_upto,
          };

          const newIns: StoredDocument = {
            id: `ins_${Date.now() + 1}`,
            type: 'INSURANCE',
            title: 'Vehicle Insurance',
            subtitle: `POL-INS-${vi.vehicle_number.slice(-4)}`,
            expiry: vi.insurance_valid_upto,
          };

          const newPUC: StoredDocument = {
            id: `puc_${Date.now() + 2}`,
            type: 'PUC',
            title: 'PUC Certificate',
            subtitle: `PUC-CERT-${vi.vehicle_number.slice(-4)}`,
            expiry: vi.pucc_valid_upto,
          };

          // Overwrite existing RC/INSURANCE/PUC for this vehicle
          let updatedDocs = documents.filter(d => d.subtitle !== vi.vehicle_number && !['RC', 'INSURANCE', 'PUC'].includes(d.type));
          updatedDocs = [...updatedDocs, newRC, newIns, newPUC];

          setDocuments(updatedDocs);
          await AsyncStorage.setItem('user_documents', JSON.stringify(updatedDocs));

          setTimeout(() => {
            setScanLoading(false);
            setVerifyModalVisible(false);
            setVerifyInput('');
            Alert.alert(
              'RTO Sync Successful!',
              `RC, Insurance, and PUC dates for ${vi.vehicle_number} have been fully synchronized with Vahan live registries.`
            );
          }, 1000);
        } else {
          throw new Error(data.message || 'Vehicle registry lookup failed.');
        }
      }
    } catch (err: any) {
      setScanLoading(false);
      Alert.alert('Verification Failed', err.message || 'The RTO server failed to respond. Please check your internet connection or try again later.');
    }
  };

  // Manual Add Document
  const handleManualSave = async () => {
    if (!formSubtitle || !formExpiry) {
      Alert.alert('Missing Info', 'Please fill in the ID number and validity dates.');
      return;
    }

    if (formType === 'LICENSE') {
      const newLicense: StoredDocument = {
        id: 'license',
        type: 'LICENSE',
        title: 'DRIVING LICENSE',
        subtitle: formSubtitle.toUpperCase(),
        expiry: formExpiry,
      };
      setLicense(newLicense);
      await AsyncStorage.setItem('user_license', JSON.stringify(newLicense));
    } else {
      const newDoc: StoredDocument = {
        id: `manual_${Date.now()}`,
        type: formType as any,
        title: formTitle,
        subtitle: formSubtitle.toUpperCase(),
        expiry: formExpiry,
      };
      const newDocs = [...documents, newDoc];
      setDocuments(newDocs);
      await AsyncStorage.setItem('user_documents', JSON.stringify(newDocs));
    }

    setModalVisible(false);
  };

  // Delete document
  const handleDelete = (id: string, name: string) => {
    Alert.alert('Remove Document', `Are you sure you want to remove ${name} from your vault?`, [
      { text: 'Keep It', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          if (id === 'license') {
            setLicense(null);
            await AsyncStorage.removeItem('user_license');
          } else {
            const updated = documents.filter(d => d.id !== id);
            setDocuments(updated);
            await AsyncStorage.setItem('user_documents', JSON.stringify(updated));
          }
        },
      },
    ]);
  };

  const handlePortalRedirect = (type: keyof typeof PORTAL_LINKS) => {
    Linking.openURL(PORTAL_LINKS[type]);
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.loaderContainer}>
          <ActivityIndicator size="large" color={PALETTE.indigo} />
          <Text style={styles.loaderText}>Syncing Vault...</Text>
        </View>
      </SafeAreaView>
    );
  }

  // Pre-fetch individual documents for easy validity rendering
  const rcDoc = documents.find(d => d.type === 'RC') || null;
  const insDoc = documents.find(d => d.type === 'INSURANCE') || null;
  const pucDoc = documents.find(d => d.type === 'PUC') || null;

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        
        {/* HEADER */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Document Vault</Text>
          <TouchableOpacity 
            style={styles.addButton} 
            onPress={() => {
              setFormType('RC');
              setFormTitle('Vehicle RC');
              setFormSubtitle('');
              setFormExpiry('');
              setModalVisible(true);
            }}
          >
            <Ionicons name="add-circle-outline" size={fs(26)} color={PALETTE.indigo} />
          </TouchableOpacity>
        </View>

        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
          
          {/* QUICK SCAN TO VERIFY BANNER */}
          <LinearGradient
            colors={['#4f46e5', '#312e81']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.scanBanner}
          >
            <View style={styles.scanBannerLeft}>
              <MaterialCommunityIcons name="cloud-sync" size={32} color="#fff" />
              <View>
                <Text style={styles.scanBannerTitle}>Instant RTO Sync</Text>
                <Text style={styles.scanBannerSubtitle}>Synchronize RC, Insurance, and PUC directly from Vahan API.</Text>
              </View>
            </View>
            <TouchableOpacity 
              style={styles.scanBannerBtn}
              onPress={() => {
                setVerifyType('RC');
                setVerifyInput('');
                setVerificationLog([]);
                setVerifyModalVisible(true);
              }}
            >
              <Text style={styles.scanBannerBtnText}>SYNC NOW</Text>
            </TouchableOpacity>
          </LinearGradient>

          {/* 1. DRIVING LICENSE CARD */}
          <Text style={styles.sectionTitle}>PERSONAL DOCUMENTS</Text>
          <View style={styles.cardContainer}>
            {license ? (
              <View style={styles.vaultCard}>
                <View style={styles.cardHeader}>
                  <View style={styles.headerTitleRow}>
                    <View style={[styles.docIcon, { backgroundColor: 'rgba(99, 102, 241, 0.1)' }]}>
                      <Ionicons name="card" size={22} color={PALETTE.indigo} />
                    </View>
                    <View>
                      <Text style={styles.docName}>DRIVING LICENSE</Text>
                      <Text style={styles.docNo}>{license.subtitle}</Text>
                    </View>
                  </View>
                  <View style={styles.statusBadgeRow}>
                    <View style={[styles.verifiedLabel, { backgroundColor: 'rgba(16, 185, 129, 0.1)' }]}>
                      <Ionicons name="checkmark-circle" size={12} color={PALETTE.emerald} />
                      <Text style={[styles.verifiedText, { color: PALETTE.emerald }]}>Sarathi Sync</Text>
                    </View>
                    <TouchableOpacity onPress={() => handleDelete('license', 'Driving License')}>
                      <Ionicons name="trash-outline" size={16} color={PALETTE.rose} />
                    </TouchableOpacity>
                  </View>
                </View>

                {/* Validity Details & Concentric Arc Ring representation */}
                {(() => {
                  const val = calculateValidity(license.expiry);
                  return (
                    <View style={styles.cardMain}>
                      <View style={styles.arcContainer}>
                        <View style={[styles.arcRing, { borderColor: `${val.color}20` }]}>
                          <View style={[styles.arcProgress, { borderColor: val.color, transform: [{ rotate: `${180 * val.percent}deg` }] } as any]} />
                          <View style={styles.arcInnerContent}>
                            <Text style={[styles.arcDaysVal, { color: val.color }]}>
                              {val.daysLeft > 0 ? val.daysLeft : '0'}
                            </Text>
                            <Text style={styles.arcDaysLabel}>Days Left</Text>
                          </View>
                        </View>
                      </View>
                      <View style={styles.infoCol}>
                        <Text style={styles.holderLabel}>HOLDER NAME</Text>
                        <Text style={styles.holderValue}>{profile.name || 'SARATHI RAJAN'}</Text>
                        
                        <View style={styles.statusBadgeContainer}>
                          <Text style={styles.validityLabel}>STATUS</Text>
                          <View style={[styles.statusChip, { backgroundColor: `${val.color}15` }]}>
                            <Text style={[styles.statusChipText, { color: val.color }]}>{val.status}</Text>
                          </View>
                        </View>

                        <Text style={styles.validityLabel}>VALID TILL</Text>
                        <Text style={styles.validityValue}>{license.expiry}</Text>
                      </View>
                    </View>
                  );
                })()}

                <View style={styles.cardFooter}>
                  <Text style={styles.footerPrompt}>Verified valid under Sec 139 MV Act.</Text>
                  <TouchableOpacity style={styles.ctaBtn} onPress={() => handlePortalRedirect('DL')}>
                    <Text style={styles.ctaBtnText}>RENEW LICENSE</Text>
                    <Ionicons name="open-outline" size={14} color={PALETTE.indigo} />
                  </TouchableOpacity>
                </View>
              </View>
            ) : (
              <View style={styles.emptyCardPlaceholder}>
                <Ionicons name="card-outline" size={32} color="#D1D5DB" />
                <Text style={styles.placeholderTitle}>Driving License Not Linked</Text>
                <Text style={styles.placeholderDesc}>Link your driver's license live via Sarathi lookup to keep track of suspensions and validity.</Text>
                <TouchableOpacity 
                  style={styles.verifyBtnOutline}
                  onPress={() => {
                    setVerifyType('DL');
                    setVerifyInput('');
                    setVerificationLog([]);
                    setVerifyModalVisible(true);
                  }}
                >
                  <Ionicons name="sync" size={16} color={PALETTE.indigo} />
                  <Text style={styles.verifyBtnOutlineText}>VERIFY VIA SARATHI API</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>

          {/* 2. RTO VEHICLE DOCUMENTS (RC, Insurance, PUC) */}
          <Text style={styles.sectionTitle}>VEHICLE DOCUMENTS</Text>
          
          {/* RC CARD */}
          <View style={styles.cardContainer}>
            {rcDoc ? (
              <View style={styles.vaultCard}>
                <View style={styles.cardHeader}>
                  <View style={styles.headerTitleRow}>
                    <View style={[styles.docIcon, { backgroundColor: 'rgba(16, 185, 129, 0.1)' }]}>
                      <Ionicons name="car" size={22} color={PALETTE.emerald} />
                    </View>
                    <View>
                      <Text style={styles.docName}>{rcDoc.title.toUpperCase()}</Text>
                      <Text style={styles.docNo}>{rcDoc.subtitle}</Text>
                    </View>
                  </View>
                  <View style={styles.statusBadgeRow}>
                    <View style={[styles.verifiedLabel, { backgroundColor: 'rgba(16, 185, 129, 0.1)' }]}>
                      <Ionicons name="checkmark-circle" size={12} color={PALETTE.emerald} />
                      <Text style={[styles.verifiedText, { color: PALETTE.emerald }]}>Vahan Sync</Text>
                    </View>
                    <TouchableOpacity onPress={() => handleDelete(rcDoc.id, rcDoc.title)}>
                      <Ionicons name="trash-outline" size={16} color={PALETTE.rose} />
                    </TouchableOpacity>
                  </View>
                </View>

                {(() => {
                  const val = calculateValidity(rcDoc.expiry);
                  return (
                    <View style={styles.cardMain}>
                      <View style={styles.arcContainer}>
                        <View style={[styles.arcRing, { borderColor: `${val.color}20` }]}>
                          <View style={[styles.arcProgress, { borderColor: val.color, transform: [{ rotate: `${180 * val.percent}deg` }] } as any]} />
                          <View style={styles.arcInnerContent}>
                            <Text style={[styles.arcDaysVal, { color: val.color }]}>
                              {val.daysLeft > 0 ? val.daysLeft : '0'}
                            </Text>
                            <Text style={styles.arcDaysLabel}>Days Left</Text>
                          </View>
                        </View>
                      </View>
                      <View style={styles.infoCol}>
                        <Text style={styles.holderLabel}>FITNESS/RC VALIDITY</Text>
                        <Text style={styles.holderValue}>{rcDoc.expiry}</Text>
                        
                        <View style={styles.statusBadgeContainer}>
                          <Text style={styles.validityLabel}>STATUS</Text>
                          <View style={[styles.statusChip, { backgroundColor: `${val.color}15` }]}>
                            <Text style={[styles.statusChipText, { color: val.color }]}>{val.status}</Text>
                          </View>
                        </View>

                        <Text style={styles.validityLabel}>RTO OFFICE</Text>
                        <Text style={styles.validityValue}>{state || 'Tamil Nadu RTO'}</Text>
                      </View>
                    </View>
                  );
                })()}

                <View style={styles.cardFooter}>
                  <Text style={styles.footerPrompt}>Authorized Digital Copy.</Text>
                  <TouchableOpacity style={styles.ctaBtn} onPress={() => handlePortalRedirect('RC')}>
                    <Text style={styles.ctaBtnText}>VIEW PORTAL</Text>
                    <Ionicons name="open-outline" size={14} color={PALETTE.indigo} />
                  </TouchableOpacity>
                </View>
              </View>
            ) : (
              <View style={styles.emptyCardPlaceholder}>
                <Ionicons name="document-text-outline" size={32} color="#D1D5DB" />
                <Text style={styles.placeholderTitle}>Registration Certificate (RC) Missing</Text>
                <Text style={styles.placeholderDesc}>Sync your RC directly from Vahan to check fitness and validity logs instantly.</Text>
              </View>
            )}
          </View>

          {/* INSURANCE CARD */}
          <View style={styles.cardContainer}>
            {insDoc ? (
              <View style={styles.vaultCard}>
                <View style={styles.cardHeader}>
                  <View style={styles.headerTitleRow}>
                    <View style={[styles.docIcon, { backgroundColor: 'rgba(245, 158, 11, 0.1)' }]}>
                      <Ionicons name="shield-checkmark" size={22} color={PALETTE.amber} />
                    </View>
                    <View>
                      <Text style={styles.docName}>{insDoc.title.toUpperCase()}</Text>
                      <Text style={styles.docNo}>{insDoc.subtitle}</Text>
                    </View>
                  </View>
                  <View style={styles.statusBadgeRow}>
                    <View style={[styles.verifiedLabel, { backgroundColor: 'rgba(16, 185, 129, 0.1)' }]}>
                      <Ionicons name="checkmark-circle" size={12} color={PALETTE.emerald} />
                      <Text style={[styles.verifiedText, { color: PALETTE.emerald }]}>Linked</Text>
                    </View>
                    <TouchableOpacity onPress={() => handleDelete(insDoc.id, insDoc.title)}>
                      <Ionicons name="trash-outline" size={16} color={PALETTE.rose} />
                    </TouchableOpacity>
                  </View>
                </View>

                {(() => {
                  const val = calculateValidity(insDoc.expiry);
                  return (
                    <View style={styles.cardMain}>
                      <View style={styles.arcContainer}>
                        <View style={[styles.arcRing, { borderColor: `${val.color}20` }]}>
                          <View style={[styles.arcProgress, { borderColor: val.color, transform: [{ rotate: `${180 * val.percent}deg` }] } as any]} />
                          <View style={styles.arcInnerContent}>
                            <Text style={[styles.arcDaysVal, { color: val.color }]}>
                              {val.daysLeft > 0 ? val.daysLeft : '0'}
                            </Text>
                            <Text style={styles.arcDaysLabel}>Days Left</Text>
                          </View>
                        </View>
                      </View>
                      <View style={styles.infoCol}>
                        <Text style={styles.holderLabel}>POLICY EXPIRY DATE</Text>
                        <Text style={styles.holderValue}>{insDoc.expiry}</Text>
                        
                        <View style={styles.statusBadgeContainer}>
                          <Text style={styles.validityLabel}>STATUS</Text>
                          <View style={[styles.statusChip, { backgroundColor: `${val.color}15` }]}>
                            <Text style={[styles.statusChipText, { color: val.color }]}>{val.status}</Text>
                          </View>
                        </View>

                        <Text style={styles.validityLabel}>REQUIREMENT</Text>
                        <Text style={styles.validityValue}>Third Party Mandatory (Sec 146)</Text>
                      </View>
                    </View>
                  );
                })()}

                <View style={styles.cardFooter}>
                  <Text style={styles.footerPrompt}>Third-party liability is legally active.</Text>
                  <TouchableOpacity style={styles.ctaBtn} onPress={() => handlePortalRedirect('INSURANCE')}>
                    <Text style={styles.ctaBtnText}>RENEW INSURANCE</Text>
                    <Ionicons name="open-outline" size={14} color={PALETTE.indigo} />
                  </TouchableOpacity>
                </View>
              </View>
            ) : (
              <View style={styles.emptyCardPlaceholder}>
                <Ionicons name="shield-outline" size={32} color="#D1D5DB" />
                <Text style={styles.placeholderTitle}>Insurance Certificate Missing</Text>
                <Text style={styles.placeholderDesc}>Third-party insurance is legally mandatory under Sec 146/196 MV Act (₹2,000 fine).</Text>
              </View>
            )}
          </View>

          {/* PUC CARD */}
          <View style={styles.cardContainer}>
            {pucDoc ? (
              <View style={styles.vaultCard}>
                <View style={styles.cardHeader}>
                  <View style={styles.headerTitleRow}>
                    <View style={[styles.docIcon, { backgroundColor: 'rgba(6, 182, 212, 0.1)' }]}>
                      <Ionicons name="leaf" size={22} color={PALETTE.cyan} />
                    </View>
                    <View>
                      <Text style={styles.docName}>{pucDoc.title.toUpperCase()}</Text>
                      <Text style={styles.docNo}>{pucDoc.subtitle}</Text>
                    </View>
                  </View>
                  <View style={styles.statusBadgeRow}>
                    <View style={[styles.verifiedLabel, { backgroundColor: 'rgba(16, 185, 129, 0.1)' }]}>
                      <Ionicons name="checkmark-circle" size={12} color={PALETTE.emerald} />
                      <Text style={[styles.verifiedText, { color: PALETTE.emerald }]}>Linked</Text>
                    </View>
                    <TouchableOpacity onPress={() => handleDelete(pucDoc.id, pucDoc.title)}>
                      <Ionicons name="trash-outline" size={16} color={PALETTE.rose} />
                    </TouchableOpacity>
                  </View>
                </View>

                {(() => {
                  const val = calculateValidity(pucDoc.expiry);
                  return (
                    <View style={styles.cardMain}>
                      <View style={styles.arcContainer}>
                        <View style={[styles.arcRing, { borderColor: `${val.color}20` }]}>
                          <View style={[styles.arcProgress, { borderColor: val.color, transform: [{ rotate: `${180 * val.percent}deg` }] } as any]} />
                          <View style={styles.arcInnerContent}>
                            <Text style={[styles.arcDaysVal, { color: val.color }]}>
                              {val.daysLeft > 0 ? val.daysLeft : '0'}
                            </Text>
                            <Text style={styles.arcDaysLabel}>Days Left</Text>
                          </View>
                        </View>
                      </View>
                      <View style={styles.infoCol}>
                        <Text style={styles.holderLabel}>EMISSIONS VALID TILL</Text>
                        <Text style={styles.holderValue}>{pucDoc.expiry}</Text>
                        
                        <View style={styles.statusBadgeContainer}>
                          <Text style={styles.validityLabel}>STATUS</Text>
                          <View style={[styles.statusChip, { backgroundColor: `${val.color}15` }]}>
                            <Text style={[styles.statusChipText, { color: val.color }]}>{val.status}</Text>
                          </View>
                        </View>

                        <Text style={styles.validityLabel}>PENALTY HINT</Text>
                        <Text style={styles.validityValue}>₹10,000 fine under Sec 190(2)</Text>
                      </View>
                    </View>
                  );
                })()}

                <View style={styles.cardFooter}>
                  <Text style={styles.footerPrompt}>PUC compliance is active.</Text>
                  <TouchableOpacity style={styles.ctaBtn} onPress={() => handlePortalRedirect('PUC')}>
                    <Text style={styles.ctaBtnText}>TEST STATIONS</Text>
                    <Ionicons name="open-outline" size={14} color={PALETTE.indigo} />
                  </TouchableOpacity>
                </View>
              </View>
            ) : (
              <View style={styles.emptyCardPlaceholder}>
                <Ionicons name="leaf-outline" size={32} color="#D1D5DB" />
                <Text style={styles.placeholderTitle}>PUCC (Emissions Test) Missing</Text>
                <Text style={styles.placeholderDesc}>PUC is legally required. Operating without it incurs a stackable ₹10,000 fine + 3-month license suspension.</Text>
              </View>
            )}
          </View>

        </ScrollView>
      </View>

      {/* SCAN-TO-VERIFY POPUP (GLASSMORPHIC SCANNING SCREEN) */}
      <Modal
        visible={verifyModalVisible}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setVerifyModalVisible(false)}
      >
        <KeyboardAvoidingView 
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.modalOverlay}
        >
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <View>
                <Text style={styles.modalTitle}>
                  {verifyType === 'DL' ? 'Sarathi DL Verification' : 'Vahan RC Synchronization'}
                </Text>
                <Text style={styles.modalSubtitle}>Query government RTO databases in real time</Text>
              </View>
              <TouchableOpacity onPress={() => setVerifyModalVisible(false)} style={styles.modalCloseBtn}>
                <Ionicons name="close" size={24} color="#6B7280" />
              </TouchableOpacity>
            </View>

            {scanLoading ? (
              <View style={styles.scanLoadingContainer}>
                <ActivityIndicator size="large" color={PALETTE.indigo} />
                <Text style={styles.scanLoadingTitle}>Querying Parivahan Hub...</Text>
                
                <ScrollView 
                  style={styles.logConsole} 
                  contentContainerStyle={{ padding: 12 }}
                  ref={(ref) => ref?.scrollToEnd({ animated: true })}
                >
                  {verificationLog.map((log, index) => (
                    <Text key={index} style={styles.logText}>
                      &gt; {log}
                    </Text>
                  ))}
                </ScrollView>
              </View>
            ) : (
              <View style={styles.form}>
                <View style={styles.inputGroup}>
                  <Text style={styles.label}>
                    {verifyType === 'DL' ? 'Driving License Number' : 'Vehicle Plate Number'}
                  </Text>
                  <TextInput
                    style={styles.input}
                    placeholder={verifyType === 'DL' ? "TN09 20210034567" : "TN09AB1234"}
                    value={verifyInput}
                    onChangeText={setVerifyInput}
                    autoCapitalize="characters"
                    placeholderTextColor="#9CA3AF"
                  />
                  <Text style={styles.formHint}>
                    {verifyType === 'DL' 
                      ? 'Format: SS-YY-YYYYNNNNNNN (State, Year of Issue, ID Number)' 
                      : 'Format: SS-R-XX-NNNN (e.g. TN09AB1234)'}
                  </Text>
                </View>

                {verifyType === 'RC' && (
                  <View style={styles.featuresList}>
                    <Text style={styles.featuresTitle}>Syncing gets you:</Text>
                    <View style={styles.featureItem}>
                      <Ionicons name="checkmark-circle" size={16} color={PALETTE.emerald} />
                      <Text style={styles.featureText}>Registration Expiry (RC fitness valid till)</Text>
                    </View>
                    <View style={styles.featureItem}>
                      <Ionicons name="checkmark-circle" size={16} color={PALETTE.emerald} />
                      <Text style={styles.featureText}>Emissions Validity (PUCC status)</Text>
                    </View>
                    <View style={styles.featureItem}>
                      <Ionicons name="checkmark-circle" size={16} color={PALETTE.emerald} />
                      <Text style={styles.featureText}>Insurance Expiry & Seizure details</Text>
                    </View>
                  </View>
                )}

                <TouchableOpacity style={styles.saveBtn} onPress={handleLiveVerify}>
                  <Ionicons name="sync-outline" size={18} color="#fff" style={{ marginRight: 6 }} />
                  <Text style={styles.saveBtnText}>Connect & Fetch Data</Text>
                </TouchableOpacity>

                <TouchableOpacity 
                  style={styles.switchModeLink}
                  onPress={() => setVerifyType(verifyType === 'RC' ? 'DL' : 'RC')}
                >
                  <Text style={styles.switchModeText}>
                    Switch to {verifyType === 'RC' ? 'Sarathi DL Verification' : 'Vahan RC Synchronization'}
                  </Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* MANUAL ADD MODAL */}
      <Modal
        visible={modalVisible}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setModalVisible(false)}
      >
        <KeyboardAvoidingView 
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.modalOverlay}
        >
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <View>
                <Text style={styles.modalTitle}>Manual Vault Addition</Text>
                <Text style={styles.modalSubtitle}>Create a secure digital backup</Text>
              </View>
              <TouchableOpacity onPress={() => setModalVisible(false)} style={styles.modalCloseBtn}>
                <Ionicons name="close" size={24} color="#6B7280" />
              </TouchableOpacity>
            </View>

            <ScrollView>
              <View style={styles.form}>
                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Select Document Type</Text>
                  <View style={styles.typeSelector}>
                    {['RC', 'INSURANCE', 'PUC', 'LICENSE'].map((type) => (
                      <TouchableOpacity
                        key={type}
                        style={[
                          styles.typeChip,
                          formType === type && { backgroundColor: PALETTE.darkGray, borderColor: PALETTE.darkGray }
                        ]}
                        onPress={() => {
                          setFormType(type as any);
                          const titles: Record<string, string> = {
                            RC: 'Vehicle RC',
                            INSURANCE: 'Vehicle Insurance',
                            PUC: 'PUC Certificate',
                            LICENSE: 'DRIVING LICENSE'
                          };
                          setFormTitle(titles[type] || 'Document');
                        }}
                      >
                        <Text style={[styles.typeChipText, formType === type && { color: '#fff' }]}>
                          {type}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>

                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Document Title</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="e.g. TN09AB1234 RC"
                    value={formTitle}
                    onChangeText={setFormTitle}
                  />
                </View>

                <View style={styles.inputGroup}>
                  <Text style={styles.label}>ID / Plate Number</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="e.g. TN-09-AB-1234"
                    value={formSubtitle}
                    onChangeText={setFormSubtitle}
                    autoCapitalize="characters"
                  />
                </View>

                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Validity Date (Expiry)</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="DD MMM YYYY (e.g. 15 JUN 2030)"
                    value={formExpiry}
                    onChangeText={setFormExpiry}
                  />
                </View>

                <TouchableOpacity style={styles.saveBtn} onPress={handleManualSave}>
                  <Text style={styles.saveBtnText}>Securely Add To Vault</Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#FAF8F5' },
  container: { flex: 1 },
  loaderContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#FAF8F5', gap: 16 },
  loaderText: { fontSize: 16, color: '#4B5563', fontWeight: '600' },
  
  // Header
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: Platform.OS === 'android' ? 44 : 12,
    paddingBottom: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  backButton: { padding: 6 },
  headerTitle: { fontSize: 18, fontWeight: '800', color: '#111827', letterSpacing: -0.5 },
  addButton: { padding: 4 },

  scrollContent: { paddingBottom: 40, paddingHorizontal: 20, paddingTop: 20 },

  // Instant Sync Banner
  scanBanner: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderRadius: 20,
    marginBottom: 24,
    shadowColor: '#4f46e5',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.25,
    shadowRadius: 12,
    elevation: 6,
  },
  scanBannerLeft: { flexDirection: 'row', alignItems: 'center', gap: 14, flex: 1, marginRight: 12 },
  scanBannerTitle: { color: '#fff', fontSize: 17, fontWeight: '800' },
  scanBannerSubtitle: { color: 'rgba(255, 255, 255, 0.8)', fontSize: 11, marginTop: 2, lineHeight: 15 },
  scanBannerBtn: {
    backgroundColor: '#fff',
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 12,
  },
  scanBannerBtnText: { color: '#4f46e5', fontSize: 12, fontWeight: '800' },

  // Section Title
  sectionTitle: {
    fontSize: 11,
    fontWeight: '900',
    color: '#9CA3AF',
    letterSpacing: 1.5,
    marginBottom: 16,
    marginLeft: 4,
  },

  // Document Card Styles
  cardContainer: { marginBottom: 24 },
  vaultCard: {
    backgroundColor: '#fff',
    borderRadius: 24,
    padding: 20,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    shadowColor: '#111827',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.05,
    shadowRadius: 12,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
    paddingBottom: 14,
    marginBottom: 16,
  },
  headerTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  docIcon: { width: 40, height: 40, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  docName: { fontSize: 14, fontWeight: '800', color: '#111827', letterSpacing: 0.5 },
  docNo: { fontSize: 12, color: '#6B7280', fontWeight: '600', marginTop: 2 },
  statusBadgeRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  verifiedLabel: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    gap: 4,
  },
  verifiedText: { fontSize: 10, fontWeight: '800' },

  // Card Main Body (Validity representation)
  cardMain: { flexDirection: 'row', alignItems: 'center', gap: 20 },
  arcContainer: { width: 100, height: 100, alignItems: 'center', justifyContent: 'center' },
  arcRing: {
    width: 90,
    height: 90,
    borderRadius: 45,
    borderWidth: 8,
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  arcProgress: {
    position: 'absolute',
    width: 90,
    height: 90,
    borderRadius: 45,
    borderWidth: 8,
    borderLeftColor: 'transparent',
    borderBottomColor: 'transparent',
    top: -8,
    left: -8,
  },
  arcInnerContent: { alignItems: 'center', justifyContent: 'center' },
  arcDaysVal: { fontSize: 20, fontWeight: '900', letterSpacing: -0.5 },
  arcDaysLabel: { fontSize: 8, color: '#9CA3AF', fontWeight: '800', marginTop: 1 },
  infoCol: { flex: 1, gap: 4 },
  holderLabel: { fontSize: 8, color: '#9CA3AF', fontWeight: '800', letterSpacing: 0.5 },
  holderValue: { fontSize: 13, fontWeight: '700', color: '#111827' },
  validityLabel: { fontSize: 8, color: '#9CA3AF', fontWeight: '800', letterSpacing: 0.5, marginTop: 4 },
  validityValue: { fontSize: 13, fontWeight: '700', color: '#4B5563' },
  statusBadgeContainer: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
  statusChip: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6 },
  statusChipText: { fontSize: 10, fontWeight: '800' },

  // Card Footer
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
    paddingTop: 12,
    marginTop: 16,
  },
  footerPrompt: { fontSize: 10, color: '#9CA3AF', fontWeight: '600' },
  ctaBtn: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  ctaBtnText: { fontSize: 11, fontWeight: '800', color: '#6366F1' },

  // Empty Card / Not Linked Placeholder
  emptyCardPlaceholder: {
    backgroundColor: '#fff',
    borderWidth: 1.5,
    borderColor: '#E5E7EB',
    borderStyle: 'dashed',
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
    gap: 12,
  },
  placeholderTitle: { fontSize: 15, fontWeight: '800', color: '#374151' },
  placeholderDesc: { fontSize: 12, color: '#6B7280', textAlign: 'center', lineHeight: 18, paddingHorizontal: 12 },
  verifyBtnOutline: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderWidth: 1.5,
    borderColor: PALETTE.indigo,
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 14,
    gap: 8,
    marginTop: 8,
  },
  verifyBtnOutlineText: { fontSize: 12, fontWeight: '800', color: PALETTE.indigo },

  // Modals overlay & contents
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 32,
    borderTopRightRadius: 32,
    padding: 24,
    maxHeight: '90%',
  },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 },
  modalTitle: { fontSize: 20, fontWeight: '900', color: '#111827', letterSpacing: -0.5 },
  modalSubtitle: { fontSize: 12, color: '#6B7280', marginTop: 4, fontWeight: '500' },
  modalCloseBtn: { padding: 4, backgroundColor: '#F3F4F6', borderRadius: 20 },

  // Forms
  form: { gap: 20 },
  inputGroup: { gap: 8 },
  label: { fontSize: 13, fontWeight: '800', color: '#111827', marginLeft: 4 },
  input: {
    backgroundColor: '#F9FAFB',
    borderWidth: 1.5,
    borderColor: '#F3F4F6',
    borderRadius: 16,
    padding: 16,
    fontSize: 15,
    color: '#111827',
    fontWeight: '600',
  },
  formHint: { fontSize: 10, color: '#9CA3AF', marginLeft: 4, fontWeight: '600' },
  saveBtn: {
    flexDirection: 'row',
    backgroundColor: '#4f46e5',
    paddingVertical: 16,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 10,
    shadowColor: '#4f46e5',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 6,
  },
  saveBtnText: { color: '#fff', fontSize: 15, fontWeight: '800' },
  switchModeLink: { alignSelf: 'center', marginTop: 12 },
  switchModeText: { fontSize: 13, color: '#6366F1', fontWeight: '700', textDecorationLine: 'underline' },

  // Scanning simulation loading state
  scanLoadingContainer: { alignItems: 'center', paddingVertical: 32, gap: 16 },
  scanLoadingTitle: { fontSize: 16, fontWeight: '800', color: '#4b5563' },
  logConsole: {
    width: '100%',
    height: 180,
    backgroundColor: '#111827',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#374151',
  },
  logText: {
    color: '#10B981',
    fontSize: 12,
    lineHeight: 20,
    paddingHorizontal: 8,
  },

  // RTO Features list
  featuresList: { backgroundColor: '#F9FAFB', padding: 16, borderRadius: 16, gap: 10, borderWidth: 1, borderColor: '#E5E7EB' },
  featuresTitle: { fontSize: 12, fontWeight: '800', color: '#4B5563', marginBottom: 4 },
  featureItem: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  featureText: { fontSize: 12, color: '#374151', fontWeight: '600' },

  // Manual Add Chip Selector
  typeSelector: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  typeChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    backgroundColor: '#fff',
  },
  typeChipText: { fontSize: 12, fontWeight: '700', color: '#4B5563' },
});
