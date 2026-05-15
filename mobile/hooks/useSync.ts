import { useState } from 'react';
import { Platform } from 'react-native';
import Constants from 'expo-constants';
import { useLocalDB } from './useLocalDB';

interface SyncStatus {
  lastSync: {
    fines: string;
    rules: string;
    zones: string;
  };
  counts: {
    fines: number;
    rules: number;
    zones: number;
  };
}

export function useSync() {
  const [isSyncing, setIsSyncing] = useState(false);
  const { upsertFines, upsertRules } = useLocalDB();
  const [syncStatus, setSyncStatus] = useState<SyncStatus>({
    lastSync: {
      fines: '2024-04-16',
      rules: '2024-04-16',
      zones: '2024-04-15',
    },
    counts: {
      fines: 1240,
      rules: 450,
      zones: 85,
    }
  });

  const getBaseUrl = () => {
    let host = Constants.expoConfig?.hostUri?.split(':')[0];
    if (!host) {
      if (Platform.OS === 'web' && typeof window !== 'undefined') {
        host = window.location.hostname;
      } else if (Platform.OS === 'android') {
        host = '10.0.2.2'; // Emulator loopback
      } else {
        host = 'localhost'; // iOS simulator / web
      }
    }
    return `http://${host}:8001`;
  };

  const triggerSync = async () => {
    setIsSyncing(true);
    const baseUrl = getBaseUrl();
    
    try {
      // 1. Fetch rules
      const rulesRes = await fetch(`${baseUrl}/sync/rules`);
      if (rulesRes.ok) {
        const rules = await rulesRes.json();
        // Transform rules if needed (backend returns raw rules list)
        const transformedRules = rules.map((r: any) => ({
          rule_id: r.rule_id,
          section: r.section,
          title: r.title,
          description: r.description,
          state: r.country === 'IN' ? 'National' : r.country,
          raw_json: JSON.stringify(r)
        }));
        await upsertRules(transformedRules);
      }

      // 2. Fetch fines
      const finesRes = await fetch(`${baseUrl}/sync/fines`);
      if (finesRes.ok) {
        const fines = await finesRes.json();
        await upsertFines(fines);
      }

      // Update local status
      const statusRes = await fetch(`${baseUrl}/sync/status`);
      if (statusRes.ok) {
        const status = await statusRes.json();
        setSyncStatus({
          lastSync: {
            fines: new Date().toISOString().split('T')[0],
            rules: new Date().toISOString().split('T')[0],
            zones: new Date().toISOString().split('T')[0],
          },
          counts: {
            fines: status.fines_count,
            rules: status.rules_count,
            zones: status.zones_count,
          }
        });
      }
    } catch (err) {
      console.error('Sync failed:', err);
    } finally {
      setIsSyncing(false);
    }
  };

  const clearCache = async () => {
    console.log('Clearing local database...');
    // In a real app, you might want to expose a drop function in useLocalDB
  };

  return { isSyncing, syncStatus, triggerSync, clearCache };
}
