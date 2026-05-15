import pytest
import sqlite3
import os
import tempfile
from datetime import datetime
from ..lookup import FineLookup

@pytest.fixture
def mock_db():
    # Use a temporary file for the database
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        db_path = tmp.name
    
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE fines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offence_code TEXT NOT NULL,
            vehicle_class TEXT NOT NULL,
            state TEXT NOT NULL,
            amount_inr INTEGER NOT NULL,
            repeat_amount_inr INTEGER,
            section_ref TEXT,
            source_url TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            version_hash TEXT NOT NULL UNIQUE
        )
    """)
    
    # Seed 3 test rows
    fetched_at = datetime.now().isoformat()
    test_data = [
        ("NO_LICENSE", "LMV", "ALL", 5000, 5000, "Sec 181", "http://test.com", "hash1"),
        ("OVERSPEED", "LMV", "TN", 1000, 2000, "Sec 183", "http://test.com", "hash2"),
        ("HELMET", "TWO_WHEELER", "TN", 1000, 1000, "Sec 194D", "http://test.com", "hash3")
    ]
    
    for row in test_data:
        # row matches (offence_code, vehicle_class, state, amount_inr, repeat_amount_inr, section_ref, source_url, version_hash)
        # Table columns: offence_code, vehicle_class, state, amount_inr, repeat_amount_inr, section_ref, source_url, fetched_at, version_hash
        conn.execute("""
            INSERT INTO fines (offence_code, vehicle_class, state, amount_inr, repeat_amount_inr, section_ref, source_url, version_hash, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (*row, fetched_at))
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)

def test_exact_match(mock_db):
    lookup = FineLookup(mock_db)
    result = lookup.query("NO_LICENSE", "LMV", "TN") # Should match ALL
    assert result is not None
    assert result['amount_inr'] == 5000
    
    result = lookup.query("OVERSPEED", "LMV", "TN") # Should match TN
    assert result is not None
    assert result['amount_inr'] == 1000

def test_no_match_returns_none(mock_db):
    lookup = FineLookup(mock_db)
    result = lookup.query("UNKNOWN_OFFENCE", "LMV", "TN")
    assert result is None

def test_repeat_offence(mock_db):
    lookup = FineLookup(mock_db)
    # First offence
    result = lookup.query("OVERSPEED", "LMV", "TN", repeat=False)
    assert result['amount_inr'] == 1000
    
    # Repeat offence
    result = lookup.query("OVERSPEED", "LMV", "TN", repeat=True)
    assert result['amount_inr'] == 2000

def test_db_age(mock_db):
    lookup = FineLookup(mock_db)
    age = lookup.get_db_age()
    assert "updated" in age.lower()
