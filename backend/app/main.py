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
import os
from app.core.config import CORS_ORIGINS
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded





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

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
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
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return ORJSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Routers ──────────────────────────────────────────────────
from app.api.routes.portfolio      import router as portfolio_router
from app.api.routes.analytics      import router as analytics_router
from app.api.routes.websocket      import router as ws_router
from app.api.routes.recommendation import router as rec_router
from app.api.routes.auth           import router as auth_router
from app.api.routes.portfolios     import router as portfolios_router
from app.api.routes.fundamentals   import router as fund_router
from app.api.routes.alerts         import router as alerts_router
from app.api.routes.tax            import router as tax_router
from app.api.routes.reports import router as reports_router
from app.api.routes.alerts  import router as alerts_router
from app.api.routes.tax     import router as tax_router


app.include_router(portfolio_router,   prefix="/api/portfolio",      tags=["Portfolio"])
app.include_router(analytics_router,   prefix="/api/analytics",      tags=["Analytics"])
app.include_router(rec_router,         prefix="/api/recommendation", tags=["Recommendation"])
app.include_router(auth_router,        prefix="/api/auth",           tags=["Auth"])
app.include_router(portfolios_router,  prefix="/api/portfolios",     tags=["Portfolios"])
app.include_router(fund_router,        prefix="/api/fundamentals",   tags=["Fundamentals"])
app.include_router(ws_router,                                         tags=["WebSocket"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(tax_router,    prefix="/api/tax",    tags=["Tax"])
app.include_router(reports_router, prefix="/api/reports", tags=["Reports"])
app.include_router(alerts_router,  prefix="/api/alerts",  tags=["Alerts"])
app.include_router(tax_router,     prefix="/api/tax",     tags=["Tax"])
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/")
def root():
    return {"name": settings.app_name, "version": settings.app_version, "status": "ok"}


@app.get("/health")
def health():
    from app.cache.store import stats
    return {"status": "healthy", "cache": stats(),  "version": "5.0.0"}


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