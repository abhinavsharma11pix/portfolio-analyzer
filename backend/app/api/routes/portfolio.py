import logging
import time
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, BackgroundTasks
from fastapi.responses import ORJSONResponse

from app.ingestion.factory import IngesterFactory
from app.services.stock_service import enrich_portfolio
from app.services.risk_service import calculate_risk_metrics
from app.services.insights_engine import generate_rule_insights
from app.services.ml_insights import calculate_portfolio_score, detect_correlated_stocks
from app.services.llm_service import generate_llm_summary
from app.services.prediction_service import generate_prediction
from app.services.template_generator import generate_template
from app.services.instrument_service import sync_prices_to_master
from app.db.repositories import HoldingsRepository, MetricSnapshotRepository
from app.cache import store as cache
from app.cache.symbol_cache import is_delisted

logger        = logging.getLogger(__name__)
router        = APIRouter(default_response_class=ORJSONResponse)
holdings_repo = HoldingsRepository()
snapshot_repo = MetricSnapshotRepository()

MAX_FILE_MB  = 10
MAX_HOLDINGS = 100


@router.post("/upload")
async def upload_portfolio(
    file:             UploadFile       = File(...),
    source:           str              = Query(default="auto"),
    background_tasks: BackgroundTasks  = None,
):
    t0    = time.monotonic()
    fname = (file.filename or "").lower()

    if not any(fname.endswith(e) for e in (".csv", ".xlsx", ".xls", ".pdf")):
        raise HTTPException(400, "Only CSV, Excel, or PDF files allowed")

    contents = await file.read()
    if len(contents) / (1024 * 1024) > MAX_FILE_MB:
        raise HTTPException(400, f"File too large. Max {MAX_FILE_MB}MB")

    source_type = (
        IngesterFactory.detect_source(file.filename or "", contents)
        if source == "auto" else source
    )

    ingester = IngesterFactory.get(source_type)
    try:
        result = ingester.process(contents)
    except Exception as e:
        raise HTTPException(422, f"Parse failed: {e}")

    holdings = result.get("holdings", [])
    if not holdings:
        raise HTTPException(422, "No valid holdings found")

    valid    = [h for h in holdings if not is_delisted(h["symbol"])]
    delisted = [h for h in holdings if is_delisted(h["symbol"])]

    if not valid:
        raise HTTPException(422, "All symbols appear delisted or unavailable")

    valid    = valid[:MAX_HOLDINGS]
    enriched = enrich_portfolio(valid)

    def _bg_save():
        try:
            holdings_repo.upsert(enriched["holdings"])
            sync_prices_to_master(enriched["holdings"])
        except Exception as e:
            logger.warning(f"Background save failed: {e}")

    if background_tasks:
        background_tasks.add_task(_bg_save)
    else:
        _bg_save()

    validation = result.get("validation", {})
    if delisted:
        validation["warnings"] = (validation.get("warnings") or []) + [
            f"Skipped (unavailable): {h['symbol']}" for h in delisted
        ]

    elapsed = round((time.monotonic() - t0) * 1000)
    logger.info(f"Upload done: {len(valid)} holdings in {elapsed}ms")

    return {
        "message":        "Portfolio uploaded successfully",
        "source":         source_type,
        "total_holdings": len(valid),
        "holdings":       enriched["holdings"],
        "summary":        enriched["summary"],
        "validation":     validation,
        "elapsed_ms":     elapsed,
    }


@router.get("/template")
def download_template():
    return generate_template()


@router.post("/risk")
async def get_risk(payload: dict):
    holdings = payload.get("holdings", [])
    if not holdings:
        raise HTTPException(400, "No holdings")

    key    = cache.make_portfolio_key("risk", holdings)
    cached = cache.get(key, cache.TTL_ANALYTICS)
    if cached:
        return ORJSONResponse(cached)

    result = calculate_risk_metrics(holdings)
    cache.set(key, result, cache.TTL_ANALYTICS)
    return ORJSONResponse(result)


@router.post("/insights")
async def get_insights(payload: dict):
    holdings = payload.get("holdings", [])
    risk     = payload.get("risk_metrics", {})
    summary  = payload.get("summary", {})
    if not holdings:
        raise HTTPException(400, "No holdings")

    key    = cache.make_portfolio_key("insights", holdings, risk)
    cached = cache.get(key, cache.TTL_ANALYTICS)
    if cached:
        return ORJSONResponse(cached)

    score      = calculate_portfolio_score(holdings, risk)
    correlated = detect_correlated_stocks(holdings)
    rules      = generate_rule_insights(holdings, summary, risk)
    llm        = generate_llm_summary(holdings, risk, rules, score)

    result = {
        "portfolio_score":   score,
        "llm_summary":       llm,
        "insights":          rules,
        "correlated_groups": correlated,
    }
    cache.set(key, result, cache.TTL_ANALYTICS)
    return ORJSONResponse(result)


@router.post("/decisions")
async def get_decisions(payload: dict):
    from app.ai.decision_engine import generate_decisions
    from app.ai.explainer import generate_decision_explanation

    holdings         = payload.get("holdings", [])
    risk_metrics     = payload.get("risk_metrics", {})
    advanced_metrics = payload.get("advanced_metrics", {})
    predictions      = payload.get("predictions", {})
    summary          = payload.get("summary", {})

    if not holdings:
        raise HTTPException(400, "No holdings")

    key    = cache.make_portfolio_key("decisions", holdings, risk_metrics)
    cached = cache.get(key, cache.TTL_ANALYTICS)
    if cached:
        return ORJSONResponse(cached)

    decisions   = generate_decisions(
        holdings=holdings, risk_metrics=risk_metrics,
        advanced_metrics=advanced_metrics,
        predictions=predictions, summary=summary,
    )
    score       = calculate_portfolio_score(holdings, risk_metrics)
    explanation = generate_decision_explanation(
        [d.to_dict() for d in decisions], score, risk_metrics
    )

    critical = [d.to_dict() for d in decisions if d.priority == 1]
    high     = [d.to_dict() for d in decisions if d.priority == 2]
    medium   = [d.to_dict() for d in decisions if d.priority == 3]
    low      = [d.to_dict() for d in decisions if d.priority == 4]

    result = {
        "explanation":     explanation,
        "portfolio_score": score,
        "total_decisions": len(decisions),
        "decisions":       {"critical": critical, "high": high, "medium": medium, "low": low},
        "all_decisions":   [d.to_dict() for d in decisions],
        "summary": {
            "critical_count":  len(critical),
            "high_count":      len(high),
            "medium_count":    len(medium),
            "low_count":       len(low),
            "action_required": len(critical) + len(high) > 0,
        },
    }
    cache.set(key, result, cache.TTL_ANALYTICS)
    return ORJSONResponse(result)


@router.get("/predict/{symbol}")
async def predict(symbol: str):
    symbol = symbol.upper().strip()
    if is_delisted(symbol):
        raise HTTPException(422, f"{symbol} appears delisted")

    key    = f"prediction:{symbol}:30"
    cached = cache.get(key, cache.TTL_PREDICTION, disk=True)
    if cached:
        return ORJSONResponse({**cached, "from_cache": True})

    result = generate_prediction(symbol)
    if "error" in result:
        raise HTTPException(422, result["error"])

    cache.set(key, result, cache.TTL_PREDICTION, disk=True)
    return ORJSONResponse(result)


@router.get("/history")
async def get_history(portfolio_id: str = "default", days: int = 30):
    return {"snapshots": snapshot_repo.get_snapshots(portfolio_id, days), "days": days}


@router.get("/instruments/search")
async def search_instruments(q: str = Query(..., min_length=1)):
    from app.services.instrument_service import search_instruments as si
    return {"results": si(q), "query": q}


@router.get("/aliases")
async def get_aliases(limit: int = 50):
    from app.core.database import get_connection
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT raw_input, resolved_symbol, confidence, use_count "
            "FROM symbol_aliases ORDER BY use_count DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return {"aliases": [dict(r) for r in rows]}
    finally:
        conn.close()