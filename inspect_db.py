import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect('backend/data/fines.db')
cursor = conn.cursor()

# AE rows in detail
cursor.execute("SELECT offence_code, state, amount_inr, repeat_amount_inr, section_ref, currency FROM fines WHERE country='AE' LIMIT 30")
print('=== AE rows ===')
for r in cursor.fetchall(): print(r)

# GB rows
cursor.execute("SELECT offence_code, state, amount_inr, repeat_amount_inr, section_ref, currency FROM fines WHERE country='GB' LIMIT 20")
print('\n=== GB rows ===')
for r in cursor.fetchall(): print(r)

# SG rows
cursor.execute("SELECT offence_code, state, amount_inr, repeat_amount_inr, section_ref, currency FROM fines WHERE country='SG' LIMIT 20")
print('\n=== SG rows ===')
for r in cursor.fetchall(): print(r)

# US rows
cursor.execute("SELECT offence_code, state, amount_inr, repeat_amount_inr, section_ref, currency FROM fines WHERE country='US' LIMIT 20")
print('\n=== US rows ===')
for r in cursor.fetchall(): print(r)

# WB drunk_driving
cursor.execute("SELECT offence_code, state, amount_inr, repeat_amount_inr FROM fines WHERE state='WB' AND offence_code='DRUNK_DRIVING'")
print('\n=== WB DRUNK_DRIVING ===', cursor.fetchall())

# Missing codes check
for code in ['NO_PUC','TRIPLE_RIDING','NO_NUMBER_PLATE','SECTION_194C','PUC_VIOLATION','JUVENILE_DRIVING']:
    cursor.execute("SELECT COUNT(*) FROM fines WHERE offence_code=?", (code,))
    cnt = cursor.fetchone()[0]
    print(f'{code}: {cnt} rows')

conn.close()
