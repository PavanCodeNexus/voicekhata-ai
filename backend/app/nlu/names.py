import sqlite3
import re
from typing import List, Dict, Any, Optional

KNOWN_NAME_STOPWORDS = {
    "aaj", "kal", "parso", "sab", "ek", "do", "teen", "chaar", "paanch",
    "udhaar", "udri", "jama", "kadan", "appu", "saala", "baredko", "likh", "likhna", "diya", "de", "diye",
    "total", "kitna", "eshtu", "evlo", "entha", "the", "a", "an", "is", "of", "rupaye", "rupees", "rupaayi",
    "nahi", "alla", "galat", "wrong", "change", "cancel", "thappu", "bhai", "ji"
}

def extract_candidate_name_from_text(text: str) -> Optional[str]:
    """
    Extracts customer name from clause like:
    'Ramesh ka 340 udhaar' -> 'Ramesh'
    'Anand avrige mooru nooru' -> 'Anand'
    'Suresh ne kal 200 diya' -> 'Suresh'
    """
    clean = text.strip()
    
    # 1. Look for patterns like Name + (ka/ki/ke/ne/ko/ku/ge/avrige/oda)
    match = re.search(r'\b([A-Za-z]+)\s+(?:ka|ki|ke|ne|ko|ku|ge|avrige|oda)\b', clean, re.IGNORECASE)
    if match:
        name = match.group(1).title()
        if name.lower() not in KNOWN_NAME_STOPWORDS:
            return name
            
    # 2. Look for first non-stopword capitalized word
    words = clean.split()
    for w in words:
        clean_w = re.sub(r'[^A-Za-z]', '', w)
        if clean_w and clean_w.lower() not in KNOWN_NAME_STOPWORDS:
            return clean_w.title()
            
    return None

def match_customers_in_db(name_or_alias: str, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Searches customers by exact match, partial match on name or alias.
    """
    if not name_or_alias:
        return []
        
    query = name_or_alias.strip().lower()
    cursor = conn.cursor()
    
    # Exact match on name
    cursor.execute("SELECT * FROM customers WHERE LOWER(name) = ? AND is_active = 1", (query,))
    exact = [dict(r) for r in cursor.fetchall()]
    if exact:
        return exact
        
    # Partial match on name or alias
    cursor.execute("""
    SELECT * FROM customers 
    WHERE (LOWER(name) LIKE ? OR LOWER(alias) LIKE ?) AND is_active = 1
    """, (f"%{query}%", f"%{query}%"))
    
    return [dict(r) for r in cursor.fetchall()]
