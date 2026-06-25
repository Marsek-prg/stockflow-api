from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.products import router as products_router
from app.api.v1.stock import router as stock_router
from app.api.v1.warehouses import router as warehouses_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(products_router)
api_router.include_router(warehouses_router)
api_router.include_router(stock_router)
