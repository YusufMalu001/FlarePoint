from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.analytics.tracking import process_incidents
from app.api.routes import router
from app.core.config import settings
from app.pipelines.ingest import run_ingestion
from app.storage.database import Base, SessionLocal, engine
from app.storage.models import IncidentModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(IncidentModel).count() == 0 and settings.demo_mode:
            run_ingestion(db, day_range=3, force_demo=True)
            process_incidents(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="FlarePoint Geospatial Wildfire Intelligence API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)
