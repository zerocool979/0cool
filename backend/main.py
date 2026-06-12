import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import NmapSLMException

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown events."""
    # Startup
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting...")

    # Ensure reports directory exists
    Path(settings.REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Reports directory: {settings.REPORTS_DIR}")

    # Check Ollama availability
    from app.services.ollama_service import check_ollama_health
    health = await check_ollama_health()
    if health["status"] == "ok":
        logger.info(f"✅ Ollama connected. Available models: {health.get('models', [])}")
        if not health.get("model_available"):
            logger.warning(
                f"⚠️  Model '{settings.OLLAMA_MODEL}' not found. "
                f"Run: ollama pull {settings.OLLAMA_MODEL}"
            )
    else:
        logger.warning("⚠️  Ollama not available. AI features will be limited.")

    yield

    # Shutdown
    logger.info("👋 Shutting down NmapSLM...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## NmapSLM - Network Scanner with AI Analysis

Aplikasi terintegrasi untuk:
- 🔍 **Network Scanning** dengan Nmap
- 🤖 **AI Analysis** menggunakan Ollama (100% offline)
- 📊 **Risk Assessment** otomatis
- 📄 **Report Generation** (PDF, Markdown, JSON)

### Peringatan Hukum
Scanning jaringan tanpa izin melanggar UU ITE Pasal 30. 
Gunakan hanya pada jaringan yang Anda miliki atau memiliki izin.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(NmapSLMException)
async def nmap_slm_exception_handler(request: Request, exc: NmapSLMException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "type": type(exc).__name__}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": "InternalError"}
    )


# Include routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "api": "/api/v1"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    from app.services.ollama_service import check_ollama_health
    ollama = await check_ollama_health()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "ollama": ollama,
        "model": settings.OLLAMA_MODEL,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
