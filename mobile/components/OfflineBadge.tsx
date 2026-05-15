import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface Props {
  isOffline: boolean;
}

export const OfflineBadge: React.FC<Props> = ({ isOffline }) => {
  if (!isOffline) return null;

  return (
    <View style={styles.container}>
      <Ionicons name="cloud-offline" size={16} color="#92400e" />
      <Text style={styles.text}>OFFLINE MODE — Local DB</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#fef3c7',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 20,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderWidth: 1,
    borderColor: '#fcd34d',
    alignSelf: 'center',
    marginVertical: 10,
  },
  text: {
    color: '#92400e',
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
});
