import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useUI } from '../hooks/useUI';
import { useRouter, usePathname } from 'expo-router';

export function SidebarRail() {
  const { toggleSidebar, isSidebarOpen } = useUI();
  const router = useRouter();
  const pathname = usePathname();
  const [hoveredIcon, setHoveredIcon] = useState<string | null>(null);

  // Custom Panel Icon (Square with vertical line)
  const PanelIcon = ({ color }: { color: string }) => (
    <View style={styles.panelIconContainer}>
      <View style={[styles.panelIconOuter, { borderColor: color }]}>
        <View style={[styles.panelIconInner, { borderRightColor: color }]} />
      </View>
    </View>
  );

  const RailIcon = ({
    name,
    label,
    active = false,
    onPress
  }: {
    name: any,
    label: string,
    active?: boolean,
    onPress: () => void
  }) => (
    <View style={styles.iconWrapper}>
      <TouchableOpacity
        onPress={onPress}
        style={[styles.iconButton, active && styles.iconActive]}
        // @ts-ignore
        onMouseEnter={() => setHoveredIcon(label)}
        onMouseLeave={() => setHoveredIcon(null)}
      >
        <Ionicons name={name} size={20} color={active ? "#fff" : "#9ca3af"} />
      </TouchableOpacity>
      
      {hoveredIcon === label && Platform.OS === 'web' && (
        <View style={styles.tooltip}>
          <Text style={styles.tooltipText}>{label}</Text>
        </View>
      )}
    </View>
  );

  const handleNewChat = () => {
    router.push({ pathname: '/', params: { new: 'true', t: Date.now() } });
  };

  return (
    <View style={styles.rail}>
      <View style={styles.topSection}>
        <View style={styles.iconWrapper}>
          <TouchableOpacity 
            onPress={toggleSidebar} 
            style={styles.toggleButton}
            // @ts-ignore
            onMouseEnter={() => setHoveredIcon('Expand')}
            onMouseLeave={() => setHoveredIcon(null)}
          >
            <PanelIcon color="#fff" />
          </TouchableOpacity>
          {hoveredIcon === 'Expand' && Platform.OS === 'web' && (
            <View style={styles.tooltip}>
              <Text style={styles.tooltipText}>Expand</Text>
            </View>
          )}
        </View>

        <View style={styles.midIcons}>
          <RailIcon
            name="add"
            label="New Chat"
            active={pathname === '/' && isSidebarOpen === false}
            onPress={handleNewChat}
          />
          <RailIcon
            name="chatbubble-outline"
            label="AI Assistant"
            active={pathname === '/'}
            onPress={() => router.push('/')}
          />
          <RailIcon
            name="map-outline"
            label="Traffic Map"
            active={pathname === '/zones'}
            onPress={() => router.push('/zones')}
          />
          <RailIcon
            name="calculator-outline"
            label="Calculator"
            onPress={() => router.push({ pathname: '/', params: { calc: 'true', t: Date.now() } })}
          />
          <View style={styles.separator} />
          <RailIcon
            name="time-outline"
            label="Recent"
            onPress={() => toggleSidebar()}
          />
          <RailIcon
            name="book-outline"
            label="Library"
            onPress={() => { }}
          />
        </View>
      </View>

      <View style={styles.footerIcons}>
        <RailIcon
          name="settings-outline"
          label="Settings"
          active={pathname === '/settings'}
          onPress={() => router.push('/settings')}
        />
        <TouchableOpacity style={styles.userButton}>
          <View style={styles.userDot} />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  rail: {
    width: 60,
    backgroundColor: '#0f1115',
    borderRightWidth: 1,
    borderRightColor: '#1f2937',
    height: '100%',
    alignItems: 'center',
    paddingVertical: 16,
    justifyContent: 'space-between',
    zIndex: 1000,
  },
  topSection: {
    alignItems: 'center',
    width: '100%',
  },
  toggleButton: {
    padding: 10,
    borderRadius: 8,
    marginBottom: 16,
  },
  panelIconContainer: {
    width: 24,
    height: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  panelIconOuter: {
    width: 20,
    height: 18,
    borderWidth: 1.5,
    borderRadius: 3,
    flexDirection: 'row',
    alignItems: 'stretch',
  },
  panelIconInner: {
    width: 6,
    height: '100%',
    borderRightWidth: 1.5,
  },
  midIcons: {
    alignItems: 'center',
    gap: 12,
  },
  iconWrapper: {
    position: 'relative',
    alignItems: 'center',
  },
  iconButton: {
    padding: 10,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconActive: {
    backgroundColor: '#1e293b',
  },
  tooltip: {
    position: 'absolute',
    left: 55,
    backgroundColor: '#1f2937',
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#374151',
    // @ts-ignore
    whiteSpace: 'nowrap',
    zIndex: 1100,
  },
  tooltipText: {
    color: '#D1D5DB',
    fontSize: 11,
    fontWeight: '600',
  },
  separator: {
    height: 1,
    width: 24,
    backgroundColor: '#1f2937',
    marginVertical: 4,
  },
  footerIcons: {
    paddingBottom: 16,
    gap: 16,
    alignItems: 'center',
  },
  userButton: {
    padding: 2,
  },
  userDot: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#3b82f6',
    borderWidth: 2,
    borderColor: '#1e293b',
  }
});
