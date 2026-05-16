import { useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface StoredDocument {
  id: string;
  title: string;
  subtitle: string;
  expiry: string;
  type: 'RC' | 'INSURANCE' | 'PUC' | 'OTHER' | 'LICENSE';
}

export function useDocuments() {
  const [documents, setDocuments] = useState<StoredDocument[]>([]);
  const [license, setLicense] = useState<StoredDocument | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const savedDocs = await AsyncStorage.getItem('user_documents');
      const savedLicense = await AsyncStorage.getItem('user_license');
      if (savedDocs) setDocuments(JSON.parse(savedDocs));
      if (savedLicense) setLicense(JSON.parse(savedLicense));
    } catch (e) {
      console.error('Failed to load documents', e);
    } finally {
      setLoading(false);
    }
  };

  const addDocument = async (doc: Omit<StoredDocument, 'id'>) => {
    const newDoc = { ...doc, id: Date.now().toString() };
    const newDocs = [...documents, newDoc];
    setDocuments(newDocs);
    await AsyncStorage.setItem('user_documents', JSON.stringify(newDocs));
  };

  const updateLicense = async (data: { title: string; subtitle: string; expiry: string }) => {
    const newLicense: StoredDocument = { 
      ...data, 
      id: 'license', 
      type: 'LICENSE',
      title: data.title || 'DRIVING LICENSE'
    };
    setLicense(newLicense);
    await AsyncStorage.setItem('user_license', JSON.stringify(newLicense));
  };

  const removeDocument = async (id: string) => {
    const newDocs = documents.filter(d => d.id !== id);
    setDocuments(newDocs);
    await AsyncStorage.setItem('user_documents', JSON.stringify(newDocs));
  };

  return { documents, license, addDocument, updateLicense, removeDocument, loading };
}
