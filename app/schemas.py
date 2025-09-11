from pydantic import BaseModel, Field
from typing import Optional

class CreatePaymentIn(BaseModel):
    amount: str = Field(..., description="Amount as string e.g. '10.00'")
    currency: Optional[str] = "EUR"
    description: Optional[str] = None
    redirect_url: Optional[str] = None  # override default FRONTEND_RETURN_URL
    metadata: Optional[dict] = None
    idempotency_key: Optional[str] = None  # optional client idempotency

class CreatePaymentOut(BaseModel):
    mollie_id: str
    checkout_url: str
    status: str

class PaymentStatusOut(BaseModel):
    mollie_id: str
    status: str
    amount: Optional[dict] = None
    description: Optional[str] = None
    checkout_url: Optional[str] = None
    raw: Optional[dict] = None

