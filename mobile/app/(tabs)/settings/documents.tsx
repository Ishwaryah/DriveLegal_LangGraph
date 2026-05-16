import React, { useState } from 'react';
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
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useSettings } from '../../../hooks/useSettings';
import { useGeoFineAlert } from '../../../hooks/useGeoFineAlert';
import { useDocuments, StoredDocument } from '../../../hooks/useDocuments';

const DOCUMENT_TYPES = [
  { id: 'RC', label: 'Vehicle RC', icon: 'document-text-outline', color: '#10B981' },
  { id: 'INSURANCE', label: 'Insurance', icon: 'shield-outline', color: '#F59E0B' },
  { id: 'PUC', label: 'PUC', icon: 'leaf-outline', color: '#06B6D4' },
  { id: 'FASTAG', label: 'FasTag', icon: 'barcode-outline', color: '#6366F1' },
  { id: 'OTHER', label: 'Other', icon: 'file-tray-outline', color: '#6B7280' },
];

export default function DocumentVaultScreen() {
  const router = useRouter();
  const { profile } = useSettings();
  const { state } = useGeoFineAlert();
  const { documents, license, addDocument, updateLicense, removeDocument, loading } = useDocuments();

  const [modalVisible, setModalVisible] = useState(false);
  const [isLicenseMode, setIsLicenseMode] = useState(false);
  const [selectedType, setSelectedType] = useState('RC');
  
  // Form State
  const [formTitle, setFormTitle] = useState('');
  const [formSubtitle, setFormSubtitle] = useState('');
  const [formExpiry, setFormExpiry] = useState('');

  const handleAddPress = () => {
    setIsLicenseMode(false);
    setSelectedType('RC');
    setFormTitle('Vehicle RC');
    setFormSubtitle('');
    setFormExpiry('');
    setModalVisible(true);
  };

  const handleEditLicense = () => {
    setIsLicenseMode(true);
    setFormTitle(license?.title || 'DRIVING LICENSE');
    setFormSubtitle(license?.subtitle || '');
    setFormExpiry(license?.expiry || '');
    setModalVisible(true);
  };

  const handleTypeSelect = (typeId: string, label: string) => {
    setSelectedType(typeId);
    setFormTitle(label);
  };

  const handleSave = async () => {
    if (!formSubtitle || !formExpiry) {
      Alert.alert('Missing info', 'Please fill in all required fields.');
      return;
    }

    if (isLicenseMode) {
      await updateLicense({
        title: 'DRIVING LICENSE',
        subtitle: formSubtitle.toUpperCase(),
        expiry: formExpiry,
      });
    } else {
      await addDocument({
        title: formTitle || 'Document',
        subtitle: formSubtitle.toUpperCase(),
        expiry: formExpiry,
        type: selectedType as any,
      });
    }
    setModalVisible(false);
  };

  const handleDelete = (id: string) => {
    Alert.alert('Delete Document', 'This action cannot be undone.', [
      { text: 'Keep It', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: () => removeDocument(id) },
    ]);
  };

  if (loading) return null;

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>

        {/* HEADER */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Document vault</Text>
          <TouchableOpacity style={styles.addButton} onPress={handleAddPress}>
            <Text style={styles.addButtonText}>+ Add</Text>
          </TouchableOpacity>
        </View>

        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>

          {/* DRIVING LICENSE CARD */}
          <TouchableOpacity activeOpacity={0.9} onPress={handleEditLicense}>
            <View style={styles.licenseCard}>
              <View style={styles.licenseTopRow}>
                <View>
                  <Text style={styles.licenseType}>DRIVING LICENSE</Text>
                  <Text style={styles.licenseCountry}>Republic of India - {state || 'Tamil Nadu'}</Text>
                </View>
                {license && (
                  <View style={styles.verifiedBadge}>
                    <Ionicons name="checkmark-circle" size={14} color="#4ADE80" />
                    <Text style={styles.verifiedText}>Verified</Text>
                  </View>
                )}
              </View>

              <Text style={styles.licenseNumber}>
                {license?.subtitle || 'NOT LINKED'}
              </Text>

              <View style={styles.licenseBottomRow}>
                <View>
                  <Text style={styles.licenseFieldLabel}>HOLDER</Text>
                  <Text style={styles.licenseFieldValue}>{profile.name || 'User'}</Text>
                </View>
                <View>
                  <Text style={styles.licenseFieldLabel}>VALID TILL</Text>
                  <Text style={styles.licenseFieldValue}>{license?.expiry || '---'}</Text>
                </View>
                <View style={styles.qrPlaceholder}>
                  {[...Array(4)].map((_, i) => (
                    <View key={i} style={styles.qrRow}>
                      {[...Array(4)].map((__, j) => (
                        <View key={j} style={[styles.qrDot, { opacity: Math.random() > 0.4 ? 1 : 0.2 }]} />
                      ))}
                    </View>
                  ))}
                </View>
              </View>
              {!license && <Text style={styles.tapToSetup}>Tap to setup your digital license</Text>}
            </View>
          </TouchableOpacity>

          {/* OTHER DOCUMENTS */}
          <Text style={styles.sectionTitle}>MY DOCUMENTS</Text>

          {documents.length > 0 ? (
            <View style={styles.docList}>
              {documents.map((doc, index) => {
                const typeData = DOCUMENT_TYPES.find(t => t.id === doc.type) || DOCUMENT_TYPES[0];
                return (
                  <DocItem
                    key={doc.id}
                    icon={typeData.icon}
                    iconBg={`${typeData.color}15`}
                    iconColor={typeData.color}
                    title={doc.title}
                    subtitle={doc.subtitle}
                    status={`Expires ${doc.expiry}`}
                    statusColor={typeData.color}
                    isLast={index === documents.length - 1}
                    onDelete={() => handleDelete(doc.id)}
                  />
                );
              })}
            </View>
          ) : (
            <View style={styles.emptyState}>
              <View style={styles.emptyIconCircle}>
                <Ionicons name="folder-open" size={32} color="#D1D5DB" />
              </View>
              <Text style={styles.emptyTextTitle}>No documents found</Text>
              <Text style={styles.emptyText}>Keep all your vehicle papers in one secure place.</Text>
              <TouchableOpacity style={styles.emptyBtn} onPress={handleAddPress}>
                <Text style={styles.emptyBtnText}>Add Document</Text>
              </TouchableOpacity>
            </View>
          )}

        </ScrollView>
      </View>

      {/* ADD/EDIT MODAL */}
      <Modal
        visible={modalVisible}
        animationType="fade"
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
                <Text style={styles.modalTitle}>
                  {isLicenseMode ? 'Verify License' : 'New Document'}
                </Text>
                <Text style={styles.modalSubtitle}>Enter details as printed on the original</Text>
              </View>
              <TouchableOpacity onPress={() => setModalVisible(false)} style={styles.modalCloseBtn}>
                <Ionicons name="close" size={24} color="#6B7280" />
              </TouchableOpacity>
            </View>

            <ScrollView bounces={false}>
              <View style={styles.form}>
                {!isLicenseMode && (
                  <View style={styles.inputGroup}>
                    <Text style={styles.label}>Select Document Type</Text>
                    <View style={styles.typeSelector}>
                      {DOCUMENT_TYPES.map((t) => (
                        <TouchableOpacity
                          key={t.id}
                          style={[
                            styles.typeChip,
                            selectedType === t.id && { backgroundColor: '#111827', borderColor: '#111827' }
                          ]}
                          onPress={() => handleTypeSelect(t.id, t.label)}
                        >
                          <Ionicons 
                            name={t.icon as any} 
                            size={14} 
                            color={selectedType === t.id ? '#fff' : '#6B7280'} 
                            style={{ marginRight: 6 }}
                          />
                          <Text style={[styles.typeChipText, selectedType === t.id && { color: '#fff' }]}>
                            {t.label}
                          </Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>
                )}

                {!isLicenseMode && selectedType === 'OTHER' && (
                  <View style={styles.inputGroup}>
                    <Text style={styles.label}>Custom Title</Text>
                    <TextInput
                      style={styles.input}
                      placeholder="e.g. Emissions Test"
                      value={formTitle}
                      onChangeText={setFormTitle}
                      placeholderTextColor="#9CA3AF"
                    />
                  </View>
                )}

                <View style={styles.inputGroup}>
                  <Text style={styles.label}>
                    {isLicenseMode ? 'License Number' : 'ID Number'}
                  </Text>
                  <View style={styles.inputWrapper}>
                    <TextInput
                      style={styles.input}
                      placeholder={isLicenseMode ? "TN09 20210034567" : "ABC-12345-XY"}
                      value={formSubtitle}
                      onChangeText={setFormSubtitle}
                      autoCapitalize="characters"
                      placeholderTextColor="#9CA3AF"
                    />
                    <Text style={styles.idHint}>{formSubtitle.length} chars</Text>
                  </View>
                </View>

                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Valid Until (Expiry)</Text>
                  <TextInput
                    style={styles.input}
                    placeholder="DD MMM YYYY (e.g. 15 JUN 2030)"
                    value={formExpiry}
                    onChangeText={setFormExpiry}
                    placeholderTextColor="#9CA3AF"
                  />
                </View>

                <TouchableOpacity style={styles.saveBtn} onPress={handleSave}>
                  <Text style={styles.saveBtnText}>Securely Save</Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        </KeyboardAvoidingView>
      </Modal>
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
  onDelete: () => void;
}

function DocItem({ icon, iconBg, iconColor, title, subtitle, status, statusColor, isLast, onDelete }: DocItemProps) {
  return (
    <>
      <View style={styles.docItem}>
        <View style={[styles.docIconWrapper, { backgroundColor: iconBg }]}>
          <Ionicons name={icon as any} size={20} color={iconColor} />
        </View>
        <View style={styles.docTextContainer}>
          <Text style={styles.docTitle}>{title}</Text>
          <Text style={styles.docSubtitle}>{subtitle}</Text>
          <Text style={[styles.docStatus, { color: statusColor }]}>{status}</Text>
        </View>
        <TouchableOpacity onPress={onDelete} style={styles.deleteBtn}>
          <Ionicons name="trash-outline" size={18} color="#EF4444" />
        </TouchableOpacity>
      </View>
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
    paddingTop: Platform.OS === 'android' ? 44 : 12,
    paddingBottom: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  backButton: { padding: 6 },
  headerTitle: { fontSize: 18, fontWeight: '800', color: '#111827', letterSpacing: -0.5 },
  addButton: { padding: 6 },
  addButtonText: { fontSize: 14, fontWeight: '800', color: '#D97706' },

  scrollContent: { paddingBottom: 40, paddingHorizontal: 20, paddingTop: 24 },

  // Driving License Card
  licenseCard: {
    backgroundColor: '#111827',
    borderRadius: 24,
    padding: 24,
    gap: 16,
    marginBottom: 32,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.4,
    shadowRadius: 20,
    elevation: 10,
  },
  licenseTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  licenseType: {
    fontSize: 10,
    fontWeight: '900',
    color: '#6B7280',
    letterSpacing: 1.5,
    marginBottom: 4,
  },
  licenseCountry: { fontSize: 12, color: '#9CA3AF', fontWeight: '500' },
  verifiedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(74,222,128,0.1)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
    gap: 4,
    borderWidth: 1,
    borderColor: 'rgba(74,222,128,0.2)',
  },
  verifiedText: { fontSize: 11, fontWeight: '800', color: '#4ADE80' },

  licenseNumber: {
    fontSize: 28,
    fontWeight: '900',
    color: '#fff',
    letterSpacing: 2,
    marginVertical: 4,
  },

  licenseBottomRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 24,
  },
  licenseFieldLabel: {
    fontSize: 9,
    color: '#6B7280',
    fontWeight: '800',
    letterSpacing: 1,
    marginBottom: 4,
  },
  licenseFieldValue: { fontSize: 14, fontWeight: '700', color: '#fff' },
  tapToSetup: { color: '#F59E0B', fontSize: 12, fontWeight: '700', marginTop: 12, textDecorationLine: 'underline' },

  // QR Code visual
  qrPlaceholder: {
    marginLeft: 'auto',
    gap: 4,
  },
  qrRow: { flexDirection: 'row', gap: 4 },
  qrDot: {
    width: 6,
    height: 6,
    borderRadius: 1.5,
    backgroundColor: '#374151',
  },

  // Section title
  sectionTitle: {
    fontSize: 11,
    fontWeight: '900',
    color: '#9CA3AF',
    letterSpacing: 1.5,
    marginBottom: 16,
    marginLeft: 4,
  },

  // Doc list
  docList: {
    backgroundColor: '#fff',
    borderRadius: 24,
    paddingHorizontal: 20,
    borderWidth: 1,
    borderColor: '#F3F4F6',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 2,
  },
  docItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 18,
    gap: 16,
  },
  docIconWrapper: {
    width: 48,
    height: 48,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  docTextContainer: { flex: 1, gap: 2 },
  docTitle: { fontSize: 16, fontWeight: '700', color: '#111827' },
  docSubtitle: { fontSize: 13, color: '#6B7280', fontWeight: '500' },
  docStatus: { fontSize: 11, fontWeight: '700', marginTop: 4 },
  docDivider: { height: 1, backgroundColor: '#F9FAFB', marginLeft: 64 },
  deleteBtn: { padding: 6 },

  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
    backgroundColor: '#fff',
    borderRadius: 28,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderStyle: 'dashed',
  },
  emptyIconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#F9FAFB',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  emptyTextTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#111827',
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 14,
    color: '#6B7280',
    textAlign: 'center',
    paddingHorizontal: 40,
    lineHeight: 20,
  },
  emptyBtn: {
    marginTop: 24,
    backgroundColor: '#111827',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 14,
  },
  emptyBtnText: {
    color: '#fff',
    fontWeight: '800',
    fontSize: 14,
  },

  // Modal Styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 32,
    borderTopRightRadius: 32,
    padding: 24,
    maxHeight: '90%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 28,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: '900',
    color: '#111827',
    letterSpacing: -0.5,
  },
  modalSubtitle: {
    fontSize: 13,
    color: '#6B7280',
    marginTop: 4,
    fontWeight: '500',
  },
  modalCloseBtn: {
    padding: 4,
    backgroundColor: '#F3F4F6',
    borderRadius: 20,
  },
  form: { gap: 20 },
  inputGroup: { gap: 10 },
  label: { fontSize: 13, fontWeight: '800', color: '#111827', marginLeft: 4 },
  typeSelector: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 4,
  },
  typeChip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    backgroundColor: '#fff',
  },
  typeChipText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#4B5563',
  },
  inputWrapper: {
    position: 'relative',
    justifyContent: 'center',
  },
  input: {
    backgroundColor: '#F9FAFB',
    borderWidth: 1.5,
    borderColor: '#F3F4F6',
    borderRadius: 16,
    padding: 16,
    fontSize: 16,
    color: '#111827',
    fontWeight: '600',
  },
  idHint: {
    position: 'absolute',
    right: 16,
    fontSize: 11,
    color: '#9CA3AF',
    fontWeight: '700',
  },
  saveBtn: {
    backgroundColor: '#D97706',
    paddingVertical: 18,
    borderRadius: 18,
    alignItems: 'center',
    marginTop: 12,
    shadowColor: '#D97706',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 8,
  },
  saveBtnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
});


