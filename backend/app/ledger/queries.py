import sqlite3
import datetime
from typing import Dict, Any, List, Optional
from app.ledger.service import get_customer_balance_paise

def get_day_book(conn: sqlite3.Connection, date_str: Optional[str] = None) -> Dict[str, Any]:
    """
    FR-B1: Day-book for a specific date (default today).
    """
    target_date = date_str or datetime.date.today().isoformat()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT t.*, c.alias as customer_alias 
    FROM transactions t
    LEFT JOIN customers c ON t.customer_id = c.id
    WHERE date(t.txn_time) = date(?) AND t.status = 'active'
    ORDER BY t.id DESC
    """, (target_date,))
    
    rows = [dict(r) for r in cursor.fetchall()]
    
    credit_total = sum(r["amount_paise"] for r in rows if r["kind"] == "credit_sale")
    payment_total = sum(r["amount_paise"] for r in rows if r["kind"] == "payment_received")
    cash_total = sum(r["amount_paise"] for r in rows if r["kind"] == "cash_sale")
    expense_total = sum(r["amount_paise"] for r in rows if r["kind"] == "expense")
    
    return {
        "date": target_date,
        "transactions": rows,
        "count": len(rows),
        "credit_paise": credit_total,
        "payment_paise": payment_total,
        "cash_paise": cash_total,
        "expense_paise": expense_total,
        "net_cash_paise": (cash_total + payment_total) - expense_total
    }

def get_today_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Sub-2s query for voice answer (F8 / US4).
    """
    today_str = datetime.date.today().isoformat()
    book = get_day_book(conn, today_str)
    
    cursor = conn.cursor()
    # Total store outstanding across all customers
    cursor.execute("""
    SELECT 
        COALESCE(SUM(CASE WHEN kind = 'credit_sale' THEN amount_paise ELSE 0 END), 0) -
        COALESCE(SUM(CASE WHEN kind = 'payment_received' THEN amount_paise ELSE 0 END), 0) as total_outstanding_paise
    FROM transactions
    WHERE status = 'active'
    """)
    total_out = cursor.fetchone()["total_outstanding_paise"] or 0
    
    return {
        "date": today_str,
        "today_credit_paise": book["credit_paise"],
        "today_credit_rupees": book["credit_paise"] / 100.0,
        "today_payment_paise": book["payment_paise"],
        "today_payment_rupees": book["payment_paise"] / 100.0,
        "today_count": book["count"],
        "total_outstanding_paise": total_out,
        "total_outstanding_rupees": total_out / 100.0
    }

def get_customer_statement(conn: sqlite3.Connection, customer_id: int) -> Dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
    cust = cursor.fetchone()
    if not cust:
        return {}
        
    cust_dict = dict(cust)
    cursor.execute("""
    SELECT * FROM transactions 
    WHERE customer_id = ? AND status = 'active'
    ORDER BY id ASC
    """, (customer_id,))
    txns = [dict(r) for r in cursor.fetchall()]
    
    bal_paise = get_customer_balance_paise(customer_id, conn)
    cust_dict["balance_paise"] = bal_paise
    cust_dict["balance_rupees"] = bal_paise / 100.0
    
    return {
        "customer": cust_dict,
        "transactions": txns,
        "current_balance_paise": bal_paise,
        "current_balance_rupees": bal_paise / 100.0
    }
