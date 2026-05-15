import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface ChatSession {
  id: string;
  query: string;
  response: string;
  timestamp: number;
  isStarred?: boolean;
}

interface HistoryContextType {
  sessions: ChatSession[];
  addSession: (query: string, response: string) => void;
  deleteSession: (id: string) => void;
  renameSession: (id: string, newQuery: string) => void;
  toggleStar: (id: string) => void;
  clearHistory: () => void;
}

const HistoryContext = createContext<HistoryContextType | undefined>(undefined);
const HISTORY_KEY = '@drivelegal_sessions_v2';

export function HistoryProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  useEffect(() => {
    const loadSessions = async () => {
      try {
        const stored = await AsyncStorage.getItem(HISTORY_KEY);
        if (stored) {
          const parsed = JSON.parse(stored);
          setSessions(parsed);
        }
      } catch (e) {
        console.error('Failed to load sessions', e);
      }
    };
    loadSessions();
  }, []);

  const addSession = async (query: string, response: string) => {
    if (!query) return;
    
    setSessions(prev => {
      const filtered = prev.filter(s => s.query !== query);
      const newSession: ChatSession = {
        id: Date.now().toString(),
        query,
        response: response || "No response received.",
        timestamp: Date.now(),
      };
      
      const updated = [newSession, ...filtered].slice(0, 20);
      
      AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(updated)).catch(e => 
        console.error('Failed to save sessions', e)
      );
      
      return updated;
    });
  };

  const deleteSession = async (id: string) => {
    setSessions(prev => {
      const updated = prev.filter(s => s.id !== id);
      AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(updated)).catch(e => 
        console.error('Failed to update sessions after delete', e)
      );
      return updated;
    });
  };

  const renameSession = async (id: string, newQuery: string) => {
    setSessions(prev => {
      const updated = prev.map(s => s.id === id ? { ...s, query: newQuery } : s);
      AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(updated)).catch(e => 
        console.error('Failed to update sessions after rename', e)
      );
      return updated;
    });
  };

  const toggleStar = async (id: string) => {
    setSessions(prev => {
      const updated = prev.map(s => s.id === id ? { ...s, isStarred: !s.isStarred } : s);
      AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(updated)).catch(e => 
        console.error('Failed to update sessions after star toggle', e)
      );
      return updated;
    });
  };

  const clearHistory = async () => {
    setSessions([]);
    await AsyncStorage.removeItem(HISTORY_KEY);
  };

  return (
    <HistoryContext.Provider value={{ sessions, addSession, deleteSession, renameSession, toggleStar, clearHistory }}>
      {children}
    </HistoryContext.Provider>
  );
}

export function useHistory() {
  const context = useContext(HistoryContext);
  if (context === undefined) {
    throw new Error('useHistory must be used within a HistoryProvider');
  }
  return context;
}


