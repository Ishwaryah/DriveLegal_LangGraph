import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/fines.db")

def migrate():
    print(f"Connecting to database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Dropping old 'fines' table if exists...")
    cursor.execute("DROP TABLE IF EXISTS fines")

    print("Creating new 'fines' table...")
    cursor.execute("""
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
    """)

    print("Creating indexes...")
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_geo_lookup 
      ON fines(country, state_province, violation_code, vehicle_type);
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_country_violation 
      ON fines(country, violation_code);
    """)

    # --- Seeding Data ---
    
    def insert_fine(country, state, code, name, v_type, min_f, max_f, curr, section, comp_elig=0, comp_fee=None, jail=0, notes=None):
        cursor.execute("""
            INSERT INTO fines (
                country, state_province, violation_code, violation_name, vehicle_type,
                min_fine_local, max_fine_local, currency, mv_act_section,
                compounding_eligible, compounding_fee, imprisonment_days, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (country, state, code, name, v_type, min_f, max_f, curr, section, comp_elig, comp_fee, jail, notes))

    # --- INDIA (MV Act 2019) ---
    # National-level violations (apply to all vehicle types unless overridden)
    india_violations = [
        ("drunk_driving",            "Drunk Driving",                        "Sec 185",   10000, 15000, 180,  "LMV first ₹10,000 / repeat ₹15,000 + 6mo jail; non-compoundable"),
        ("overspeeding",             "Overspeeding",                         "Sec 183",   1000,  2000,  0,    "LMV ₹1,000–₹2,000 / HMV ₹2,000–₹4,000"),
        ("no_helmet",                "No Helmet",                            "Sec 194D",  1000,  1000,  0,    "₹1,000 + 3-month licence disqualification"),
        ("no_seatbelt",              "No Seatbelt",                          "Sec 194B",  1000,  1000,  0,    "₹1,000 for driver and all passengers"),
        ("using_phone",              "Using Phone while Driving",            "Sec 194F",  1500,  5000,  0,    "₹1,500 first / ₹5,000 repeat + licence suspension"),
        ("no_insurance",             "Driving without Insurance",            "Sec 196",   2000,  4000,  90,   "₹2,000 first / ₹4,000 repeat + 3mo jail"),
        ("no_rc",                    "Driving without Registration",         "Sec 192",   2000,  5000,  180,  "₹2,000–₹5,000 + up to 6mo jail"),
        ("signal_jumping",           "Signal Jumping / Red Light",           "Sec 184",   1000,  5000,  180,  "₹1,000–₹5,000 + up to 6mo jail; non-compoundable"),
        ("dangerous_driving",        "Dangerous Driving",                    "Sec 184",   1000,  5000,  180,  "₹1,000–₹5,000 + up to 6mo jail; non-compoundable"),
        ("overloading",              "Overloading",                          "Sec 194",   20000, 20000, 0,    "₹20,000 base + ₹2,000 per extra tonne"),
        ("no_license",               "Driving without License",              "Sec 181",   5000,  5000,  0,    "₹5,000"),
        ("juvenile_driving",         "Juvenile / Underage Driving",          "Sec 199A",  25000, 25000, 1095, "Guardian liable: ₹25,000 + 3yr jail; RC cancelled"),
        ("wrong_side",               "Driving on Wrong Side",                "Sec 184",   1100,  5000,  0,    "₹1,100–₹5,000"),
        ("not_giving_way_to_emergency", "Not Giving Way to Emergency Vehicles", "Sec 194E", 10000, 10000, 180, "₹10,000 + up to 6mo jail"),
        ("puc_violation",            "Driving without Valid PUC Certificate","Sec 190",   10000, 10000, 180,  "₹10,000 + up to 6mo jail for first offence"),
        ("stunt_driving",            "Stunt Driving / Street Racing",        "Sec 189",   5000,  10000, 90,   "₹5,000 first / ₹10,000 repeat + up to 1yr jail"),
        ("tinted_glass",             "Illegal Window Tint / Dark Glass",     "Sec 177",   1000,  5000,  0,    "₹1,000–₹5,000; vehicle may be impounded"),
        ("disobeying_police",        "Disobeying Traffic Police Orders",     "Sec 179",   2000,  2000,  0,    "₹2,000 fine"),
        ("triple_riding",            "Triple Riding on Two-Wheeler",         "Sec 194C",  1000,  1000,  0,    "₹1,000"),
        ("vehicle_modification",     "Illegal Vehicle Modification",         "Sec 52",    5000,  5000,  0,    "₹5,000 + vehicle seizure"),
        ("parking_violation",        "Illegal Parking",                      "Sec 122",   500,   2000,  0,    "₹500–₹2,000 + towing charges"),
        ("wrong_overtaking",         "Wrong / Unsafe Overtaking",            "Sec 184",   1000,  5000,  0,    "₹1,000–₹5,000 under dangerous driving"),
        ("road_rage",                "Road Rage / Aggressive Driving",       "Sec 184",   1000,  5000,  180,  "₹1,000–₹5,000 + IPC charges if assault"),
        ("suspended_licence",        "Driving with Suspended/Cancelled DL",  "Sec 182",   10000, 10000, 90,   "₹10,000 + up to 3mo jail"),
    ]

    india_vehicle_types = ['two_wheeler', 'three_wheeler', 'lmv', 'hmv', 'commercial']

    # National rows (state_province = NULL)
    for code, name, section, min_f, max_f, jail, notes in india_violations:
        for v_type in india_vehicle_types:
            actual_min = min_f
            actual_max = max_f
            # HGV/commercial typically have higher fines for overloading and overspeeding
            if code == "overspeeding" and v_type in ['hmv', 'commercial']:
                actual_min, actual_max = 2000, 4000
            # PUC violation applies equally to all vehicle types
            insert_fine('IN', None, code, name, v_type, actual_min, actual_max, 'INR', section, 0, None, jail, notes)

    # --- State-specific overrides ---
    # Format: (state, code, name, section, min_f, max_f, v_type, comp_elig, comp_fee, jail, notes)
    state_overrides = [
        # DELHI — higher fixed fines under Delhi Motor Vehicles Rules
        ("Delhi", "signal_jumping",  "Signal Jumping",          "Sec 184",  5000, 5000, "all", 0, None, 0, "Delhi: ₹5,000 fixed fine"),
        ("Delhi", "using_phone",     "Mobile Phone while Driving","Sec 194F",5000, 5000, "all", 0, None, 0, "Delhi: ₹5,000 fixed fine"),
        ("Delhi", "wrong_side",      "Wrong Side Driving",      "Sec 184",  5000, 5000, "all", 0, None, 0, "Delhi: ₹5,000 fixed fine"),
        ("Delhi", "no_license",      "No Driving Licence",      "Sec 181",  5000, 5000, "all", 0, None, 0, "Delhi: ₹5,000"),
        ("Delhi", "no_rc",           "No Registration Certificate","Sec 192",5000, 5000, "all", 0, None, 0, "Delhi: ₹5,000"),
        ("Delhi", "no_helmet",       "No Helmet",               "Sec 194D", 1000, 1000, "two_wheeler", 1, 1000, 0, "Delhi: ₹1,000"),
        ("Delhi", "no_seatbelt",     "No Seatbelt",             "Sec 194B", 1000, 1000, "all", 1, 1000, 0, "Delhi: ₹1,000"),
        ("Delhi", "no_insurance",    "No Insurance",            "Sec 196",  2000, 4000, "all", 0, None, 0, "Delhi: ₹2,000"),
        ("Delhi", "overspeeding",    "Overspeeding",            "Sec 183",  2000, 4000, "lmv", 1, 2000, 0, "Delhi LMV: ₹2,000"),
        ("Delhi", "overspeeding",    "Overspeeding HGV",        "Sec 183",  4000, 4000, "hmv", 1, 4000, 0, "Delhi HGV: ₹4,000"),
        # MAHARASHTRA — reduced some fines after public protests
        ("Maharashtra", "no_helmet", "No Helmet",               "Sec 194D", 500,  500,  "two_wheeler", 1, 500, 0, "Maharashtra: reduced to ₹500"),
        ("Maharashtra", "no_seatbelt","No Seatbelt",            "Sec 194B", 500,  500,  "all", 1, 500,  0, "Maharashtra: reduced to ₹500"),
        ("Maharashtra", "no_license","No DL",                   "Sec 181",  1000, 1000, "all", 1, 1000, 0, "Maharashtra: ₹1,000"),
        ("Maharashtra", "no_rc",     "No RC",                   "Sec 192",  2000, 2000, "all", 1, 2000, 0, "Maharashtra: ₹2,000"),
        ("Maharashtra", "signal_jumping","Signal Jumping",      "Sec 184",  1000, 5000, "all", 0, None, 0, "Maharashtra: ₹1,000–₹5,000"),
        ("Maharashtra", "using_phone","Mobile Phone",           "Sec 194F", 1000, 1000, "all", 1, 1000, 0, "Maharashtra: ₹1,000"),
        ("Maharashtra", "no_insurance","No Insurance",          "Sec 196",  2000, 4000, "all", 0, None, 0, "Maharashtra: ₹2,000"),
        # TAMIL NADU
        ("Tamil Nadu", "no_license", "No DL",                   "Sec 181",  5000, 5000, "all", 0, None, 0, "Tamil Nadu: ₹5,000"),
        ("Tamil Nadu", "no_rc",      "No RC",                   "Sec 192",  5000, 5000, "all", 0, None, 0, "Tamil Nadu: ₹5,000"),
        ("Tamil Nadu", "no_helmet",  "No Helmet",               "Sec 194D", 1000, 1000, "two_wheeler", 1, 1000, 0, "Tamil Nadu: ₹1,000"),
        ("Tamil Nadu", "no_seatbelt","No Seatbelt",             "Sec 194B", 1000, 1000, "all", 1, 1000, 0, "Tamil Nadu: ₹1,000"),
        ("Tamil Nadu", "no_insurance","No Insurance",           "Sec 196",  2000, 4000, "all", 0, None, 0, "Tamil Nadu: ₹2,000"),
        ("Tamil Nadu", "overspeeding","Overspeeding LMV",       "Sec 183",  1000, 2000, "lmv", 1, 1000, 0, "Tamil Nadu: ₹1,000"),
        # KARNATAKA
        ("Karnataka", "no_license",  "No DL",                   "Sec 181",  5000, 5000, "all", 0, None, 0, "Karnataka: ₹5,000"),
        ("Karnataka", "no_rc",       "No RC",                   "Sec 192",  5000, 5000, "all", 0, None, 0, "Karnataka: ₹5,000"),
        ("Karnataka", "signal_jumping","Signal Jumping",        "Sec 184",  1000, 5000, "all", 0, None, 0, "Karnataka: ₹1,000"),
        ("Karnataka", "using_phone", "Mobile Phone",            "Sec 194F", 1000, 1000, "all", 1, 1000, 0, "Karnataka: ₹1,000"),
        ("Karnataka", "no_insurance","No Insurance",            "Sec 196",  2000, 4000, "all", 0, None, 0, "Karnataka: ₹2,000"),
        ("Karnataka", "no_helmet",   "No Helmet",               "Sec 194D", 1000, 1000, "two_wheeler", 1, 1000, 0, "Karnataka: ₹1,000"),
        # KERALA
        ("Kerala", "no_helmet",      "No Helmet",               "Sec 194D", 1000, 1000, "two_wheeler", 1, 1000, 0, "Kerala: ₹1,000"),
        ("Kerala", "no_seatbelt",    "No Seatbelt",             "Sec 194B", 1000, 1000, "all", 1, 1000, 0, "Kerala: ₹1,000"),
        ("Kerala", "signal_jumping", "Signal Jumping",          "Sec 184",  1000, 5000, "all", 0, None, 0, "Kerala: ₹1,000"),
        ("Kerala", "no_insurance",   "No Insurance",            "Sec 196",  2000, 4000, "all", 0, None, 0, "Kerala: ₹2,000"),
    ]

    for state, code, name, section, min_f, max_f, v_type, comp_elig, comp_fee, jail, notes in state_overrides:
        insert_fine('IN', state, code, name, v_type, min_f, max_f, 'INR', section, comp_elig, comp_fee, jail, notes)

    # --- UAE ---
    uae_violations = [
        ("drunk_driving", "Drunk Driving", "Federal Traffic Law No. 21 of 1995", 20000, 20000, 30, "AED 20,000 + jail + deportation risk"),
        ("overspeeding_20", "Overspeeding (>20 km/h)", "Federal Traffic Law No. 21 of 1995", 300, 300, 0, "4 black points"),
        ("overspeeding_40", "Overspeeding (>40 km/h)", "Federal Traffic Law No. 21 of 1995", 600, 600, 0, "6 black points"),
        ("overspeeding_60", "Overspeeding (>60 km/h)", "Federal Traffic Law No. 21 of 1995", 1000, 1000, 0, "8 black points + license confiscation 60 days"),
        ("no_seatbelt", "No Seatbelt", "Federal Traffic Law No. 21 of 1995", 400, 400, 0, "4 black points"),
        ("using_phone", "Using Phone while Driving", "Federal Traffic Law No. 21 of 1995", 800, 800, 0, "4 black points"),
        ("signal_jumping", "Signal Jumping", "Federal Traffic Law No. 21 of 1995", 1000, 1000, 0, "12 black points"),
        ("no_insurance", "Driving without Insurance", "Federal Traffic Law No. 21 of 1995", 500, 500, 0, "AED 500"),
        ("reckless_driving", "Reckless Driving", "Federal Traffic Law No. 21 of 1995", 2000, 2000, 7, "AED 2000 + jail + 23 black points"),
        ("no_license", "Driving without License", "Federal Traffic Law No. 21 of 1995", 500, 500, 0, "AED 500")
    ]
    for code, name, section, min_f, max_f, jail, notes in uae_violations:
        insert_fine('AE', None, code, name, 'all', min_f, max_f, 'AED', section, 0, None, jail, notes)

    # --- SINGAPORE ---
    sg_violations = [
        ("drunk_driving", "Drunk Driving", "Road Traffic Act Cap 276", 1000, 5000, 30, "SGD 1,000-5,000 first / up to 10,000 repeat + jail"),
        ("overspeeding", "Overspeeding", "Traffic Police Speed Bands", 130, 1000, 0, "SGD 130-1,000 based on band"),
        ("no_seatbelt", "No Seatbelt", "Road Traffic Act Cap 276", 120, 120, 0, "SGD 120"),
        ("using_phone", "Using Phone while Driving", "Road Traffic Act Cap 276", 200, 1000, 0, "SGD 200-1,000"),
        ("signal_jumping", "Signal Jumping", "Road Traffic Act Cap 276", 200, 200, 0, "SGD 200"),
        ("reckless_driving", "Reckless Driving", "Road Traffic Act Cap 276", 3000, 3000, 365, "SGD 3,000 + jail 12mo first"),
        ("no_insurance", "Driving without Insurance", "Road Traffic Act Cap 276", 600, 1200, 0, "SGD 600-1,200"),
        ("no_license", "Driving without License", "Road Traffic Act Cap 276", 400, 800, 0, "SGD 400-800"),
        ("drink_drug_driving", "Drink/Drug Driving", "Road Traffic Act Cap 276", 5000, 5000, 365, "SGD 5,000 + 12mo jail first offense"),
        ("dangerous_driving", "Dangerous Driving", "Road Traffic Act Cap 276", 5000, 10000, 730, "SGD 5,000-10,000 + up to 2yr jail"),
    ]
    for code, name, section, min_f, max_f, jail, notes in sg_violations:
        insert_fine('SG', None, code, name, 'all', min_f, max_f, 'SGD', section, 0, None, jail, notes)

    # --- UK ---
    uk_violations = [
        ("drunk_driving", "Drunk Driving", "Road Traffic Act 1988", 5000, 5000, 180, "unlimited fine + 6mo jail + min 12mo ban"),
        ("overspeeding_minor", "Overspeeding (Minor)", "Road Traffic Offenders Act 1988", 100, 2500, 0, "3 points, SP30"),
        ("overspeeding_serious", "Overspeeding (Serious)", "Road Traffic Offenders Act 1988", 2500, 5000, 0, "up to unlimited, 6 points, SP50, court referral"),
        ("no_seatbelt", "No Seatbelt", "Road Traffic Act 1988", 100, 100, 0, "GBP 100"),
        ("using_phone", "Using Phone while Driving", "Road Traffic Act 1988", 200, 200, 0, "6 points"),
        ("no_insurance", "Driving without Insurance", "Road Traffic Offenders Act 1988", 300, 300, 0, "300 fixed + 6-8 points, IN10"),
        ("reckless_driving", "Reckless Driving", "Road Traffic Act 1988", 5000, 5000, 730, "unlimited + 2yr jail, DD40"),
        ("no_license", "Driving without License", "Road Traffic Act 1988", 1000, 1000, 0, "GBP 1,000"),
        ("no_mot", "Driving without Valid MOT", "Road Traffic Act 1988", 1000, 1000, 0, "GBP 1,000 fixed penalty"),
        ("dangerous_driving", "Dangerous Driving", "Road Traffic Act 1988", 5000, 5000, 730, "unlimited fine + 2yr jail, DD40/DD60"),
    ]
    for code, name, section, min_f, max_f, jail, notes in uk_violations:
        insert_fine('GB', None, code, name, 'all', min_f, max_f, 'GBP', section, 0, None, jail, notes)

    conn.commit()
    
    print("\nMigration Complete. Row counts per country:")
    cursor.execute("SELECT country, COUNT(*) FROM fines GROUP BY country")
    for country, count in cursor.fetchall():
        print(f"  {country}: {count} rows")
    
    conn.close()

if __name__ == "__main__":
    migrate()
