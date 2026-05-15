CREATE TABLE IF NOT EXISTS fines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  country TEXT NOT NULL DEFAULT 'IN',
  state_province TEXT,
  violation_code TEXT NOT NULL,
  violation_name TEXT NOT NULL,
  vehicle_type TEXT NOT NULL DEFAULT 'all',
  min_fine_local INTEGER,
  max_fine_local INTEGER,
  currency TEXT NOT NULL DEFAULT 'INR',
  mv_act_section TEXT,
  compounding_eligible BOOLEAN DEFAULT 0,
  compounding_fee INTEGER,
  imprisonment_days INTEGER DEFAULT 0,
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_geo_lookup 
  ON fines(country, state_province, violation_code, vehicle_type);

CREATE INDEX IF NOT EXISTS idx_country_violation 
  ON fines(country, violation_code);

CREATE TABLE IF NOT EXISTS rules (
  rule_id TEXT PRIMARY KEY,
  section TEXT,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'ALL',
  raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS zones (
  zone_id TEXT PRIMARY KEY,
  zone_type TEXT NOT NULL,
  state TEXT NOT NULL,
  rule_set_id TEXT,
  geometry_json TEXT NOT NULL,
  fine_multiplier REAL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS sync_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  synced_at TEXT NOT NULL,
  module TEXT NOT NULL,
  rows_updated INTEGER DEFAULT 0,
  status TEXT NOT NULL,
  error TEXT
);
