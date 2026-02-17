from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..core.security import create_access_token, decode_access_token

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(payload: LoginRequest):
    # Dummy user validation for Step 3 — replace with proper lookup later
    if payload.username != "dev" or payload.password != "dev":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=payload.username)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
async def me(token: str | None = None):
    # Simple token introspection endpoint for development
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    payload = decode_access_token(token)
    return payload
