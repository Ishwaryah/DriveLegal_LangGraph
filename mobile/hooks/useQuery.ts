import { useState, useEffect } from 'react';
import { Platform, Alert } from 'react-native';
// SQLite is loaded conditionally inside the hook
import Constants from 'expo-constants';

interface QueryResult {
  status: string;
  intent?: string;
  // NLP pipeline uses `text`; Gemini agent uses `response`
  text?: string;
  response?: string;
  query_summary?: string;
  agent_powered?: boolean;
  tools_used?: any[];
  fine: {
    amount_inr: number | null;
    section_ref: string;
    source_url: string;
    data_as_of: string;
  } | null;
  rule: {
    rule_id: string;
    title: string;
    description: string;
    state_override?: string;
  } | null;
}

interface UseQueryResult {
  data: QueryResult | null;
  isLoading: boolean;
  isOffline: boolean;
  error: string | null;
  submitQuery: (text: string, gps?: { lat: number, lon: number } | null, country?: string) => Promise<void>;
}

export function useQuery(): UseQueryResult {
  const [data, setData] = useState<QueryResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [session, setSession] = useState<any>({});

  const db = Platform.OS !== 'web' ? require('expo-sqlite').openDatabase('drivelegal.db') : null;

  const submitQuery = async (text: string, gps?: { lat: number, lon: number } | null, country?: string) => {
    setIsLoading(true);
    setError(null);
    setData(null);
    
    // Fallback IP for this machine: 10.129.22.97
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
    
    const BASE_URL = `http://${host}:8001`;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000);

      // Attempt network fetch
      const response = await fetch(`${BASE_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          text: text, 
          session: session,
          gps: gps,
          country: country
        }),
        signal: controller.signal as any,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const result = await response.json();
        setData(result);
        if (result.session) {
          setSession((prevSession: any) => ({ ...prevSession, ...result.session }));
        }
        setIsOffline(false);
      } else {
        throw new Error('Network response not ok');
      }
    } catch (err: any) {
      console.log(`Network failed for ${BASE_URL}:`, err);
      setIsOffline(true);
      
      const fetchErrorMsg = err.name === 'AbortError' 
        ? `[TIMEOUT] Request to ${BASE_URL} timed out. Is the backend frozen?` 
        : `[CONNECT_ERROR] Failed to reach ${BASE_URL} (${err.message}). Are you on the same Wi-Fi?`;

      // Fallback to local SQLite lookup
      if (Platform.OS !== 'web' && db) {
        try {
          db.transaction((tx) => {
            tx.executeSql(
              'SELECT * FROM fines WHERE rule_description LIKE ? LIMIT 1',
              [`%${text}%`],
              (_, { rows }) => {
                if (rows.length > 0) {
                  const item = rows.item(0);
                  setData({
                    status: 'ok',
                    intent: 'fine_lookup',
                    text: `Localized Info: ${item.description}`,
                    query_summary: `Local lookup for ${text}`,
                    fine: {
                      amount_inr: item.amount,
                      section_ref: item.section,
                      source_url: item.url,
                      data_as_of: item.updated_at,
                    },
                    rule: {
                      rule_id: item.rule_id || 'LOCAL',
                      title: item.title,
                      description: item.description,
                    }
                  });
                } else {
                  setError('Data not available for this query');
                  setData(null);
                }
              },
              (_, error) => {
                setError('Local database error');
                return false;
              }
            );
          });
        } catch (localErr) {
          setError('Data not available for this query');
        }
      } else {
        setError(fetchErrorMsg);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return { data, isLoading, isOffline, error, submitQuery };
}

