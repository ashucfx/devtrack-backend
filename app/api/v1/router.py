from fastapi import APIRouter

from app.api.v1.routes.applications import router as applications_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.companies import router as companies_router
from app.api.v1.routes.users import router as users_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(companies_router)
api_v1_router.include_router(applications_router)
