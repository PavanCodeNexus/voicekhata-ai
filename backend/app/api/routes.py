import os
import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models import init_db, seed_demo_data
from app.ledger.service import record_transaction, apply_correction
from app.ledger.queries import get_day_book, get_today_summary, get_customer_statement
from app.ledger.stats import get_store_stats
from app.agent.graph import process_utterance, session_cache
from app.documents.bill_pdf import generate_bill_pdf
from app.documents.export_xlsx import export_ledger_to_excel
from app.config import settings

api_router = APIRouter()

class TextUtteranceRequest(BaseModel):
    text: str
    language: Optional[str] = "kn-IN"

class ManualTxnRequest(BaseModel):
    customer_name: str
    amount_rupees: float
    kind: str # 'credit_sale', 'payment_received', 'cash_sale', 'expense'
    note: Optional[str] = ""

@api_router.get("/health")
def health_check():
    from app.db.supabase_service import supabase_service
    sb_connected = supabase_service.ping()
    return {
        "status": "healthy",
        "service": "VoiceKhata AI",
        "version": settings.VERSION,
        "database": {
            "mode": "supabase" if sb_connected else "sqlite_fallback",
            "supabase_configured": supabase_service.is_configured(),
            "supabase_connected": sb_connected,
            "supabase_url": settings.SUPABASE_URL
        }
    }

@api_router.get("/supabase/status")
def supabase_status():
    from app.db.supabase_service import supabase_service
    sb_connected = supabase_service.ping()
    return {
        "supabase_configured": supabase_service.is_configured(),
        "supabase_connected": sb_connected,
        "supabase_url": settings.SUPABASE_URL,
        "schema": "voicekhata",
        "views": ["vk_customers", "vk_transactions", "vk_bills"]
    }

@api_router.get("/summary")
def get_summary_endpoint():
    with get_db() as conn:
        return get_today_summary(conn)

@api_router.get("/stats")
def get_stats_endpoint(range: str = Query("7d", pattern="^(today|3d|7d|30d)$")):
    with get_db() as conn:
        return get_store_stats(conn, range)

@api_router.get("/daybook")
def get_daybook_endpoint(date: Optional[str] = None):
    with get_db() as conn:
        return get_day_book(conn, date)

@api_router.get("/customers")
def get_customers_endpoint(q: Optional[str] = None):
    with get_db() as conn:
        cursor = conn.cursor()
        if q:
            cursor.execute("""
            SELECT c.*, 
                COALESCE(SUM(CASE WHEN t.kind = 'credit_sale' THEN t.amount_paise ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN t.kind = 'payment_received' THEN t.amount_paise ELSE 0 END), 0) as balance_paise
            FROM customers c
            LEFT JOIN transactions t ON c.id = t.customer_id AND t.status = 'active'
            WHERE LOWER(c.name) LIKE ? OR LOWER(c.alias) LIKE ?
            GROUP BY c.id
            ORDER BY c.name ASC
            """, (f"%{q.lower()}%", f"%{q.lower()}%"))
        else:
            cursor.execute("""
            SELECT c.*, 
                COALESCE(SUM(CASE WHEN t.kind = 'credit_sale' THEN t.amount_paise ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN t.kind = 'payment_received' THEN t.amount_paise ELSE 0 END), 0) as balance_paise
            FROM customers c
            LEFT JOIN transactions t ON c.id = t.customer_id AND t.status = 'active'
            GROUP BY c.id
            ORDER BY balance_paise DESC
            """)
        rows = [dict(r) for r in cursor.fetchall()]
        for r in rows:
            r["balance_rupees"] = (r["balance_paise"] or 0) / 100.0
        return rows

@api_router.get("/customers/{customer_id}/ledger")
def get_customer_ledger_endpoint(customer_id: int):
    with get_db() as conn:
        stmt = get_customer_statement(conn, customer_id)
        if not stmt:
            raise HTTPException(status_code=404, detail="Customer not found")
        return stmt

@api_router.get("/transactions")
def get_transactions_endpoint(limit: int = 40):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        for r in rows:
            r["amount_rupees"] = r["amount_paise"] / 100.0
        return rows

@api_router.post("/transactions")
def create_manual_transaction(req: ManualTxnRequest):
    with get_db() as conn:
        amt_paise = int(round(req.amount_rupees * 100))
        now_iso = datetime.datetime.now().isoformat()
        res = record_transaction(
            conn=conn,
            customer_name=req.customer_name,
            amount_paise=amt_paise,
            kind=req.kind,
            txn_time=now_iso,
            note=req.note or "Manual entry",
            source="manual"
        )
        return res

@api_router.post("/process_utterance")
def process_utterance_endpoint(req: TextUtteranceRequest):
    """
    Simulates speech input or text processing through the LangGraph State Engine.
    """
    with get_db() as conn:
        res = process_utterance(req.text, req.language or "kn-IN", conn)
        return res

@api_router.post("/bills/{transaction_id}")
def create_bill_for_transaction(transaction_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
        txn = cursor.fetchone()
        if not txn:
            raise HTTPException(status_code=404, detail="Transaction not found")
            
        cursor.execute("SELECT MAX(bill_no) as max_no FROM bills")
        max_no = cursor.fetchone()["max_no"] or 1000
        bill_no = max_no + 1
        
        c_id = txn["customer_id"]
        c_name = txn["customer_name"] or "Walk-in"
        amt_rs = txn["amount_paise"] / 100.0
        kind = txn["kind"]
        t_time = txn["txn_time"]
        
        # Calculate running balance
        cursor.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN kind = 'credit_sale' THEN amount_paise ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN kind = 'payment_received' THEN amount_paise ELSE 0 END), 0) as bal
        FROM transactions WHERE customer_id = ? AND status = 'active'
        """, (c_id,))
        bal_rs = (cursor.fetchone()["bal"] or 0) / 100.0
        
        pdf_path = generate_bill_pdf(bill_no, c_name, amt_rs, kind, bal_rs, t_time)
        
        cursor.execute("""
        INSERT INTO bills (bill_no, transaction_id, customer_id, customer_name, amount_paise, pdf_path)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (bill_no, transaction_id, c_id, c_name, txn["amount_paise"], pdf_path))
        bill_id = cursor.lastrowid
        conn.commit()
        
        # WhatsApp Share Link
        wa_msg = (
            f"Namaste {c_name} ji 🙏\n"
            f"Bill #{bill_no} of Rs {amt_rs:.2f} ({kind.replace('_', ' ').title()}) recorded.\n"
            f"Current Balance: Rs {bal_rs:.2f}.\n"
            f"Pay via UPI: {settings.SHOP_UPI_VPA}\n"
            f"Thank you!"
        )
        encoded_wa = wa_msg.replace(' ', '%20').replace('\n', '%0A')
        wa_url = f"https://wa.me/?text={encoded_wa}"
        
        return {
            "bill_id": bill_id,
            "bill_no": bill_no,
            "pdf_filename": os.path.basename(pdf_path),
            "whatsapp_url": wa_url,
            "message": wa_msg
        }

@api_router.get("/bills/{bill_id}/pdf")
def download_bill_pdf(bill_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bills WHERE id = ?", (bill_id,))
        b = cursor.fetchone()
        if not b or not os.path.exists(b["pdf_path"]):
            raise HTTPException(status_code=404, detail="Bill PDF not found")
        return FileResponse(b["pdf_path"], media_type="application/pdf", filename=os.path.basename(b["pdf_path"]))

@api_router.get("/exports")
def export_data_endpoint(type: str = "csv"):
    with get_db() as conn:
        csv_path = export_ledger_to_excel(conn)
        return FileResponse(
            csv_path,
            media_type="text/csv",
            filename=os.path.basename(csv_path)
        )

@api_router.post("/reset_demo")
def reset_demo_endpoint():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS bills;")
        cursor.execute("DROP TABLE IF EXISTS transaction_items;")
        cursor.execute("DROP TABLE IF EXISTS transactions;")
        cursor.execute("DROP TABLE IF EXISTS customer_memory;")
        cursor.execute("DROP TABLE IF EXISTS audit_log;")
        cursor.execute("DROP TABLE IF EXISTS customers;")
        conn.commit()
        init_db(conn)
        seed_demo_data(conn)
        session_cache["pending_ambiguity"] = None
        session_cache["last_customer_name"] = None
        return {"status": "SUCCESS", "message": "Demo database successfully reset with fresh test data."}
