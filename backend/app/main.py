import asyncio
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
from app.core.config import get_settings
from app.db.migrations import run_migrations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger   = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 {settings.app_name} v{settings.app_version}")
    run_migrations()
    logger.info("✅ DB ready")

    from app.core.price_broadcaster import broadcast_loop
    task = asyncio.create_task(broadcast_loop())
    logger.info("✅ Broadcaster started")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("✅ Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    t0       = time.monotonic()
    response = await call_next(request)
    elapsed  = round((time.monotonic() - t0) * 1000)
    response.headers["X-Response-Time"] = f"{elapsed}ms"
    if elapsed > 5000:
        logger.warning(f"SLOW: {request.method} {request.url.path} {elapsed}ms")
    else:
        logger.info(f"{request.method} {request.url.path} → {response.status_code} {elapsed}ms")
    return response


@app.exception_handler(Exception)
async def global_error(request: Request, exc: Exception):
    logger.error(f"Error on {request.url.path}: {exc}", exc_info=True)
    return ORJSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# ── Routers ────────────────────────────────────────────────────
from app.api.routes import portfolio
from app.api.routes.analytics import router as analytics_router
from app.api.routes.websocket import router as ws_router
from app.api.routes.recommendation import router as rec_router

app.include_router(portfolio.router,  prefix="/api/portfolio",       tags=["Portfolio"])
app.include_router(analytics_router,  prefix="/api/analytics",       tags=["Analytics"])
app.include_router(rec_router,        prefix="/api/recommendation",  tags=["Recommendation"])
app.include_router(ws_router,                                         tags=["WebSocket"])


# ── Health endpoints ───────────────────────────────────────────
@app.get("/")
def root():
    return {
        "name":    settings.app_name,
        "version": settings.app_version,
        "status":  "ok",
    }


@app.get("/health")
def health():
    from app.cache.store import stats
    return {"status": "healthy", "cache": stats()}


@app.get("/api/db/status")
def db_status():
    from app.core.database import get_connection
    try:
        conn   = get_connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        conn.close()
        return {"status": "connected", "tables": [t["name"] for t in tables]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/api/market/status")
def market_status():
    from app.core.market_calendar import market_status as ms
    return ms()


@app.get("/api/connections")
def connections():
    from app.core.connection_manager import manager
    return {"active": manager.active_count}


@app.get("/api/cache/stats")
def cache_stats():
    from app.cache.store import stats
    return stats()


@app.delete("/api/cache/clear")
def cache_clear():
    from app.cache.store import _l1, _disk
    _l1.clear()
    try:
        _disk.clear()
    except Exception:
        pass
    return {"cleared": True}