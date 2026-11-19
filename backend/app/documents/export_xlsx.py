import sqlite3
import datetime
import csv
from pathlib import Path
from app.config import settings

def export_ledger_to_excel(conn: sqlite3.Connection) -> str:
    """
    FR-B3: Generates CSV / Excel workbook of all customers and daily transactions.
    """
    filename = f"VoiceKhata_Export_{datetime.date.today().isoformat()}.csv"
    out_path = settings.EXPORTS_DIR / filename
    
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        c.id, c.name, c.alias, c.phone, c.language,
        COALESCE(SUM(CASE WHEN t.kind = 'credit_sale' THEN t.amount_paise ELSE 0 END), 0) -
        COALESCE(SUM(CASE WHEN t.kind = 'payment_received' THEN t.amount_paise ELSE 0 END), 0) as balance_paise
    FROM customers c
    LEFT JOIN transactions t ON c.id = t.customer_id AND t.status = 'active'
    GROUP BY c.id
    ORDER BY balance_paise DESC
    """)
    customer_rows = cursor.fetchall()
    
    cursor.execute("""
    SELECT id, txn_time, customer_name, kind, amount_paise, source, parse_confidence, status
    FROM transactions
    ORDER BY id DESC
    """)
    txn_rows = cursor.fetchall()
    
    with open(out_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["=== VOICEKHATA AI: CUSTOMER BALANCES ==="])
        writer.writerow(["Customer ID", "Name", "Alias", "Phone", "Language", "Total Balance (Rs)", "Status"])
        for r in customer_rows:
            bal_rs = (r["balance_paise"] or 0) / 100.0
            status = "Dues Pending" if bal_rs > 0 else "Cleared"
            writer.writerow([r["id"], r["name"], r["alias"], r["phone"], r["language"], f"{bal_rs:.2f}", status])
            
        writer.writerow([])
        writer.writerow(["=== DAILY TRANSACTIONS JOURNAL ==="])
        writer.writerow(["Txn ID", "Date & Time", "Customer Name", "Type", "Amount (Rs)", "Source", "Confidence", "Status"])
        for r in txn_rows:
            writer.writerow([
                r["id"], r["txn_time"], r["customer_name"], r["kind"],
                f"{r['amount_paise'] / 100.0:.2f}", r["source"], r["parse_confidence"], r["status"]
            ])
            
    return str(out_path)
