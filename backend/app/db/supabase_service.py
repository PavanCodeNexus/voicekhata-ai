import httpx
import logging
from typing import Dict, Any, List, Optional
from app.config import settings

logger = logging.getLogger("voicekhata.supabase")

class SupabaseService:
    def __init__(self):
        self.url = settings.SUPABASE_URL.rstrip("/") if settings.SUPABASE_URL else ""
        self.key = settings.SUPABASE_KEY or ""
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def is_configured(self) -> bool:
        return bool(self.url and self.key)

    def ping(self) -> bool:
        if not self.is_configured():
            return False
        try:
            r = httpx.get(
                f"{self.url}/rest/v1/vk_customers?select=id&limit=1",
                headers=self.headers,
                timeout=3.0
            )
            return r.status_code == 200
        except Exception as e:
            logger.warning(f"Supabase ping failed: {e}")
            return False

    def get_customers(self) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []
        try:
            r = httpx.get(
                f"{self.url}/rest/v1/vk_customers?select=*&order=name.asc",
                headers=self.headers,
                timeout=4.0
            )
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.error(f"Error fetching Supabase customers: {e}")
        return []

    def record_transaction(self, txn_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Sync transaction to Supabase table
        """
        if not self.is_configured():
            return None
        try:
            r = httpx.post(
                f"{self.url}/rest/v1/vk_transactions",
                headers=self.headers,
                json=txn_payload,
                timeout=4.0
            )
            if r.status_code in (200, 201):
                res = r.json()
                return res[0] if isinstance(res, list) and len(res) > 0 else res
        except Exception as e:
            logger.error(f"Error syncing transaction to Supabase: {e}")
        return None

supabase_service = SupabaseService()
