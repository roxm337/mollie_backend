from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mollie_id: Optional[str] = Field(default=None, index=True)
    amount: float
    currency: str = "EUR"
    description: Optional[str] = None
    status: str = Field(default="open", index=True)  # open, pending, paid, canceled, failed
    checkout_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    payment_metadata: Optional[str] = Field(default=None, alias="metadata")  # JSON string if you want to store app metadata
    idempotency_key: Optional[str] = None

