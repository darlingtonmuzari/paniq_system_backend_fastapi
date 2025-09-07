"""
Main API router for v1 endpoints
"""
from fastapi import APIRouter

# Import available routers
from app.api.v1.attestation import router as attestation_router
from app.api.v1.auth import router as auth_router
from app.api.v1.security_firms import router as security_firms_router
from app.api.v1.users import router as users_router
from app.api.v1.mobile_users import router as mobile_users_router
from app.api.v1.personnel import router as personnel_router
from app.api.v1.credits import router as credits_router
from app.api.v1.payments import router as payments_router
from app.api.v1.mobile_subscriptions import router as mobile_subscriptions_router
from app.api.v1.subscription_products import router as subscription_products_router

# Import routers when they're created
# from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.emergency import router as emergency_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.websocket import router as websocket_router
from app.api.v1.silent_mode import router as silent_mode_router
from app.api.v1.prank_detection import router as prank_detection_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.cache_management import router as cache_management_router
from app.api.v1.database_optimization import router as database_optimization_router
from app.api.v1.logs import router as logs_router
from app.api.v1.document_types import router as document_types_router
from app.api.v1.firm_applications import router as firm_applications_router
from app.api.v1.application_details import router as application_details_router

api_router = APIRouter()

# Include available routers
api_router.include_router(attestation_router, prefix="/attestation", tags=["attestation"])
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(security_firms_router, prefix="/security-firms", tags=["security-firms"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(mobile_users_router, prefix="/mobile/users", tags=["mobile-users"])
api_router.include_router(personnel_router, prefix="/personnel", tags=["personnel"])
api_router.include_router(credits_router, prefix="/credits", tags=["credits"])
api_router.include_router(payments_router, tags=["payments"])
api_router.include_router(mobile_subscriptions_router, prefix="/mobile/subscriptions", tags=["mobile-subscriptions"])
api_router.include_router(subscription_products_router, prefix="/subscription-products", tags=["subscription-products"])

# Include routers when they're created
# api_router.include_router(subscriptions_router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(emergency_router, prefix="/emergency", tags=["emergency"])
api_router.include_router(feedback_router, prefix="/feedback", tags=["feedback"])
api_router.include_router(websocket_router, tags=["websocket"])
api_router.include_router(silent_mode_router, prefix="/mobile/silent-mode", tags=["mobile-silent-mode"])
api_router.include_router(prank_detection_router, prefix="/admin", tags=["prank-detection"])
api_router.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
api_router.include_router(cache_management_router, prefix="/admin", tags=["cache-management"])
api_router.include_router(database_optimization_router, prefix="/admin", tags=["database-optimization"])
api_router.include_router(logs_router, prefix="/admin", tags=["log-management"])
api_router.include_router(document_types_router, prefix="/document-types", tags=["document-types"])
api_router.include_router(firm_applications_router, prefix="/firm-applications", tags=["firm-applications"])
api_router.include_router(application_details_router, prefix="/applications", tags=["application-details"])

@api_router.get("/")
async def root():
    return {"message": "Panic System Platform API v1"}