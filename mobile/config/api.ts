import { Platform } from 'react-native';

// Auto-detect base URL for Android emulator or web/iOS simulator
export const API_BASE = Platform.OS === 'android' ? 'http://10.0.2.2:8001' : 'http://localhost:8001';
