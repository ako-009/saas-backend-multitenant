from fastapi import APIRouter
from app.api.routes import tenants, auth

api_router = APIRouter()
api_router.include_router(tenants.router)
api_router.include_router(auth.router)