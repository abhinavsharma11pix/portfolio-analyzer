"""
Fetches real stock lists from free public sources.
NSE: uses NSE India public API (no auth needed)
US: uses Wikipedia S&P 500 list
"""
import logging
import requests
import pandas as pd
from typing import Dict, List
from app.cache import store as cache

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    ),
    "Referer": "https://www.nseindia.com/",
    "Accept":  "application/json",
}

# Sector mapping from NSE industry names → our labels
NSE_SECTOR_MAP = {
    "Information Technology":         "Technology",
    "IT - Software":                  "Technology",
    "IT - Hardware":                  "Technology",
    "Computer Software":              "Technology",
    "Banks":                          "Banking",
    "Bank - Private":                 "Banking",
    "Bank - Public":                  "Banking",
    "Finance":                        "Finance",
    "Finance - NBFCs":                "Finance",
    "Finance - Others":               "Finance",
    "Insurance":                      "Finance",
    "Pharmaceuticals":                "Healthcare",
    "Pharmaceuticals & Biotechnology":"Healthcare",
    "Healthcare":                     "Healthcare",
    "Hospitals & Medical Services":   "Healthcare",
    "FMCG":                           "FMCG",
    "Consumer Goods":                 "FMCG",
    "Consumer Non Durables":          "FMCG",
    "Oil & Gas":                      "Energy",
    "Oil":                            "Energy",
    "Gas":                            "Energy",
    "Power":                          "Energy",
    "Utilities":                      "Energy",
    "Automobile":                     "Auto",
    "Auto Ancillaries":               "Auto",
    "Cement":                         "Infra",
    "Construction":                   "Infra",
    "Infrastructure":                 "Infra",
    "Capital Goods":                  "Infra",
    "Consumer Durables":              "Consumer",
    "Retail":                         "Consumer",
    "Chemicals":                      "Consumer",
    "Realty":                         "Infra",
    "Metals":                         "Metals",
    "Mining":                         "Metals",
    "Steel":                          "Metals",
    "Media":                          "Media",
    "Telecom":                        "Telecom",
    "Defence":                        "Defense",
    "Aerospace & Defence":            "Defense",
    "Fertilisers":                    "FMCG",
    "Textiles":                       "Consumer",
    "Diversified":                    "Diversified",
}

US_SECTOR_MAP = {
    "Information Technology":    "Technology",
    "Technology":                "Technology",
    "Financials":                "Finance",
    "Financial Services":        "Finance",
    "Health Care":               "Healthcare",
    "Consumer Discretionary":    "Consumer",
    "Consumer Staples":          "FMCG",
    "Energy":                    "Energy",
    "Industrials":               "Infra",
    "Materials":                 "Metals",
    "Real Estate":               "Infra",
    "Utilities":                 "Energy",
    "Communication Services":    "Telecom",
}


def fetch_nse_all_stocks() -> List[Dict]:
    """
    Fetch all NSE-listed stocks from NSE India public API.
    Returns list of {symbol, name, sector, market_cap_category}
    """
    key    = "nse_universe_v2"
    cached = cache.get(key, 86400, disk=True)
    if cached:
        logger.info(f"NSE universe from cache: {len(cached)} stocks")
        return cached

    stocks = []

    # Try NSE equity list API
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=5)

        res = session.get(
            "https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O",
            headers=NSE_HEADERS, timeout=10
        )
        if res.status_code == 200:
            data  = res.json()
            items = data.get("data", [])
            for item in items:
                sym = item.get("symbol", "").strip()
                if sym:
                    stocks.append({
                        "symbol":   sym + ".NS",
                        "name":     item.get("meta", {}).get("companyName", sym),
                        "sector":   NSE_SECTOR_MAP.get(
                            item.get("meta", {}).get("industry", ""), "Other"
                        ),
                    })
    except Exception as e:
        logger.warning(f"NSE F&O API failed: {e}")

    # Fallback: Nifty 500 (broad coverage)
    if len(stocks) < 50:
        try:
            session = requests.Session()
            session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=5)

            for index in ["NIFTY 500", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250"]:
                res = session.get(
                    f"https://www.nseindia.com/api/equity-stockIndices?index={requests.utils.quote(index)}",
                    headers=NSE_HEADERS, timeout=10
                )
                if res.status_code == 200:
                    items = res.json().get("data", [])
                    seen  = {s["symbol"] for s in stocks}
                    for item in items:
                        sym = item.get("symbol", "").strip()
                        full = sym + ".NS"
                        if sym and full not in seen:
                            stocks.append({
                                "symbol": full,
                                "name":   item.get("meta", {}).get("companyName", sym),
                                "sector": NSE_SECTOR_MAP.get(
                                    item.get("meta", {}).get("industry", ""), "Other"
                                ),
                            })
                            seen.add(full)
        except Exception as e:
            logger.warning(f"Nifty index API failed: {e}")

    # Final fallback: CSV from NSE
    if len(stocks) < 50:
        stocks = _fallback_nse_csv()

    if stocks:
        cache.set(key, stocks, 86400, disk=True)
        logger.info(f"NSE universe loaded: {len(stocks)} stocks")
    return stocks


def _fallback_nse_csv() -> List[Dict]:
    """Download NSE equity list CSV."""
    try:
        url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=5)
        res = session.get(url, headers=NSE_HEADERS, timeout=15)
        if res.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(res.text))
            stocks = []
            for _, row in df.iterrows():
                sym = str(row.get("SYMBOL", "")).strip()
                if sym:
                    stocks.append({
                        "symbol": sym + ".NS",
                        "name":   str(row.get("NAME OF COMPANY", sym)),
                        "sector": "Other",
                    })
            logger.info(f"NSE CSV fallback: {len(stocks)} stocks")
            return stocks
    except Exception as e:
        logger.warning(f"NSE CSV fallback failed: {e}")
    return []


def fetch_sp500_stocks() -> List[Dict]:
    """Fetch S&P 500 constituents from Wikipedia."""
    key    = "sp500_universe_v2"
    cached = cache.get(key, 86400, disk=True)
    if cached:
        return cached

    try:
        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            attrs={"id": "constituents"}
        )
        df     = tables[0]
        stocks = []
        for _, row in df.iterrows():
            sym = str(row.get("Symbol", "")).strip().replace(".", "-")
            if sym:
                stocks.append({
                    "symbol": sym,
                    "name":   str(row.get("Security", sym)),
                    "sector": US_SECTOR_MAP.get(str(row.get("GICS Sector", "")), "Other"),
                })
        if stocks:
            cache.set(key, stocks, 86400, disk=True)
            logger.info(f"S&P 500 loaded: {len(stocks)} stocks")
            return stocks
    except Exception as e:
        logger.warning(f"S&P 500 Wikipedia fetch failed: {e}")

    # Fallback: Russell 1000 ETF holdings or hardcoded top 100
    return _us_fallback()


def _us_fallback() -> List[Dict]:
    """Broad US stock fallback if Wikipedia fails."""
    stocks = []
    base   = {
        "Technology":  ["AAPL","MSFT","GOOGL","NVDA","META","AMD","INTC","CRM","ORCL","IBM","CSCO","ADBE","QCOM","TXN"],
        "Finance":     ["JPM","BAC","GS","MS","WFC","C","BLK","AXP","V","MA","USB","PNC","TFC"],
        "Healthcare":  ["JNJ","PFE","ABBV","MRK","UNH","LLY","BMY","AMGN","GILD","CVS","CI","HUM","ISRG"],
        "Consumer":    ["AMZN","TSLA","NKE","SBUX","MCD","HD","LOW","TGT","COST","TJX","BKNG","HLT"],
        "Energy":      ["XOM","CVX","COP","SLB","OXY","PSX","VLO","MPC","HAL","BKR","EOG"],
        "Infra":       ["UNP","CAT","DE","EMR","GE","HON","MMM","RTX","LMT","NOC","BA"],
        "Metals":      ["NEM","FCX","AA","X","NUE","STLD","CLF"],
        "ETF":         ["SPY","QQQ","VTI","GLD","AGG","IWM","EFA","VEA"],
    }
    for sector, syms in base.items():
        for sym in syms:
            stocks.append({"symbol": sym, "name": sym, "sector": sector})
    return stocks


def get_universe(market: str) -> List[Dict]:
    """Get full stock universe for given market."""
    if market == "india":
        return fetch_nse_all_stocks()
    return fetch_sp500_stocks()


def filter_by_sectors(
    universe: List[Dict],
    sectors:  List[str],
) -> List[Dict]:
    """
    STRICT sector filter — only return stocks from requested sectors.
    If sectors empty, return full universe.
    """
    if not sectors:
        return universe
    sector_set = {s.lower() for s in sectors}
    filtered   = [s for s in universe if s.get("sector", "").lower() in sector_set]
    logger.info(f"Sector filter: {sectors} → {len(filtered)}/{len(universe)} stocks")
    return filtered