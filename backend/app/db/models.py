import sqlite3
import datetime
from typing import List, Dict, Any, Optional

def init_db(conn: sqlite3.Connection):
    cursor = conn.cursor()
    
    # 1. Customers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        alias TEXT,
        phonetic_key TEXT,
        phone TEXT,
        language TEXT DEFAULT 'kn-IN',
        whatsapp_opt_in INTEGER DEFAULT 1,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. Append-Only Transactions Table (Money in integer paise)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        customer_name TEXT,
        kind TEXT NOT NULL CHECK (kind IN ('credit_sale','payment_received','cash_sale','expense')),
        amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
        txn_time TEXT NOT NULL,
        recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
        recorded_by TEXT DEFAULT 'worker',
        source TEXT DEFAULT 'voice' CHECK (source IN ('voice','manual')),
        parse_confidence REAL DEFAULT 1.0,
        note TEXT,
        status TEXT DEFAULT 'active' CHECK (status IN ('active','void')),
        voided_at TEXT,
        void_reason TEXT,
        replaces_txn_id INTEGER REFERENCES transactions(id),
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    );
    """)
    
    # 3. Transaction Items (for itemized parchi billing)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transaction_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER NOT NULL REFERENCES transactions(id),
        name TEXT NOT NULL,
        qty REAL,
        unit TEXT,
        unit_price_paise INTEGER,
        line_total_paise INTEGER
    );
    """)
    
    # 4. Bills Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_no INTEGER NOT NULL UNIQUE,
        transaction_id INTEGER NOT NULL REFERENCES transactions(id),
        customer_id INTEGER REFERENCES customers(id),
        customer_name TEXT,
        amount_paise INTEGER NOT NULL,
        pdf_path TEXT,
        voice_path TEXT,
        shared_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. Customer Memory (Opt-in)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer_memory (
        customer_id INTEGER PRIMARY KEY REFERENCES customers(id),
        notes TEXT,
        visit_count INTEGER DEFAULT 1,
        last_visit_at TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 6. Audit Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        entity TEXT,
        entity_id INTEGER,
        detail TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    conn.commit()

def seed_demo_data(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM customers")
    if cursor.fetchone()[0] == 0:
        today = datetime.date.today().isoformat()
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        
        # Seed synthetic Bangalore Kirana customers
        # Two Ramesh customers included specifically for name disambiguation tests!
        customers = [
            ("Ramesh Sharma", "Sharma ji (Kirana)", "RMSHRM", "+91 98765 43210", "hi-IN", 1),
            ("Ramesh Verma", "Verma ji (Tailor)", "RMVRM", "+91 98765 43211", "kn-IN", 1),
            ("Suresh Kumar", "Dairy Suresh", "SRSKMR", "+91 98765 43212", "kn-IN", 1),
            ("Anand Gowda", "Vegetable vendor", "ANDGWD", "+91 98765 43213", "kn-IN", 1),
            ("Murugan K", "Auto driver", "MRGNK", "+91 98765 43214", "ta-IN", 1),
            ("Priya Reddy", "Silk teacher", "PRYRD", "+91 98765 43215", "te-IN", 1)
        ]
        
        for name, alias, pkey, phone, lang, optin in customers:
            cursor.execute("""
            INSERT INTO customers (name, alias, phonetic_key, phone, language, whatsapp_opt_in)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (name, alias, pkey, phone, lang, optin))
            cust_id = cursor.lastrowid
            
            # Initial opening balances for realism
            if name == "Ramesh Sharma":
                cursor.execute("""
                INSERT INTO transactions (customer_id, customer_name, kind, amount_paise, txn_time, note)
                VALUES (?, ?, 'credit_sale', 45000, ?, 'Previous opening balance')
                """, (cust_id, name, yesterday))
            elif name == "Anand Gowda":
                cursor.execute("""
                INSERT INTO transactions (customer_id, customer_name, kind, amount_paise, txn_time, note)
                VALUES (?, ?, 'credit_sale', 65000, ?, 'Previous opening balance')
                """, (cust_id, name, yesterday))
            elif name == "Suresh Kumar":
                cursor.execute("""
                INSERT INTO transactions (customer_id, customer_name, kind, amount_paise, txn_time, note)
                VALUES (?, ?, 'credit_sale', 20000, ?, 'Previous opening balance')
                """, (cust_id, name, yesterday))
                
        conn.commit()
