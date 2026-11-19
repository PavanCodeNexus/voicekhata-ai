import sqlite3
import datetime
from typing import Dict, Any, Optional, List
from app.nlu.names import match_customers_in_db

def record_transaction(
    conn: sqlite3.Connection,
    customer_name: Optional[str],
    amount_paise: int,
    kind: str,
    txn_time: str,
    note: str = "",
    customer_id: Optional[int] = None,
    source: str = "voice",
    confidence: float = 1.0
) -> Dict[str, Any]:
    """
    Append-only write to ledger.
    """
    cursor = conn.cursor()
    
    # Resolve customer if not explicitly provided
    resolved_cust = None
    if customer_id:
        cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        row = cursor.fetchone()
        if row:
            resolved_cust = dict(row)
    elif customer_name:
        candidates = match_customers_in_db(customer_name, conn)
        if len(candidates) == 1:
            resolved_cust = candidates[0]
            customer_id = resolved_cust["id"]
            customer_name = resolved_cust["name"]
        elif len(candidates) > 1:
            return {
                "status": "AMBIGUOUS",
                "message": f"Multiple customers found matching '{customer_name}'",
                "candidates": candidates
            }
        else:
            # Auto-create new customer
            cursor.execute("""
            INSERT INTO customers (name, alias, phonetic_key, language)
            VALUES (?, 'New Customer', '', 'kn-IN')
            """, (customer_name.title(),))
            customer_id = cursor.lastrowid
            customer_name = customer_name.title()
            cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
            resolved_cust = dict(cursor.fetchone())

    # Insert transaction row
    cursor.execute("""
    INSERT INTO transactions (
        customer_id, customer_name, kind, amount_paise, txn_time,
        source, parse_confidence, note, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
    """, (customer_id, customer_name, kind, amount_paise, txn_time, source, confidence, note))
    
    txn_id = cursor.lastrowid
    
    # Audit log entry
    cursor.execute("""
    INSERT INTO audit_log (action, entity, entity_id, detail)
    VALUES ('txn.create', 'transaction', ?, ?)
    """, (txn_id, f"{kind} of Rs {amount_paise/100:.2f} for {customer_name or 'store'}"))
    
    conn.commit()
    
    # Get updated balance
    cur_bal_paise = get_customer_balance_paise(customer_id, conn) if customer_id else 0
    
    return {
        "status": "SUCCESS",
        "transaction_id": txn_id,
        "customer": resolved_cust,
        "amount_paise": amount_paise,
        "amount_rupees": amount_paise / 100.0,
        "kind": kind,
        "txn_time": txn_time,
        "new_balance_paise": cur_bal_paise,
        "new_balance_rupees": cur_bal_paise / 100.0
    }

def apply_correction(
    conn: sqlite3.Connection,
    new_amount_paise: int,
    customer_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Void and replace previous transaction (FR-N6 / US2).
    """
    cursor = conn.cursor()
    
    query = "SELECT * FROM transactions WHERE status = 'active'"
    params = []
    if customer_name:
        query += " AND LOWER(customer_name) LIKE ?"
        params.append(f"%{customer_name.strip().lower()}%")
    query += " ORDER BY id DESC LIMIT 1"
    
    cursor.execute(query, tuple(params))
    last_txn = cursor.fetchone()
    
    if not last_txn:
        return {"status": "ERROR", "message": "No recent active transaction found to correct."}
        
    old_id = last_txn["id"]
    cust_id = last_txn["customer_id"]
    c_name = last_txn["customer_name"]
    kind = last_txn["kind"]
    old_amt = last_txn["amount_paise"]
    now_iso = datetime.datetime.now().isoformat()
    
    # Mark old transaction void
    cursor.execute("""
    UPDATE transactions 
    SET status = 'void', voided_at = ?, void_reason = 'voice_correction'
    WHERE id = ?
    """, (now_iso, old_id))
    
    # Insert replacement transaction linked by replaces_txn_id
    cursor.execute("""
    INSERT INTO transactions (
        customer_id, customer_name, kind, amount_paise, txn_time,
        source, parse_confidence, note, status, replaces_txn_id
    ) VALUES (?, ?, ?, ?, ?, 'voice', 1.0, 'Corrected by voice', 'active', ?)
    """, (cust_id, c_name, kind, new_amount_paise, now_iso, old_id))
    
    new_id = cursor.lastrowid
    
    cursor.execute("""
    INSERT INTO audit_log (action, entity, entity_id, detail)
    VALUES ('txn.void_and_replace', 'transaction', ?, ?)
    """, (new_id, f"Replaced #{old_id} (Rs {old_amt/100}) with Rs {new_amount_paise/100}"))
    
    conn.commit()
    
    cur_bal_paise = get_customer_balance_paise(cust_id, conn) if cust_id else 0
    
    return {
        "status": "SUCCESS",
        "corrected": True,
        "old_transaction_id": old_id,
        "new_transaction_id": new_id,
        "customer_name": c_name,
        "kind": kind,
        "old_amount_paise": old_amt,
        "new_amount_paise": new_amount_paise,
        "new_balance_paise": cur_bal_paise,
        "new_balance_rupees": cur_bal_paise / 100.0
    }

def get_customer_balance_paise(customer_id: int, conn: sqlite3.Connection) -> int:
    """
    Computes running customer balance: credit_sale (+) minus payment_received (-).
    """
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        COALESCE(SUM(CASE WHEN kind = 'credit_sale' THEN amount_paise ELSE 0 END), 0) -
        COALESCE(SUM(CASE WHEN kind = 'payment_received' THEN amount_paise ELSE 0 END), 0) as balance_paise
    FROM transactions
    WHERE customer_id = ? AND status = 'active'
    """, (customer_id,))
    row = cursor.fetchone()
    return row["balance_paise"] if row else 0
