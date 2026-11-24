"""
app/main.py
Titik masuk aplikasi FastAPI RapiInDoc.
"""

from __future__ import annotations

import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes_presets import router as presets_router
from app.api.routes_rules import router as rules_router
from app.api.routes_session import router as session_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.services.file_manager import file_manager
from app.services.session_store import session_store


# ============================================================
# Lifespan (startup / shutdown)
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(debug=settings.debug)
    logger.info("startup", env=settings.app_env, version=settings.app_version)

    # Mulai pembersih terjadwal (setiap 5 menit)
    stop_event = threading.Event()
    def _cleaner():
        while not stop_event.is_set():
            try:
                n_files = file_manager.purge_expired()
                n_sessions = session_store.purge_expired()
                if n_files or n_sessions:
                    logger.info("purge", files=n_files, sessions=n_sessions)
            except Exception as e:
                logger.error("purge_error", error=str(e))
            stop_event.wait(timeout=300)  # 5 menit

    cleaner_thread = threading.Thread(target=_cleaner, daemon=True, name="cleaner")
    cleaner_thread.start()

    yield  # Aplikasi berjalan

    stop_event.set()
    logger.info("shutdown")


# ============================================================
# Aplikasi
# ============================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Backend RapiInDoc – perapian dokumen akademik otomatis.\n\n"
        "Tidak ada data pengguna atau dokumen yang disimpan permanen."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ----- CORS -----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----- Rate Limiting sederhana (in-process) -----
_rate_buckets: dict[str, list[float]] = {}
_rate_lock = threading.Lock()

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Hanya upload dan job creation yang dibatasi
    if request.url.path.endswith("/upload") or request.url.path.endswith("/jobs"):
        ip = request.client.host if request.client else "unknown"
        limit = settings.rate_limit_upload
        now = time.time()
        window = 60.0  # 1 menit

        with _rate_lock:
            timestamps = _rate_buckets.get(ip, [])
            timestamps = [t for t in timestamps if now - t < window]
            if len(timestamps) >= limit:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Terlalu banyak permintaan. Coba lagi nanti."},
                )
            timestamps.append(now)
            _rate_buckets[ip] = timestamps

    return await call_next(request)


# ----- Global Exception Handler -----
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_error", path=request.url.path, error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Terjadi kesalahan internal. Silakan coba lagi."},
    )


# ----- Router -----
app.include_router(session_router)
app.include_router(presets_router)
app.include_router(rules_router)


# ----- Health Check -----
@app.get("/health", tags=["system"])
def health_check():
    return {
        "status": "ok",
        "version": settings.app_version,
        "env": settings.app_env,
    }


@app.get("/", tags=["system"])
def root():
    return {
        "message": "RapiInDoc API",
        "docs": "/docs",
        "version": settings.app_version,
    }
