from fastapi import APIRouter

from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.applications import router as applications_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.companies import router as companies_router
from app.api.v1.routes.follow_ups import router as follow_ups_router
from app.api.v1.routes.interviews import router as interviews_router
from app.api.v1.routes.notes import router as notes_router
from app.api.v1.routes.users import router as users_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(companies_router)
api_v1_router.include_router(applications_router)
api_v1_router.include_router(interviews_router)
api_v1_router.include_router(notes_router)
api_v1_router.include_router(follow_ups_router)
api_v1_router.include_router(analytics_router)
