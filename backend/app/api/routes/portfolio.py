import io
import logging
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.stock_service import enrich_portfolio
from app.services.risk_service import calculate_risk_metrics
from app.services.insights_engine import generate_rule_insights
from app.services.ml_insights import calculate_portfolio_score, detect_correlated_stocks
from app.services.llm_service import generate_llm_summary
from app.services.prediction_service import generate_prediction

logger = logging.getLogger(__name__)
router = APIRouter()

REQUIRED_COLUMNS = {"symbol", "quantity", "avg_buy_price"}
MAX_FILE_SIZE_MB = 5
MAX_HOLDINGS = 50


def parse_dataframe(contents: bytes, filename: str) -> pd.DataFrame:
    """Parse CSV or Excel file into DataFrame with encoding fallback."""
    if filename.endswith(".csv"):
        for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                return pd.read_csv(io.StringIO(contents.decode(encoding)))
            except (UnicodeDecodeError, Exception):
                continue
        raise ValueError("Could not decode CSV file. Please save as UTF-8.")
    else:
        return pd.read_excel(io.BytesIO(contents))


def validate_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Validate columns, clean data, return sanitized DataFrame."""
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}. Required: symbol, quantity, avg_buy_price")

    df = df[list(REQUIRED_COLUMNS | ({"sector"} & set(df.columns)))].copy()
    df = df.dropna(subset=["symbol", "quantity", "avg_buy_price"])

    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["avg_buy_price"] = pd.to_numeric(df["avg_buy_price"], errors="coerce")
    df = df.dropna(subset=["quantity", "avg_buy_price"])
    df = df[(df["quantity"] > 0) & (df["avg_buy_price"] > 0)]

    if "sector" in df.columns:
        df["sector"] = df["sector"].astype(str).str.strip().str.title()

    return df


@router.post("/upload") 
async def upload_portfolio(file: UploadFile = File(...)):
    # File type check
    allowed = (".csv", ".xlsx", ".xls")
    if not any(file.filename.lower().endswith(ext) for ext in allowed):
        raise HTTPException(status_code=400, detail="Only CSV or Excel files (.csv, .xlsx, .xls) allowed")

    contents = await file.read()

    # File size check
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File too large. Max size is {MAX_FILE_SIZE_MB}MB")

    try:
        df = parse_dataframe(contents, file.filename.lower())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File parse error: {e}")
        raise HTTPException(status_code=400, detail="Could not parse file. Check format and try again.")

    try:
        df = validate_and_clean(df)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if len(df) == 0:
        raise HTTPException(status_code=422, detail="No valid holdings found after cleaning.")

    if len(df) > MAX_HOLDINGS:
        raise HTTPException(status_code=422, detail=f"Too many holdings. Max is {MAX_HOLDINGS}.")

    holdings = df.to_dict(orient="records")
    logger.info(f"Portfolio uploaded: {len(holdings)} holdings from {file.filename}")

    result = enrich_portfolio(holdings)

    return {
        "message": "Portfolio uploaded successfully",
        "total_holdings": len(holdings),
        "holdings": result["holdings"],
        "summary": result["summary"]
    }


@router.post("/risk")
async def get_risk_metrics(payload: dict):
    holdings = payload.get("holdings", [])
    if not holdings:
        raise HTTPException(status_code=400, detail="No holdings provided")
    if len(holdings) > MAX_HOLDINGS:
        raise HTTPException(status_code=400, detail="Too many holdings")

    logger.info(f"Risk metrics requested for {len(holdings)} holdings")
    metrics = calculate_risk_metrics(holdings)
    return metrics


@router.post("/insights")
async def get_insights(payload: dict):
    holdings = payload.get("holdings", [])
    risk_metrics = payload.get("risk_metrics", {})
    summary = payload.get("summary", {})

    if not holdings:
        raise HTTPException(status_code=400, detail="No holdings provided")

    # Layer 1 — Rules (free)
    rule_insights = generate_rule_insights(holdings, summary, risk_metrics)

    # Layer 2 — ML scoring (free)
    portfolio_score = calculate_portfolio_score(holdings, risk_metrics)
    correlated = detect_correlated_stocks(holdings)

    # Layer 3 — LLM summary (Groq, free tier)
    llm_summary = generate_llm_summary(holdings, risk_metrics, rule_insights, portfolio_score)

    return {
        "portfolio_score": portfolio_score,
        "llm_summary": llm_summary,
        "insights": rule_insights,
        "correlated_groups": correlated
    }
    

@router.get("/predict/{symbol}")
async def predict_stock(symbol: str):
    """Generate 30-day price prediction for a stock symbol."""
    symbol = symbol.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol required")

    logger.info(f"Prediction requested for {symbol}")
    result = generate_prediction(symbol)

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    return result