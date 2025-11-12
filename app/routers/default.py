from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer

router = APIRouter()
oauth2_scheme = HTTPBearer()


@router.get("/health")
async def health():
    return {"status": "ok"}