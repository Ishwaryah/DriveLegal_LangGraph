import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/fines.db"))

def migrate():
    logger.info("Connecting to database at %s", DB_PATH)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    logger.info("Creating 'vehicle_cache' table if it does not exist...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicle_cache (
        reg_no TEXT PRIMARY KEY,
        rc_data TEXT,        -- JSON string
        last_fetched TEXT,   -- ISO datetime
        source TEXT          -- 'live' or 'offline'
    );
    """)

    conn.commit()
    logger.info("Migration successful! 'vehicle_cache' table created/verified.")
    conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate()
