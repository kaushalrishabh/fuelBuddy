from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.entries import router as entries_router
from app.api.health import router as health_router
from app.api.odometer_events import router as odometer_events_router
from app.api.vehicles import router as vehicles_router
from app.core.config import get_settings
from app.core.csrf import CSRFHeaderMiddleware
from app.core.db import SessionLocal
from app.core.seed import seed_admin_user

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    db = SessionLocal()
    try:
        seed_admin_user(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="FuelBuddy API",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_dev else None,
    redoc_url="/redoc" if settings.is_dev else None,
    openapi_url="/openapi.json" if settings.is_dev else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CSRFHeaderMiddleware)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(vehicles_router, prefix="/api/vehicles", tags=["vehicles"])
app.include_router(entries_router, prefix="/api/vehicles/{vehicle_id}/entries", tags=["entries"])
app.include_router(
    odometer_events_router,
    prefix="/api/vehicles/{vehicle_id}/odometer-events",
    tags=["odometer-events"],
)
