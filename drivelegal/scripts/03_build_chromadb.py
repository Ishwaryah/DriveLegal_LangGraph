import psycopg2
from chromadb import Client

# ---------- CONNECT TO DB ----------
conn = psycopg2.connect(
    dbname="drivelegal",
    user="postgres",
    password="postgres",   # change if needed
    host="localhost",
    port="5432"
)

cur = conn.cursor()

# ---------- FETCH DATA ----------
cur.execute("""
    SELECT violation_code, section_id, description, vehicle_type, severity
    FROM violations
""")

rows = cur.fetchall()

print(f"📊 Loaded {len(rows)} records from DB")

# ---------- INIT CHROMADB ----------
client = Client()
collection = client.get_or_create_collection(name="laws")

# ---------- PREPARE DOCUMENTS ----------
documents = []
ids = []

for i, row in enumerate(rows):
    violation_code, section_id, description, vehicle_type, severity = row

    text = f"""
    Violation: {violation_code}
    Section: {section_id}
    Description: {description}
    Vehicle: {vehicle_type}
    Severity: {severity}
    """

    documents.append(text.strip())
    ids.append(str(i))

# ---------- ADD TO CHROMADB ----------
collection.add(
    documents=documents,
    ids=ids
)

print("✅ ChromaDB built successfully")

# ---------- CLEANUP ----------
cur.close()
conn.close()