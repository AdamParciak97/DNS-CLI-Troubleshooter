from __future__ import annotations
import os
import time
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import hmac
import hashlib
import json
import base64

security = HTTPBearer(auto_error=False)

def _get_secret() -> str:
    return os.getenv("CT_SECRET_KEY", "changeme-secret-key-12345")

def _get_credentials() -> tuple[str, str]:
    username = os.getenv("CT_USERNAME", "admin")
    password = os.getenv("CT_PASSWORD", "admin")
    return username, password

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _unb64(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * pad)

def create_token(username: str) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps({"sub": username, "iat": int(time.time()), "exp": int(time.time()) + 86400 * 7}).encode())
    sig = _b64(hmac.new(_get_secret().encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"

def verify_token(token: str) -> Optional[str]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, sig = parts
        expected_sig = _b64(hmac.new(_get_secret().encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected_sig):
            return None
        data = json.loads(_unb64(payload))
        if data.get("exp", 0) < time.time():
            return None
        return data.get("sub")
    except Exception:
        return None

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    # If auth is disabled (no CT_USERNAME set), allow all
    if not os.getenv("CT_USERNAME"):
        return "anonymous"
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Brak tokenu autoryzacji")
    username = verify_token(credentials.credentials)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nieprawidłowy lub wygasły token")
    return username
