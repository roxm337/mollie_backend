from fastapi import Header, HTTPException
from typing import Optional
from .config import settings

def require_service_api_key(x_api_key: Optional[str] = Header(default=None)):
    if x_api_key != settings.service_api_key:
        raise HTTPException(status_code=401, detail="Invalid X-API-KEY")
    return True

