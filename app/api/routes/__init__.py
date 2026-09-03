from fastapi import APIRouter
from app.api.routes import tenants

api_router = APIRouter()
api_router.include_router(tenants.router)