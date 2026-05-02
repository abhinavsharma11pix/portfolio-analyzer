import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import portfolio
from app.db.migrations import run_migrations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Portfolio Analyzer",
    description="Hedge-fund grade portfolio analysis",
    version="2.0.0"
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
    """Initialize database on startup."""
    logger.info("🚀 Starting AI Portfolio Analyzer...")
    run_migrations()
    logger.info("✅ Database ready")

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

app.include_router(
    portfolio.router,
    prefix="/api/portfolio",
    tags=["Portfolio"]
)

@app.get("/")
def root():
    return {
        "message": "AI Portfolio Analyzer API 🚀",
        "version": "2.0.0"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/db/status")
def db_status():
    """Verify DB is working."""
    from app.core.database import get_connection
    try:
        conn = get_connection()
        tables = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """).fetchall()
        conn.close()
        return {
            "status": "connected",
            "tables": [t["name"] for t in tables],
            "db_path": "data/portfolio.db"
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}