"""Wire all API routers."""

from fastapi import APIRouter
from .generate import router as generate_router
from .status import router as status_router

api_router = APIRouter()
api_router.include_router(generate_router, tags=["generate"])
api_router.include_router(status_router, tags=["status"])
