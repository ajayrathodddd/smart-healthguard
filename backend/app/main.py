from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import connect_to_mongodb, close_mongodb_connection
from app.routes.medicine import router as medicine_router
from app.routes.voice import router as voice_router
from app.routes.medicine import router as medicine_router
from app.routes.voice import router as voice_router
from app.routes.ocr import router as ocr_router
from app.routes.ocr_analysis import router as ocr_analysis_router
from app.routes.risk import router as risk_router
from app.routes.ai_assistant import router as ai_assistant_router
from app.routes.history import router as history_router

from app.routes.auth import router as auth_router
from app.auth.service import ensure_auth_indexes
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongodb()
    await ensure_auth_indexes()

    yield

    await close_mongodb_connection()


app = FastAPI(
    title="AI-Powered Smart HealthGuard",
    description="Educational platform for medicine and product information analysis.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(medicine_router)
app.include_router(voice_router)
app.include_router(medicine_router)
app.include_router(voice_router)
app.include_router(ocr_router)
app.include_router(ocr_analysis_router)
app.include_router(risk_router)
app.include_router(ai_assistant_router)
app.include_router(history_router)
app.include_router(auth_router)
@app.get("/")
async def root():
    return {
        "message": "Smart HealthGuard API is running!",
        "project": "AI-Powered Smart HealthGuard",
        "status": "success",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
    }