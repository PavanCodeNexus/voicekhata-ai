import time
import re
import sqlite3
import datetime
import httpx
import logging
from typing import Dict, Any, Optional

from app.config import settings
from app.agent.state import AgentState
from app.agent.templates.voice_templates import format_spoken_response
from app.nlu.numbers import parse_spoken_number
from app.nlu.direction import detect_transaction_direction
from app.nlu.dates import resolve_relative_date
from app.nlu.names import extract_candidate_name_from_text, match_customers_in_db
from app.ledger.service import record_transaction, apply_correction
from app.ledger.queries import get_today_summary, get_customer_statement

logger = logging.getLogger("voicekhata.agent")

def groq_llm_parse(transcript: str, language: str) -> Optional[Dict[str, Any]]:
    """Optional Groq LLM fallback for complex, highly colloquial sentences."""
    if not settings.GROQ_API_KEY:
        return None
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        prompt = (
            "You are an Indian Kirana store Khata NLU parser. Extract customer name, amount in rupees, and transaction kind (credit_sale or payment_received) from this spoken transcript.\n"
            f"Transcript: \"{transcript}\"\n"
            "Return JSON only: {\"customer_name\": string, \"amount_rupees\": float, \"kind\": \"credit_sale\"|\"payment_received\"}"
        )
        for model in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]:
            try:
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1,
                    "max_tokens": 150
                }
                r = httpx.post(url, headers=headers, json=payload, timeout=3.0)
                if r.status_code == 200:
                    import json
                    data = r.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    if parsed.get("amount_rupees") and parsed.get("customer_name"):
                        return parsed
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Groq LLM fallback error: {e}")
    return None

# Session memory for active ambiguity and last active customer
session_cache: Dict[str, Any] = {
    "pending_ambiguity": None,
    "last_customer_name": None,
    "turn_count": 0
}

# Fast keyword triggers
CORRECTION_WORDS = ["alla", "nahi", "wrong", "change", "cancel", "galat", "thappu"]
TODAY_QUERY_WORDS = ["aaj kitna", "aaj ka total", "today total", "ivatthu eshtu", "ivathu eshtu", "today credit"]
BALANCE_QUERY_WORDS = ["total", "baaki", "balance", "kodbeku", "tharanum", "ivvali"]

def process_utterance(transcript: str, language: str = "kn-IN", conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """
    Main LangGraph State Machine execution loop.
    Enforces 'Rules First, LLM Second' for sub-2s execution.
    """
    t_start = time.time()
    clean = transcript.strip().lower()
    timings = {}
    
    # 1. Check for Pending Ambiguity Clarification
    if session_cache.get("pending_ambiguity"):
        pending = session_cache["pending_ambiguity"]
        candidates = pending.get("candidates", [])
        matched_cand = None
        words = clean.split()
        for cand in candidates:
            c_name = cand["name"].lower()
            c_alias = (cand.get("alias") or "").lower()
            if c_name in clean or clean in c_name or clean in c_alias or any(w in c_alias or w in c_name for w in words if len(w) > 2):
                matched_cand = cand
                break
                
        if matched_cand:
            txn_req = pending["txn_request"]
            res = record_transaction(
                conn=conn,
                customer_name=matched_cand["name"],
                amount_paise=txn_req["amount_paise"],
                kind=txn_req["kind"],
                txn_time=txn_req["txn_time"],
                customer_id=matched_cand["id"]
            )
            session_cache["pending_ambiguity"] = None
            session_cache["last_customer_name"] = matched_cand["name"]
            
            timings["parse_ms"] = int((time.time() - t_start) * 1000)
            voice_out = format_spoken_response({
                "intent": "TRANSACTION",
                "records": [res]
            }, lang=language)
            timings["total_ms"] = int((time.time() - t_start) * 1000)
            
            return {
                "intent": "TRANSACTION",
                "status": "SUCCESS",
                "records": [res],
                "spoken_reply": voice_out,
                "timings": timings
            }

    # 2. Check for Correction Intent ("alla, 430" / "nahi, 430 likhna")
    if any(cw in clean.split() or clean.startswith(cw) for cw in CORRECTION_WORDS):
        new_amt_paise = parse_spoken_number(clean)
        if new_amt_paise:
            # For short corrections, default to the last active customer
            cust_cand = extract_candidate_name_from_text(clean)
            cust_name = cust_cand if (cust_cand and len(clean.split()) > 4) else session_cache.get("last_customer_name")
            corr_res = apply_correction(conn, new_amt_paise, cust_name)
            
            timings["parse_ms"] = int((time.time() - t_start) * 1000)
            corr_res["intent"] = "CORRECTION"
            voice_out = format_spoken_response(corr_res, lang=language)
            timings["total_ms"] = int((time.time() - t_start) * 1000)
            
            return {
                "intent": "CORRECTION",
                "status": corr_res["status"],
                "result": corr_res,
                "spoken_reply": voice_out,
                "timings": timings
            }

    # 3. Check for Today's Summary Query ("Aaj kitna udhaar gaya?" / "Ivatthu eshtu saala?")
    if any(qw in clean for qw in TODAY_QUERY_WORDS):
        today_stats = get_today_summary(conn)
        today_stats["intent"] = "QUERY_TODAY_SUMMARY"
        
        timings["parse_ms"] = int((time.time() - t_start) * 1000)
        voice_out = format_spoken_response(today_stats, lang=language)
        timings["total_ms"] = int((time.time() - t_start) * 1000)
        
        return {
            "intent": "QUERY_TODAY_SUMMARY",
            "status": "SUCCESS",
            "summary": today_stats,
            "spoken_reply": voice_out,
            "timings": timings
        }

    # 4. Check for Specific Customer Balance Query ("Ramesh ka total?" / "Ramesh eshtu kodbeku?")
    if any(bw in clean for bw in BALANCE_QUERY_WORDS) and not parse_spoken_number(clean):
        c_name = extract_candidate_name_from_text(clean)
        if c_name:
            candidates = match_customers_in_db(c_name, conn)
            if len(candidates) > 1:
                session_cache["pending_ambiguity"] = {
                    "candidates": candidates,
                    "txn_request": None
                }
                timings["parse_ms"] = int((time.time() - t_start) * 1000)
                voice_out = format_spoken_response({
                    "intent": "AMBIGUOUS",
                    "candidates": candidates
                }, lang=language)
                timings["total_ms"] = int((time.time() - t_start) * 1000)
                return {
                    "intent": "AMBIGUOUS",
                    "candidates": candidates,
                    "spoken_reply": voice_out,
                    "timings": timings
                }
            elif len(candidates) == 1:
                stmt = get_customer_statement(conn, candidates[0]["id"])
                timings["parse_ms"] = int((time.time() - t_start) * 1000)
                voice_out = format_spoken_response({
                    "intent": "QUERY_CUSTOMER_BALANCE",
                    "customer": stmt["customer"]
                }, lang=language)
                timings["total_ms"] = int((time.time() - t_start) * 1000)
                return {
                    "intent": "QUERY_CUSTOMER_BALANCE",
                    "customer": stmt["customer"],
                    "spoken_reply": voice_out,
                    "timings": timings
                }

    # 5. Compound / Multi-Clause Transactions ("Ramesh ka 340 udhaar, kal 200 diya tha")
    sub_clauses = re.split(r'[,;\+]|\baur\b|\band\b|\bmatthu\b', clean)
    if len(sub_clauses) > 1:
        extracted = []
        for clause in sub_clauses:
            clause = clause.strip()
            amt_paise = parse_spoken_number(clause)
            if amt_paise:
                c_name = extract_candidate_name_from_text(clause)
                kind, conf = detect_transaction_direction(clause)
                date_iso, _ = resolve_relative_date(clause)
                extracted.append({
                    "customer_name": c_name,
                    "amount_paise": amt_paise,
                    "kind": kind,
                    "txn_time": date_iso,
                    "confidence": conf
                })
        if len(extracted) > 1:
            # Propagate primary customer name if missing in subsequent clauses
            base_name = extracted[0]["customer_name"]
            records = []
            for item in extracted:
                t_cust = item["customer_name"] or base_name
                res = record_transaction(
                    conn=conn,
                    customer_name=t_cust,
                    amount_paise=item["amount_paise"],
                    kind=item["kind"],
                    txn_time=item["txn_time"],
                    confidence=item["confidence"]
                )
                if res.get("status") == "AMBIGUOUS":
                    session_cache["pending_ambiguity"] = {
                        "candidates": res["candidates"],
                        "txn_request": item
                    }
                    voice_out = format_spoken_response({
                        "intent": "AMBIGUOUS",
                        "candidates": res["candidates"]
                    }, lang=language)
                    return {
                        "intent": "AMBIGUOUS",
                        "candidates": res["candidates"],
                        "spoken_reply": voice_out,
                        "timings": timings
                    }
                records.append(res)
                session_cache["last_customer_name"] = t_cust

            timings["parse_ms"] = int((time.time() - t_start) * 1000)
            voice_out = format_spoken_response({
                "intent": "COMPOUND_TRANSACTION",
                "records": records
            }, lang=language)
            timings["total_ms"] = int((time.time() - t_start) * 1000)
            
            return {
                "intent": "COMPOUND_TRANSACTION",
                "status": "SUCCESS",
                "records": records,
                "spoken_reply": voice_out,
                "timings": timings
            }

    # 6. Single Standard Voice Entry ("Ramesh ka 340 udhaar")
    amt_paise = parse_spoken_number(clean)
    if amt_paise:
        c_name = extract_candidate_name_from_text(clean)
        kind, conf = detect_transaction_direction(clean)
        date_iso, _ = resolve_relative_date(clean)
        
        res = record_transaction(
            conn=conn,
            customer_name=c_name or "Walk-in",
            amount_paise=amt_paise,
            kind=kind,
            txn_time=date_iso,
            confidence=conf
        )
        
        if res.get("status") == "AMBIGUOUS":
            session_cache["pending_ambiguity"] = {
                "candidates": res["candidates"],
                "txn_request": {
                    "customer_name": c_name,
                    "amount_paise": amt_paise,
                    "kind": kind,
                    "txn_time": date_iso
                }
            }
            timings["parse_ms"] = int((time.time() - t_start) * 1000)
            voice_out = format_spoken_response({
                "intent": "AMBIGUOUS",
                "candidates": res["candidates"]
            }, lang=language)
            timings["total_ms"] = int((time.time() - t_start) * 1000)
            return {
                "intent": "AMBIGUOUS",
                "candidates": res["candidates"],
                "spoken_reply": voice_out,
                "timings": timings
            }
            
        session_cache["last_customer_name"] = c_name
        timings["parse_ms"] = int((time.time() - t_start) * 1000)
        voice_out = format_spoken_response({
            "intent": "TRANSACTION",
            "records": [res]
        }, lang=language)
        timings["total_ms"] = int((time.time() - t_start) * 1000)
        
        return {
            "intent": "TRANSACTION",
            "status": "SUCCESS",
            "records": [res],
            "spoken_reply": voice_out,
            "timings": timings
        }

    # 6. Optional Groq LLM Fallback (if deterministic rules did not catch it)
    if settings.GROQ_API_KEY:
        llm_res = groq_llm_parse(transcript, language)
        if llm_res and conn:
            c_name = llm_res.get("customer_name")
            amt_rupees = float(llm_res.get("amount_rupees", 0))
            amt_paise = int(round(amt_rupees * 100))
            kind = llm_res.get("kind", "credit_sale")
            if c_name and amt_paise > 0:
                res = record_transaction(
                    conn=conn,
                    customer_name=c_name,
                    amount_paise=amt_paise,
                    kind=kind,
                    txn_time=datetime.datetime.now().isoformat(),
                    confidence=0.85
                )
                voice_out = format_spoken_response({
                    "intent": "TRANSACTION",
                    "records": [res]
                }, lang=language)
                timings["total_ms"] = int((time.time() - t_start) * 1000)
                return {
                    "intent": "TRANSACTION",
                    "status": "SUCCESS",
                    "records": [res],
                    "spoken_reply": voice_out,
                    "timings": timings,
                    "source": "groq_llm"
                }

    # Fallback
    timings["total_ms"] = int((time.time() - t_start) * 1000)
    return {
        "intent": "UNKNOWN",
        "spoken_reply": "Hisab samajh nahi aaya, kripya dobara bolein." if "hi" in language else "Hisab artha aaglilla, mathomme heli.",
        "timings": timings
    }
