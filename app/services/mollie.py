import uuid
import httpx
from typing import Optional
from ..config import settings

MOLLIE_BASE = settings.mollie_api_base
API_KEY = settings.mollie_api_key
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

async def create_mollie_payment(amount: str,
                                currency: str = "EUR",
                                description: Optional[str] = None,
                                redirect_url: Optional[str] = None,
                                idempotency_key: Optional[str] = None,
                                metadata: Optional[dict] = None,
                                ) -> dict:
    """
    Create a Mollie payment and return JSON response.
    """
    if not redirect_url:
        redirect_url = settings.frontend_return_url

    payload = {
        "amount": {"currency": currency, "value": amount},
        "description": description or "Payment",
        "redirectUrl": redirect_url,
    }
    if metadata:
        payload["metadata"] = metadata

    # choose idempotency key
    idem_key = idempotency_key or str(uuid.uuid4())

    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = HEADERS.copy()
        headers["Idempotency-Key"] = idem_key
        resp = await client.post(f"{MOLLIE_BASE}/payments", json=payload, headers=headers)
        resp.raise_for_status()
        return {"data": resp.json(), "idempotency_key": idem_key}


async def get_mollie_payment(payment_id: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        headers = HEADERS.copy()
        resp = await client.get(f"{MOLLIE_BASE}/payments/{payment_id}", headers=headers)
        resp.raise_for_status()
        return resp.json()

