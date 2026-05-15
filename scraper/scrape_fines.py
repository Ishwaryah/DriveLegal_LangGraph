import asyncio
import json
import hashlib
import sqlite3
import os
from datetime import datetime
from playwright.async_api import async_playwright

DB_PATH = os.path.join(os.path.dirname(__file__), "../backend/data/fines.db")
SOURCES_PATH = os.path.join(os.path.dirname(__file__), "sources.json")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "../backend/modules/fines/schema.sql")

def generate_version_hash(offence_code, vehicle_class, state, amount_inr):
    payload = f"{offence_code}{vehicle_class}{state}{amount_inr}"
    return hashlib.sha256(payload.encode()).hexdigest()

async def log_sync(source_url, status, message, inserted=0, updated=0):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO sync_log (source_url, status, message, rows_inserted, rows_updated)
        VALUES (?, ?, ?, ?, ?)
    """, (source_url, status, message, inserted, updated))
    conn.commit()
    conn.close()

async def scrape_source(browser, source):
    print(f"Scraping {source['name']} ({source['url']})...")
    page = await browser.new_page()
    try:
        await page.goto(source['url'], timeout=60000)
        # In a real scenario, we'd wait for specific selectors.
        # Here we extract all tables and try to parse them.
        tables = await page.query_selector_all("table")
        
        extracted_data = []
        for table in tables:
            rows = await table.query_selector_all("tr")
            if not rows: continue
            
            headers = [await (await col.get_property("innerText")).json_value() for col in await rows[0].query_selector_all("th, td")]
            headers = [h.strip().lower() for h in headers]
            
            # Simple heuristic mapping
            mapping = {}
            for i, h in enumerate(headers):
                if "offence" in h or "violation" in h or "nature" in h: mapping['offence_code'] = i
                if "class" in h or "vehicle" in h: mapping['vehicle_class'] = i
                if "amount" in h or "fine" in h or "penalty" in h or "rupees" in h: mapping['amount_inr'] = i
                if "section" in h or "ref" in h: mapping['section_ref'] = i

            if 'offence_code' in mapping and 'amount_inr' in mapping:
                for row in rows[1:]:
                    cols = await row.query_selector_all("td")
                    if not cols or len(cols) <= max(mapping.values()): continue
                    
                    try:
                        offence = (await (await cols[mapping['offence_code']].get_property("innerText")).json_value()).strip()
                        amount_str = (await (await cols[mapping['amount_inr']].get_property("innerText")).json_value()).strip()
                        # Extract first number from amount string
                        amount = int(''.join(filter(str.isdigit, amount_str.split('.')[0])))
                        
                        v_class = "ALL"
                        if 'vehicle_class' in mapping:
                            v_class = (await (await cols[mapping['vehicle_class']].get_property("innerText")).json_value()).strip()
                        
                        section = ""
                        if 'section_ref' in mapping:
                            section = (await (await cols[mapping['section_ref']].get_property("innerText")).json_value()).strip()

                        extracted_data.append({
                            'offence_code': offence[:100], # Trucate if too long
                            'vehicle_class': v_class[:50],
                            'state': source['state'],
                            'amount_inr': amount,
                            'section_ref': section,
                            'source_url': source['url']
                        })
                    except Exception as e:
                        continue # Skip malformed rows

        if not extracted_data:
            await log_sync(source['url'], "WARNING", "No data extracted from tables")
            return 0, 0

        # Save to DB
        conn = sqlite3.connect(DB_PATH)
        inserted, updated = 0, 0
        fetched_at = datetime.now().isoformat()
        
        for item in extracted_data:
            v_hash = generate_version_hash(item['offence_code'], item['vehicle_class'], item['state'], item['amount_inr'])
            
            # Check if exists
            cursor = conn.execute("SELECT id FROM fines WHERE version_hash = ?", (v_hash,))
            existing = cursor.fetchone()
            
            if not existing:
                # Check if same offence/class/state exists with different amount or other details
                cursor = conn.execute(
                    "SELECT id FROM fines WHERE offence_code = ? AND vehicle_class = ? AND state = ?",
                    (item['offence_code'], item['vehicle_class'], item['state'])
                )
                same_key = cursor.fetchone()
                
                if same_key:
                    conn.execute("""
                        UPDATE fines SET 
                            amount_inr = ?, section_ref = ?, source_url = ?, fetched_at = ?, version_hash = ?
                        WHERE id = ?
                    """, (item['amount_inr'], item['section_ref'], item['source_url'], fetched_at, v_hash, same_key[0]))
                    updated += 1
                else:
                    conn.execute("""
                        INSERT INTO fines (offence_code, vehicle_class, state, amount_inr, section_ref, source_url, fetched_at, version_hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (item['offence_code'], item['vehicle_class'], item['state'], item['amount_inr'], item['section_ref'], item['source_url'], fetched_at, v_hash))
                    inserted += 1

        conn.commit()
        conn.close()
        await log_sync(source['url'], "SUCCESS", f"Processed {len(extracted_data)} rows", inserted, updated)
        return inserted, updated

    except Exception as e:
        print(f"Error scraping {source['name']}: {e}")
        await log_sync(source['url'], "ERROR", str(e))
        return 0, 0
    finally:
        await page.close()

async def main():
    if not os.path.exists(SOURCES_PATH):
        print("sources.json not found")
        return

    # Initialize DB
    conn = sqlite3.connect(DB_PATH)
    if os.path.exists(SCHEMA_PATH):
        with open(SCHEMA_PATH, 'r') as f:
            conn.executescript(f.read())
    conn.close()

    with open(SOURCES_PATH, 'r') as f:
        data = json.load(f)
        sources = [s for s in data['sources'] if s.get('enabled')]

    if not sources:
        print("No enabled sources to scrape")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        tasks = [scrape_source(browser, s) for s in sources]
        results = await asyncio.gather(*tasks)
        await browser.close()
        
        total_inserted = sum(r[0] for r in results)
        total_updated = sum(r[1] for r in results)
        print(f"Scrape completed. Total inserted: {total_inserted}, Total updated: {total_updated}")

if __name__ == "__main__":
    asyncio.run(main())
