# app/api/routes/__init__.py
from __future__ import annotations

from fastapi import APIRouter

from .trends import router as trends_router

api_router = APIRouter(prefix="/api")

# /api/trends/...
api_router.include_router(trends_router)
