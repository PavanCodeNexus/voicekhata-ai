import sqlite3
import datetime
from typing import Dict, Any

def get_store_stats(conn: sqlite3.Connection, period: str = "7d") -> Dict[str, Any]:
    """
    Computes owner statistics: sales, credit given, collections, expenses, net cash, and ageing.
    Periods: 'today', '3d', '7d', '30d'
    """
    days_map = {"today": 0, "3d": 3, "7d": 7, "30d": 30}
    days = days_map.get(period.lower(), 7)
    
    start_date = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT kind, SUM(amount_paise) as total, COUNT(*) as count
    FROM transactions
    WHERE date(txn_time) >= date(?) AND status = 'active'
    GROUP BY kind
    """, (start_date,))
    
    stats_dict = {"credit_sale": 0, "payment_received": 0, "cash_sale": 0, "expense": 0}
    counts_dict = {"credit_sale": 0, "payment_received": 0, "cash_sale": 0, "expense": 0}
    
    for row in cursor.fetchall():
        k = row["kind"]
        if k in stats_dict:
            stats_dict[k] = row["total"] or 0
            counts_dict[k] = row["count"] or 0
            
    sales_paise = stats_dict["cash_sale"] + stats_dict["credit_sale"]
    credit_paise = stats_dict["credit_sale"]
    collections_paise = stats_dict["payment_received"]
    expense_paise = stats_dict["expense"]
    net_cash_paise = (stats_dict["cash_sale"] + stats_dict["payment_received"]) - expense_paise
    
    # Total outstanding
    cursor.execute("""
    SELECT 
        COALESCE(SUM(CASE WHEN kind = 'credit_sale' THEN amount_paise ELSE 0 END), 0) -
        COALESCE(SUM(CASE WHEN kind = 'payment_received' THEN amount_paise ELSE 0 END), 0) as total_out
    FROM transactions
    WHERE status = 'active'
    """)
    total_out = cursor.fetchone()["total_out"] or 0
    
    # Top debtors
    cursor.execute("""
    SELECT 
        c.id, c.name, c.alias, c.phone,
        COALESCE(SUM(CASE WHEN t.kind = 'credit_sale' THEN t.amount_paise ELSE 0 END), 0) -
        COALESCE(SUM(CASE WHEN t.kind = 'payment_received' THEN t.amount_paise ELSE 0 END), 0) as balance_paise
    FROM customers c
    JOIN transactions t ON c.id = t.customer_id
    WHERE t.status = 'active'
    GROUP BY c.id
    HAVING balance_paise > 0
    ORDER BY balance_paise DESC
    LIMIT 5
    """)
    top_debtors = [
        {
            "id": r["id"],
            "name": r["name"],
            "alias": r["alias"],
            "phone": r["phone"],
            "balance_paise": r["balance_paise"],
            "balance_rupees": r["balance_paise"] / 100.0
        }
        for r in cursor.fetchall()
    ]
    
    # Ageing buckets: 0-7 days, 8-30 days, 31+ days
    d7_str = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    d30_str = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    
    cursor.execute("""
    SELECT 
        SUM(CASE WHEN date(txn_time) >= date(?) THEN amount_paise ELSE 0 END) as bucket_0_7,
        SUM(CASE WHEN date(txn_time) >= date(?) AND date(txn_time) < date(?) THEN amount_paise ELSE 0 END) as bucket_8_30,
        SUM(CASE WHEN date(txn_time) < date(?) THEN amount_paise ELSE 0 END) as bucket_31_plus
    FROM transactions
    WHERE kind = 'credit_sale' AND status = 'active'
    """, (d7_str, d30_str, d7_str, d30_str))
    
    ageing_row = cursor.fetchone()
    
    return {
        "period": period,
        "sales_rupees": sales_paise / 100.0,
        "credit_given_rupees": credit_paise / 100.0,
        "collections_rupees": collections_paise / 100.0,
        "expenses_rupees": expense_paise / 100.0,
        "net_cash_rupees": net_cash_paise / 100.0,
        "total_outstanding_rupees": total_out / 100.0,
        "top_debtors": top_debtors,
        "ageing": {
            "bucket_0_7_rupees": (ageing_row["bucket_0_7"] or 0) / 100.0,
            "bucket_8_30_rupees": (ageing_row["bucket_8_30"] or 0) / 100.0,
            "bucket_31_plus_rupees": (ageing_row["bucket_31_plus"] or 0) / 100.0
        }
    }
