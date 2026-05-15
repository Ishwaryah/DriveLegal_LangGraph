import { useState, useEffect, useRef, useCallback } from 'react';
import * as Location from 'expo-location';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useLocalDB } from './useLocalDB';

const CACHE_KEY = '@drivelegal_last_location_v1';

export const COUNTRY_ISO: Record<string, string> = {
  India: 'IN',
  'United Arab Emirates': 'AE',
  Singapore: 'SG',
  'United Kingdom': 'GB',
};

export const FLAG_EMOJI: Record<string, string> = {
  IN: '🇮🇳',
  AE: '🇦🇪',
  SG: '🇸🇬',
  GB: '🇬🇧',
};

export const STATE_CODE: Record<string, string> = {
  'Tamil Nadu': 'TN',
  Maharashtra: 'MH',
  Karnataka: 'KA',
  Delhi: 'DL',
  'National Capital Territory of Delhi': 'DL',
  Gujarat: 'GJ',
  Telangana: 'TG',
};

export const STATE_FINE_INFO: Record<string, {
  name: string;
  helmetFine: string;
  speedFine: string;
}> = {
  TN: {
    name: 'Tamil Nadu',
    helmetFine: '₹1,000 (compoundable at ₹500 at local RTO)',
    speedFine: '₹1,000–₹2,000 (Sec 183 MV Act)',
  },
  MH: {
    name: 'Maharashtra',
    helmetFine: '₹500',
    speedFine: '₹1,000–₹2,000 (Sec 183 MV Act)',
  },
  KA: {
    name: 'Karnataka',
    helmetFine: '₹500',
    speedFine: '₹1,000–₹2,000 (Sec 183 MV Act)',
  },
  DL: {
    name: 'Delhi',
    helmetFine: '₹1,000',
    speedFine: '₹2,000–₹4,000 (Sec 183 MV Act)',
  },
  GJ: {
    name: 'Gujarat',
    helmetFine: '₹500',
    speedFine: '₹1,000–₹2,000 (Sec 183 MV Act)',
  },
  TG: {
    name: 'Telangana',
    helmetFine: '₹500',
    speedFine: '₹1,000–₹2,000 (Sec 183 MV Act)',
  },
};

export interface GeoAlert {
  id: string;
  type: 'state_boundary' | 'speed_zone';
  message: string;
  fineDetail: string;
  persistent: boolean;
}

export interface UseGeoFineAlertResult {
  country: string | null;
  countryCode: string | null;
  state: string | null;
  stateCode: string | null;
  locationName: string | null;
  activeAlerts: GeoAlert[];
  isOffline: boolean;
  permissionDenied: boolean;
  speedZoneLimit: number | null;
  dismissAlert: (id: string) => void;
  setManualLocation: (countryName: string, stateName: string) => void;
}

interface CachedLocation {
  country: string;
  countryCode: string;
  state: string;
  stateCode: string;
  locationName: string;
}

function getSpeedLimitFromZone(zone: { zone_type: string; geometry_json: string }): number | null {
  try {
    const geojson = JSON.parse(zone.geometry_json);
    const prop = geojson?.properties?.speed_limit;
    if (prop) return Number(prop);
  } catch {}

  const type = zone.zone_type.toLowerCase();
  if (type.includes('school') || type.includes('hospital')) return 25;
  const match = type.match(/speed[_\s-]*(\d+)/);
  if (match) return Number(match[1]);
  if (type.includes('speed')) return 30;
  return null;
}

export function useGeoFineAlert(): UseGeoFineAlertResult {
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [country, setCountry] = useState<string | null>(null);
  const [countryCode, setCountryCode] = useState<string | null>(null);
  const [state, setState] = useState<string | null>(null);
  const [stateCode, setStateCode] = useState<string | null>(null);
  const [locationName, setLocationName] = useState<string | null>(null);
  const [activeAlerts, setActiveAlerts] = useState<GeoAlert[]>([]);
  const [isOffline, setIsOffline] = useState(false);
  const [permissionDenied, setPermissionDenied] = useState(false);
  const [speedZoneLimit, setSpeedZoneLimit] = useState<number | null>(null);

  const prevStateCodeRef = useRef<string | null>(null);
  const { getZonesForPoint, initialized } = useLocalDB();

  // Phase 1: load cached location immediately, then get fresh GPS fix
  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        const raw = await AsyncStorage.getItem(CACHE_KEY);
        if (raw && !cancelled) {
          const cached: CachedLocation = JSON.parse(raw);
          setCountry(cached.country);
          setCountryCode(cached.countryCode);
          setState(cached.state);
          setStateCode(cached.stateCode);
          setLocationName(cached.locationName);
          setIsOffline(true);
        }
      } catch {}

      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        if (!cancelled) setPermissionDenied(true);
        return;
      }

      try {
        const fix = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });
        if (!cancelled) {
          setCoords({ lat: fix.coords.latitude, lon: fix.coords.longitude });
        }
      } catch {
        // GPS failed — cached data stays active, isOffline remains true
      }
    };

    run();
    return () => { cancelled = true; };
  }, []);

  // Phase 2: reverse geocode on new coords
  useEffect(() => {
    if (!coords) return;
    let cancelled = false;

    const geocode = async () => {
      try {
        const results = await Location.reverseGeocodeAsync({
          latitude: coords.lat,
          longitude: coords.lon,
        });
        const geo = results[0];
        if (!geo || cancelled) return;

        const rc = geo.country ?? '';
        const rcc = geo.isoCountryCode ?? COUNTRY_ISO[rc] ?? '';
        const rs = geo.region ?? '';
        const rsc = STATE_CODE[rs] ?? '';
        const rln = [geo.city, geo.region].filter(Boolean).join(', ') || 'Unknown';

        const cached: CachedLocation = {
          country: rc,
          countryCode: rcc,
          state: rs,
          stateCode: rsc,
          locationName: rln,
        };
        await AsyncStorage.setItem(CACHE_KEY, JSON.stringify(cached));

        if (!cancelled) {
          setCountry(rc);
          setCountryCode(rcc);
          setState(rs);
          setStateCode(rsc);
          setLocationName(rln);
          setIsOffline(false);
        }
      } catch {
        if (!cancelled) setIsOffline(true);
      }
    };

    geocode();
    return () => { cancelled = true; };
  }, [coords]);

  // Phase 3: state boundary alert when stateCode changes
  useEffect(() => {
    if (!stateCode || stateCode === prevStateCodeRef.current) return;
    prevStateCodeRef.current = stateCode;

    const fineInfo = STATE_FINE_INFO[stateCode];
    if (!fineInfo) return;

    const alertId = `state_${stateCode}_${Date.now()}`;
    const alert: GeoAlert = {
      id: alertId,
      type: 'state_boundary',
      message: `📍 You're in ${fineInfo.name} — Local traffic laws apply.\nHelmet fine: ${fineInfo.helmetFine}`,
      fineDetail: fineInfo.helmetFine,
      persistent: false,
    };

    setActiveAlerts(prev => [...prev.filter(a => a.type !== 'state_boundary'), alert]);
    const timer = setTimeout(() => {
      setActiveAlerts(prev => prev.filter(a => a.id !== alertId));
    }, 5000);

    return () => clearTimeout(timer);
  }, [stateCode]);

  // Phase 4: zone speed limit detection
  useEffect(() => {
    if (!coords || !initialized) return;
    let cancelled = false;

    const detectZones = async () => {
      try {
        const zones = await getZonesForPoint(coords.lat, coords.lon);
        if (cancelled) return;

        let limit: number | null = null;
        for (const zone of zones) {
          const l = getSpeedLimitFromZone(zone);
          if (l !== null) { limit = l; break; }
        }
        setSpeedZoneLimit(limit);
      } catch {}
    };

    detectZones();
    return () => { cancelled = true; };
  }, [coords, initialized, getZonesForPoint]);

  const dismissAlert = useCallback((id: string) => {
    setActiveAlerts(prev => prev.filter(a => a.id !== id));
  }, []);

  const setManualLocation = useCallback((countryName: string, stateName: string) => {
    const cc = COUNTRY_ISO[countryName] ?? '';
    const sc = STATE_CODE[stateName] ?? '';
    setCountry(countryName);
    setCountryCode(cc);
    setState(stateName);
    setStateCode(sc);
    setLocationName(`${stateName}, ${countryName}`);
    setIsOffline(true);
    setPermissionDenied(false);
  }, []);

  return {
    country,
    countryCode,
    state,
    stateCode,
    locationName,
    activeAlerts,
    isOffline,
    permissionDenied,
    speedZoneLimit,
    dismissAlert,
    setManualLocation,
  };
}
