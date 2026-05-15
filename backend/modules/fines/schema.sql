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

CREATE TABLE IF NOT EXISTS sync_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
  source_url TEXT NOT NULL,
  status TEXT NOT NULL,
  message TEXT,
  rows_inserted INTEGER DEFAULT 0,
  rows_updated INTEGER DEFAULT 0
);
