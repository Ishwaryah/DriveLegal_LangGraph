import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface RuleProps {
  rule: {
    title: string;
    description: string;
    state_override?: string;
  } | null;
}

export const RuleCard: React.FC<RuleProps> = ({ rule }) => {
  if (!rule) return null;

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Ionicons name="document-text" size={20} color="#2563eb" />
        <Text style={styles.title}>{rule.title}</Text>
      </View>
      
      <View style={styles.content}>
        <Text style={styles.description}>{rule.description}</Text>
      </View>

      {rule.state_override && (
        <View style={styles.overrideContainer}>
          <View style={styles.overrideBadge}>
            <Ionicons name="location" size={12} color="#fff" />
            <Text style={styles.overrideBadgeText}>STATE SPECIFIC</Text>
          </View>
          <Text style={styles.overrideText}>{rule.state_override}</Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#f8fafc',
    borderRadius: 16,
    padding: 20,
    marginVertical: 10,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 8,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1e293b',
  },
  content: {
    marginBottom: 12,
  },
  description: {
    fontSize: 15,
    lineHeight: 22,
    color: '#475569',
  },
  overrideContainer: {
    backgroundColor: '#eff6ff',
    borderRadius: 8,
    padding: 12,
    marginTop: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#3b82f6',
  },
  overrideBadge: {
    backgroundColor: '#3b82f6',
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    marginBottom: 8,
    gap: 4,
  },
  overrideBadgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '900',
  },
  overrideText: {
    fontSize: 14,
    color: '#1d4ed8',
    fontWeight: '500',
    fontStyle: 'italic',
  }
});
