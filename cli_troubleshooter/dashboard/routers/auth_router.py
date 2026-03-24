from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from cli_troubleshooter.auth import create_token, _get_credentials

router = APIRouter(tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/auth/login")
async def login(payload: LoginRequest):
    username, password = _get_credentials()
    if payload.username != username or payload.password != password:
        raise HTTPException(status_code=401, detail="Nieprawidłowy login lub hasło")
    token = create_token(payload.username)
    return {"access_token": token, "token_type": "bearer", "username": payload.username}

@router.get("/auth/me")
async def me(credentials=None):
    import os
    from fastapi import Depends
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from cli_troubleshooter.auth import verify_token, security
    return {"auth_required": bool(os.getenv("CT_USERNAME"))}
