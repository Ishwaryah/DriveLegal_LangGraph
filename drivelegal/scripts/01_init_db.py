import psycopg2
import os

# Absolute path fix (IMPORTANT)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
schema_path = os.path.join(BASE_DIR, "db", "schema.sql")

# STEP 1 — connect to default DB
conn = psycopg2.connect(
    host="localhost",
    database="postgres",
    user="postgres",
    password="postgres",
    port="5432"
)
conn.autocommit = True
cursor = conn.cursor()

# STEP 2 — create DB
try:
    cursor.execute("CREATE DATABASE drivelegal;")
    print("✅ Database created")
except:
    print("⚠️ Database exists")

cursor.close()
conn.close()

# STEP 3 — connect to drivelegal
conn = psycopg2.connect(
    host="localhost",
    database="drivelegal",
    user="postgres",
    password="postgres",
    port="5432"
)
conn.autocommit = True
cursor = conn.cursor()

# STEP 4 — read schema
print("📂 Reading schema from:", schema_path)

with open(schema_path, "r") as f:
    sql = f.read()

# DEBUG: print SQL
print("📜 Running SQL:\n", sql)

# STEP 5 — execute
cursor.execute(sql)

print("✅ Table created successfully")

cursor.close()
conn.close()