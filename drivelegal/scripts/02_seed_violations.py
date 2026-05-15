import psycopg2
import pandas as pd

# ---------- DB CONNECTION ----------
conn = psycopg2.connect(
    dbname="drivelegal",
    user="postgres",
    password="postgres",   # ← change if needed
    host="localhost",
    port="5432"
)

cur = conn.cursor()

# ---------- LOAD CSV ----------
df = pd.read_csv("data/processed/violations.csv")

print(f"📄 Loaded {len(df)} rows from CSV")

# ---------- INSERT DATA ----------
for _, row in df.iterrows():

    # 1️⃣ Insert into violations table
    cur.execute("""
        INSERT INTO violations
        (violation_code, section_id, description, vehicle_type, severity)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (
        row["violation_code"],
        row["section_id"],
        row["description"],
        row["vehicle_type"],
        row["severity"]
    ))

    # 2️⃣ Insert into state table (optional but good design)
    cur.execute("""
        INSERT INTO state
        (state_code, state_name, country)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (
        row["state_code"],
        row["state_code"],   # using code as name (can improve later)
        "India"
    ))

    # 3️⃣ Insert into state_fine table
    cur.execute("""
        INSERT INTO state_fine
        (state_code, violation_code, vehicle_type, fine, points)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (
        row["state_code"],
        row["violation_code"],
        row["vehicle_type"],
        int(row["fine"]),
        int(row["points"])
    ))

# ---------- COMMIT ----------
conn.commit()

# ---------- CLOSE ----------
cur.close()
conn.close()

print("✅ Data inserted successfully into all tables")