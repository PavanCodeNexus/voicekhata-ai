from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class AgentState(BaseModel):
    transcript: str
    language: str = "kn-IN"
    speaker_id: Optional[str] = "worker"
    role: str = "worker"
    intent: Optional[str] = None # 'entry', 'query', 'correction', 'disambiguate_reply', 'unknown'
    customer_name: Optional[str] = None
    customer_id: Optional[int] = None
    amount_paise: Optional[int] = None
    kind: Optional[str] = None # 'credit_sale', 'payment_received', 'cash_sale', 'expense'
    txn_time: Optional[str] = None
    confidence: float = 1.0
    pending_ambiguity: Optional[Dict[str, Any]] = None
    records: List[Dict[str, Any]] = []
    spoken_reply: Optional[str] = None
    latency_timings: Dict[str, int] = {}
