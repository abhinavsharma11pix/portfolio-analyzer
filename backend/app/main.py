import asyncio
import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import portfolio
from app.db.migrations import run_migrations
from app.core.market_calendar import market_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Portfolio Analyzer",
    description="Hedge-fund grade portfolio analysis",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    logger.info("🚀 Starting AI Portfolio Analyzer v3...")
    run_migrations()
    logger.info("✅ Database ready")

    # Import here to avoid circular imports
    from app.core.price_broadcaster import broadcast_loop
    asyncio.create_task(broadcast_loop())
    logger.info("✅ WebSocket price broadcaster started")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round(time.time() - start, 3)
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} ({duration}s)"
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# HTTP routes
app.include_router(
    portfolio.router,
    prefix="/api/portfolio",
    tags=["Portfolio"]
)

# WebSocket route
from app.api.routes.websocket import router as ws_router
app.include_router(ws_router, tags=["WebSocket"])


@app.get("/")
def root():
    return {"message": "AI Portfolio Analyzer API 🚀", "version": "3.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/db/status")
def db_status():
    from app.core.database import get_connection
    try:
        conn = get_connection()
        tables = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' ORDER BY name
        """).fetchall()
        conn.close()
        return {"status": "connected", "tables": [t["name"] for t in tables]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/api/market/status")
def get_market_status():
    return market_status()


@app.get("/api/connections")
def get_connections():
    from app.core.connection_manager import manager
    return {
        "active_connections": manager.active_count,
        "has_active": manager.has_active,
    }