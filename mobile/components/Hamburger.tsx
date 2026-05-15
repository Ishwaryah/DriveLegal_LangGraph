import React from 'react';
import { TouchableOpacity, StyleSheet, View, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useUI } from '../hooks/useUI';

export function Hamburger({ color = "#9ca3af", style = {} }: { color?: string, style?: any }) {
  const { toggleSidebar } = useUI();

  return (
    <TouchableOpacity onPress={toggleSidebar} style={[styles.button, style]}>
      <Ionicons name="menu-outline" size={24} color={color} />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: '#262626', // Matching sidebar toggle background
    justifyContent: 'center',
    alignItems: 'center',
  }
});
