import sqlite3
import os

db_path = "backend/data/fines.db"
if not os.path.exists(db_path):
    print("DB not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT violation_name, country FROM fines WHERE violation_name LIKE '%RED SIGNAL%'")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    conn.close()
