from fastapi import APIRouter
from src.interface.api.candidate_handler import router as candidate_router
from src.interface.api.recruiter_handler import router as recruiter_router
from src.interface.api.vision_handler import router as vision_router

api_router = APIRouter()

# Register sub-routers
api_router.include_router(candidate_router)
api_router.include_router(recruiter_router)
api_router.include_router(vision_router)

