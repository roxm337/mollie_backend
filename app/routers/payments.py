from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import Optional
from ..schemas import CreatePaymentIn, CreatePaymentOut, PaymentStatusOut
from ..services.mollie import create_mollie_payment, get_mollie_payment
from ..db import async_session
from ..models import Payment
from ..utils import require_service_api_key
from ..config import settings
import json
from datetime import datetime

router = APIRouter(prefix="/payments", tags=["payments"])

# internal helper to persist a payment
async def save_payment_to_db(session: AsyncSession, mollie_json: dict, idempotency_key: str, metadata: Optional[dict]):
    mollie_id = mollie_json.get("id")
    amount = mollie_json.get("amount", {}).get("value")
    currency = mollie_json.get("amount", {}).get("currency", "EUR")
    checkout_url = mollie_json.get("_links", {}).get("checkout", {}).get("href")

    # convert amount string to float safely
    try:
        amount_f = float(amount) if amount is not None else 0.0
    except:
        amount_f = 0.0

    # upsert by idempotency_key or mollie_id
    q = select(Payment).where(Payment.idempotency_key == idempotency_key)
    res = await session.exec(q)
    found = res.one_or_none()
    if found:
        found.mollie_id = mollie_id
        found.checkout_url = checkout_url
        found.amount = amount_f
        found.currency = currency
        found.description = mollie_json.get("description")
        found.status = mollie_json.get("status", "open")
        found.payment_metadata = json.dumps(metadata) if metadata else None
        found.updated_at = datetime.utcnow()
        session.add(found)
        await session.commit()
        await session.refresh(found)
        return found
    else:
        new = Payment(
            mollie_id=mollie_id,
            amount=amount_f,
            currency=currency,
            description=mollie_json.get("description"),
            status=mollie_json.get("status", "open"),
            checkout_url=checkout_url,
            payment_metadata=json.dumps(metadata) if metadata else None,
            idempotency_key=idempotency_key,
        )
        session.add(new)
        await session.commit()
        await session.refresh(new)
        return new

@router.post("/create", response_model=CreatePaymentOut, dependencies=[Depends(require_service_api_key)])
async def create_payment(payload: CreatePaymentIn):
    """Create a Mollie payment. Protected by SERVICE API KEY header."""
    # call Mollie
    mollie_resp = await create_mollie_payment(
        amount=payload.amount,
        currency=payload.currency or "EUR",
        description=payload.description,
        redirect_url=payload.redirect_url or settings.frontend_return_url,
        idempotency_key=payload.idempotency_key,
        metadata=payload.metadata,
    )
    mollie_json = mollie_resp["data"]
    idem_key = mollie_resp["idempotency_key"]

    # persist
    async with async_session() as session:
        payment = await save_payment_to_db(session, mollie_json, idem_key, payload.metadata)

    return CreatePaymentOut(
        mollie_id=mollie_json.get("id"),
        checkout_url=mollie_json.get("_links", {}).get("checkout", {}).get("href"),
        status=mollie_json.get("status", "open"),
    )

@router.get("/status/{mollie_id}", response_model=PaymentStatusOut, dependencies=[Depends(require_service_api_key)])
async def payment_status(mollie_id: str):
    """Get the latest status for a given Mollie payment id."""
    # first, call Mollie to be sure data is fresh
    try:
        mollie_json = await get_mollie_payment(mollie_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    out = PaymentStatusOut(
        mollie_id = mollie_json.get("id"),
        status = mollie_json.get("status"),
        amount = mollie_json.get("amount"),
        description = mollie_json.get("description"),
        checkout_url = mollie_json.get("_links", {}).get("checkout", {}).get("href"),
        raw = mollie_json
    )

    # update local DB if present
    async with async_session() as session:
        q = select(Payment).where(Payment.mollie_id == mollie_id)
        res = await session.exec(q)
        found = res.one_or_none()
        if found:
            found.status = mollie_json.get("status", found.status)
            found.updated_at = datetime.utcnow()
            await session.commit()

    return out

# Webhook (Mollie -> POST)
@router.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Mollie will POST a small payload containing 'id' (mollie payment id).
    We fetch payment details from Mollie to confirm and update our DB.
    """
    payload = await request.json()
    mollie_id = payload.get("id")
    if not mollie_id:
        raise HTTPException(status_code=400, detail="Missing id in webhook payload")

    # schedule background update (fast response to Mollie)
    background_tasks.add_task(handle_webhook_update, mollie_id)
    return {"status": "accepted"}

async def handle_webhook_update(mollie_id: str):
    try:
        mollie_json = await get_mollie_payment(mollie_id)
    except Exception:
        # log failure (left simple here)
        return

    # update or create local record
    async with async_session() as session:
        # try to find by mollie_id
        q = select(Payment).where(Payment.mollie_id == mollie_id)
        res = await session.exec(q)
        found = res.one_or_none()
        if found:
            found.status = mollie_json.get("status", found.status)
            found.updated_at = datetime.utcnow()
            await session.commit()
        else:
            # Create bare record
            try:
                amount = mollie_json.get("amount", {}).get("value")
                amount_f = float(amount) if amount else 0.0
            except:
                amount_f = 0.0
            new = Payment(
                mollie_id=mollie_json.get("id"),
                amount=amount_f,
                currency=mollie_json.get("amount", {}).get("currency", "EUR"),
                description=mollie_json.get("description"),
                status=mollie_json.get("status", "open"),
                checkout_url=mollie_json.get("_links", {}).get("checkout", {}).get("href"),
                payment_metadata=None,
            )
            session.add(new)
            await session.commit()

