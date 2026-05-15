import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Linking } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface FineProps {
  fine: {
    amount_inr: number | null;
    section_ref: string;
    source_url: string;
    data_as_of: string;
  } | null;
}

export const FineCard: React.FC<FineProps> = ({ fine }) => {
  if (!fine || fine.amount_inr === null) {
    return (
      <View style={[styles.card, styles.emptyCard]}>
        <Ionicons name="alert-circle-outline" size={24} color="#ef4444" />
        <Text style={styles.emptyText}>Not in database — verify at official source</Text>
        {fine?.source_url && (
            <TouchableOpacity onPress={() => Linking.openURL(fine.source_url)}>
                <Text style={styles.linkText}>View Official Source</Text>
            </TouchableOpacity>
        )}
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <Text style={styles.label}>Estimated Fine</Text>
      <Text style={styles.amount}>₹{fine.amount_inr.toLocaleString()}</Text>
      <View style={styles.divider} />
      <Text style={styles.sectionHeader}>Section Ref: {fine.section_ref}</Text>
      <Text style={styles.timestamp}>Data as of: {new Date(fine.data_as_of).toLocaleDateString()}</Text>
      
      <TouchableOpacity 
        style={styles.button} 
        onPress={() => Linking.openURL(fine.source_url)}
      >
        <Text style={styles.buttonText}>Open Source URL</Text>
        <Ionicons name="open-outline" size={16} color="#fff" />
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    marginVertical: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 5,
  },
  emptyCard: {
    borderWidth: 1,
    borderColor: '#fecaca',
    backgroundColor: '#fef2f2',
    alignItems: 'center',
  },
  label: {
    fontSize: 14,
    color: '#64748b',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  amount: {
    fontSize: 48,
    fontWeight: '800',
    color: '#0f172a',
    marginVertical: 8,
  },
  divider: {
    height: 1,
    backgroundColor: '#e2e8f0',
    marginVertical: 12,
  },
  sectionHeader: {
    fontSize: 16,
    color: '#334155',
    fontWeight: '600',
  },
  timestamp: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 4,
  },
  emptyText: {
    fontSize: 16,
    color: '#b91c1c',
    textAlign: 'center',
    marginTop: 8,
    marginBottom: 8,
  },
  linkText: {
    color: '#2563eb',
    textDecorationLine: 'underline',
    fontWeight: '600',
  },
  button: {
    backgroundColor: '#2563eb',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 8,
    marginTop: 16,
    gap: 8,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 14,
  }
});
