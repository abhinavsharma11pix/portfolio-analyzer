import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.ingestion.factory import IngesterFactory
from app.services.stock_service import enrich_portfolio
from app.services.risk_service import calculate_risk_metrics
from app.services.insights_engine import generate_rule_insights
from app.services.ml_insights import (
    calculate_portfolio_score, detect_correlated_stocks
)
from app.services.llm_service import generate_llm_summary
from app.services.prediction_service import generate_prediction
from app.services.template_generator import generate_template
from app.services.instrument_service import sync_prices_to_master
from app.db.repositories import (
    HoldingsRepository,
    MetricSnapshotRepository
)
from app.core import cache as price_cache

logger = logging.getLogger(__name__)
router = APIRouter()

holdings_repo = HoldingsRepository()
snapshot_repo = MetricSnapshotRepository()

MAX_FILE_SIZE_MB = 5
MAX_HOLDINGS = 50


@router.post("/upload")
async def upload_portfolio(
    file: UploadFile = File(...),
    source: str = Query(default="auto")
):
    fname = file.filename.lower()
    allowed = (".csv", ".xlsx", ".xls", ".pdf")
    if not any(fname.endswith(ext) for ext in allowed):
        raise HTTPException(
            status_code=400,
            detail="Only CSV, Excel or PDF files allowed"
        )

    contents = await file.read()

    if len(contents) / (1024 * 1024) > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max {MAX_FILE_SIZE_MB}MB"
        )

    source_type = (
        IngesterFactory.detect_source(file.filename, contents)
        if source == "auto" else source
    )
    logger.info(f"Detected source: {source_type}")

    ingester = IngesterFactory.get(source_type)
    try:
        result = ingester.process(contents)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse file: {str(e)}"
        )

    holdings = result["holdings"]
    if not holdings:
        raise HTTPException(
            status_code=422,
            detail=f"No valid holdings found. {result['validation']['errors']}"
        )

    if len(holdings) > MAX_HOLDINGS:
        raise HTTPException(
            status_code=422,
            detail=f"Too many holdings. Max {MAX_HOLDINGS}."
        )

    enriched = enrich_portfolio(holdings)

    holdings_repo.upsert(enriched["holdings"])

    for h in enriched["holdings"]:
        if h.get("current_price"):
            price_cache.set_price(
                h["symbol"],
                h["current_price"],
                h.get("currency", "INR")
            )

    sync_prices_to_master(enriched["holdings"])

    logger.info(f"Upload complete: {len(holdings)} holdings from {source_type}")

    return {
        "message": "Portfolio uploaded successfully",
        "source": source_type,
        "total_holdings": len(holdings),
        "holdings": enriched["holdings"],
        "summary": enriched["summary"],
        "validation": result["validation"],
    }


@router.get("/template")
def download_template():
    return generate_template()


@router.post("/risk")
async def get_risk_metrics(payload: dict):
    holdings = payload.get("holdings", [])
    if not holdings:
        raise HTTPException(status_code=400, detail="No holdings provided")
    return calculate_risk_metrics(holdings)


@router.post("/insights")
async def get_insights(payload: dict):
    holdings = payload.get("holdings", [])
    risk     = payload.get("risk_metrics", {})
    summary  = payload.get("summary", {})

    if not holdings:
        raise HTTPException(status_code=400, detail="No holdings provided")

    rule_insights   = generate_rule_insights(holdings, summary, risk)
    portfolio_score = calculate_portfolio_score(holdings, risk)
    correlated      = detect_correlated_stocks(holdings)
    llm_summary     = generate_llm_summary(
        holdings, risk, rule_insights, portfolio_score
    )

    return {
        "portfolio_score": portfolio_score,
        "llm_summary":     llm_summary,
        "insights":        rule_insights,
        "correlated_groups": correlated,
    }


@router.get("/predict/{symbol}")
async def predict_stock(symbol: str):
    symbol = symbol.upper().strip()
    result = generate_prediction(symbol)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


@router.get("/history")
async def get_history(
    portfolio_id: str = "default",
    days: int = 30
):
    snapshots = snapshot_repo.get_snapshots(portfolio_id, days)
    return {"snapshots": snapshots, "days": days}


@router.get("/instruments/search")
async def search_instruments(q: str = Query(..., min_length=1)):
    from app.services.instrument_service import search_instruments
    results = search_instruments(q)
    return {"results": results, "query": q}


@router.get("/aliases")
async def get_symbol_aliases(limit: int = 50):
    from app.core.database import get_connection
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT raw_input, resolved_symbol,
                   confidence, source, use_count
            FROM symbol_aliases
            ORDER BY use_count DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return {"aliases": [dict(r) for r in rows]}
    finally:
        conn.close()