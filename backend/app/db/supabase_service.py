import httpx
import logging
from typing import Dict, Any, List, Optional
from app.config import settings

logger = logging.getLogger("voicekhata.supabase")

class SupabaseService:
    def __init__(self):
        self.url = (settings.SUPABASE_URL or "").rstrip("/")
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
                f"{self.url}/rest/v1/customers?select=id&limit=1",
                headers=self.headers,
                timeout=3.0
            )
            if r.status_code == 200:
                return True
            # Fallback check
            r2 = httpx.get(
                f"{self.url}/rest/v1/vk_customers?select=id&limit=1",
                headers=self.headers,
                timeout=3.0
            )
            return r2.status_code == 200
        except Exception as e:
            logger.warning(f"Supabase ping failed: {e}")
            return False

    def get_customers(self) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []
        try:
            r = httpx.get(
                f"{self.url}/rest/v1/customers?select=*&order=name.asc",
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
        Sync transaction to Supabase table (transactions or vk_transactions)
        """
        if not self.is_configured():
            return None
        try:
            # Try primary table
            r = httpx.post(
                f"{self.url}/rest/v1/transactions",
                headers=self.headers,
                json=txn_payload,
                timeout=4.0
            )
            if r.status_code in (200, 201):
                res = r.json()
                return res[0] if isinstance(res, list) and len(res) > 0 else res
            
            # Fallback to vk_transactions if present
            r2 = httpx.post(
                f"{self.url}/rest/v1/vk_transactions",
                headers=self.headers,
                json=txn_payload,
                timeout=4.0
            )
            if r2.status_code in (200, 201):
                res2 = r2.json()
                return res2[0] if isinstance(res2, list) and len(res2) > 0 else res2
        except Exception as e:
            logger.error(f"Error syncing transaction to Supabase: {e}")
        return None

supabase_service = SupabaseService()
