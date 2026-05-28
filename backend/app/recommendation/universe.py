"""
Fetches real stock lists from free public sources.
Fixed sector mapping to match user input exactly.
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

# Map NSE industry strings → our sector labels (lowercase for matching)
NSE_SECTOR_MAP = {
    "information technology":          "Technology",
    "it - software":                   "Technology",
    "it - hardware":                   "Technology",
    "computer software":               "Technology",
    "software":                        "Technology",
    "banks":                           "Banking",
    "bank - private":                  "Banking",
    "bank - public":                   "Banking",
    "banking":                         "Banking",
    "finance":                         "Finance",
    "finance - nbfcs":                 "Finance",
    "finance - others":                "Finance",
    "non banking financial company":   "Finance",
    "insurance":                       "Finance",
    "pharmaceuticals":                 "Healthcare",
    "pharmaceuticals & biotechnology": "Healthcare",
    "healthcare":                      "Healthcare",
    "hospital":                        "Healthcare",
    "hospitals & medical services":    "Healthcare",
    "fmcg":                            "FMCG",
    "consumer goods":                  "FMCG",
    "consumer non durables":           "FMCG",
    "food & beverages":                "FMCG",
    "beverages":                       "FMCG",
    "personal care":                   "FMCG",
    "oil & gas":                       "Energy",
    "oil":                             "Energy",
    "gas":                             "Energy",
    "power":                           "Energy",
    "utilities":                       "Energy",
    "petroleum products":              "Energy",
    "automobile":                      "Auto",
    "auto ancillaries":                "Auto",
    "auto":                            "Auto",
    "cement":                          "Infra",
    "construction":                    "Infra",
    "infrastructure":                  "Infra",
    "capital goods":                   "Infra",
    "realty":                          "Infra",
    "consumer durables":               "Consumer",
    "retail":                          "Consumer",
    "chemicals":                       "Consumer",
    "paints":                          "Consumer",
    "metals":                          "Metals",
    "mining":                          "Metals",
    "steel":                           "Metals",
    "iron & steel":                    "Metals",
    "media":                           "Media",
    "entertainment":                   "Media",
    "telecom":                         "Telecom",
    "telecommunications":              "Telecom",
    "defence":                         "Defense",
    "aerospace & defence":             "Defense",
    "fertilisers":                     "FMCG",
    "agrochemicals":                   "FMCG",
    "textiles":                        "Consumer",
    "trading":                         "Diversified",
    "diversified":                     "Diversified",
}

# Fallback hardcoded universe with CORRECT sectors
# Used when NSE API fails — these are liquid NSE stocks
HARDCODED_NSE = {
    "Technology": [
        "INFY.NS","TCS.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS",
        "MPHASIS.NS","LTIM.NS","PERSISTENT.NS","COFORGE.NS","TATAELXSI.NS",
    ],
    "Banking": [
        "HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS","SBIN.NS","AXISBANK.NS",
        "INDUSINDBK.NS","BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","PNB.NS",
    ],
    "Healthcare": [
        "SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","APOLLOHOSP.NS",
        "LUPIN.NS","AUROPHARMA.NS","TORNTPHARM.NS","ALKEM.NS","GLENMARK.NS",
    ],
    "FMCG": [
        "HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","BRITANNIA.NS","DABUR.NS",
        "MARICO.NS","GODREJCP.NS","COLPAL.NS","EMAMILTD.NS","TATACONSUM.NS",
    ],
    "Energy": [
        "RELIANCE.NS","ONGC.NS","NTPC.NS","POWERGRID.NS","TATAPOWER.NS",
        "BPCL.NS","IOC.NS","GAIL.NS","ADANIGREEN.NS","TORNTPOWER.NS",
    ],
    "Finance": [
        "BAJFINANCE.NS","BAJAJFINSV.NS","CHOLAFIN.NS","SBILIFE.NS","HDFCLIFE.NS",
        "MUTHOOTFIN.NS","LICHSGFIN.NS","M&MFIN.NS","MANAPPURAM.NS","ICICIGI.NS",
    ],
    "Auto": [
        "MARUTI.NS","M&M.NS","BAJAJ-AUTO.NS","HEROMOTOCO.NS","EICHERMOT.NS",
        "TATAMOTORS.NS","ASHOKLEY.NS","TVSMOTOR.NS","BALKRISIND.NS","MRF.NS",
    ],
    "Infra": [
        "LT.NS","ADANIPORTS.NS","ULTRACEMCO.NS","GRASIM.NS","SHREECEM.NS",
        "ACC.NS","AMBUJACEMENT.NS","BHARTIARTL.NS","DLF.NS","GODREJPROP.NS",
    ],
    "Consumer": [
        "ASIANPAINT.NS","TITAN.NS","PIDILITIND.NS","HAVELLS.NS","VOLTAS.NS",
        "WHIRLPOOL.NS","BLUEDART.NS","TRENT.NS","VMART.NS","PAGEIND.NS",
    ],
    "Pharma": [
        "LUPIN.NS","AUROPHARMA.NS","TORNTPHARM.NS","ALKEM.NS","GLENMARK.NS",
        "IPCALAB.NS","NATCOPHARM.NS","GRANULES.NS","LAURUS.NS","ABBOTINDIA.NS",
    ],
    "Metals": [
        "TATASTEEL.NS","JSWSTEEL.NS","HINDALCO.NS","VEDL.NS","COALINDIA.NS",
        "NMDC.NS","SAIL.NS","HINDZINC.NS","NATIONALUM.NS","MOIL.NS",
    ],
    "Defense": [
        "HAL.NS","BEL.NS","BHEL.NS","COCHINSHIP.NS","GRSE.NS",
    ],
    "IT": [
        "LTIM.NS","PERSISTENT.NS","COFORGE.NS","TATAELXSI.NS","KPITTECH.NS",
        "CYIENT.NS","HEXAWARE.NS","NIITTECH.NS","MINDTREE.NS","MPHASIS.NS",
    ],
    "Telecom": [
        "BHARTIARTL.NS","VODAIDEA.NS","TATACOMM.NS","ROUTE.NS","RAILTEL.NS",
    ],
}

US_SECTOR_MAP = {
    "Information Technology": "Technology",
    "Technology":             "Technology",
    "Financials":             "Finance",
    "Financial Services":     "Finance",
    "Health Care":            "Healthcare",
    "Consumer Discretionary": "Consumer",
    "Consumer Staples":       "FMCG",
    "Energy":                 "Energy",
    "Industrials":            "Infra",
    "Materials":              "Metals",
    "Real Estate":            "Infra",
    "Utilities":              "Energy",
    "Communication Services": "Telecom",
}


def fetch_nse_all_stocks() -> List[Dict]:
    """
    Fetch NSE stocks with sector data.
    Priority: NSE Index API → NSE CSV with sector enrichment → hardcoded fallback
    """
    key    = "nse_universe_v3"
    cached = cache.get(key, 86400, disk=True)
    if cached:
        logger.info(f"NSE universe from cache: {len(cached)} stocks")
        return cached

    stocks: List[Dict] = []

    # Try NSE index APIs (these have sector/industry info)
    indices = [
        "NIFTY 500",
        "NIFTY MIDCAP 150",
        "NIFTY SMALLCAP 250",
        "SECURITIES IN F&O",
    ]

    session = requests.Session()
    try:
        session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=5)
    except Exception:
        pass

    seen: set = set()
    for index_name in indices:
        try:
            url = f"https://www.nseindia.com/api/equity-stockIndices?index={requests.utils.quote(index_name)}"
            res = session.get(url, headers=NSE_HEADERS, timeout=10)
            if res.status_code != 200:
                continue
            items = res.json().get("data", [])
            for item in items:
                sym = item.get("symbol", "").strip()
                if not sym or sym in seen:
                    continue
                industry = (
                    item.get("meta", {}).get("industry", "") or
                    item.get("industryInfo", {}).get("industry", "") or ""
                )
                sector = NSE_SECTOR_MAP.get(industry.lower(), "Other")
                stocks.append({
                    "symbol": sym + ".NS",
                    "name":   item.get("meta", {}).get("companyName", sym),
                    "sector": sector,
                })
                seen.add(sym)
        except Exception as e:
            logger.debug(f"NSE index {index_name} failed: {e}")

    # If we got stocks with sectors, cache and return
    sectored = [s for s in stocks if s["sector"] != "Other"]
    if len(sectored) >= 100:
        cache.set(key, stocks, 86400, disk=True)
        logger.info(f"NSE universe from API: {len(stocks)} stocks ({len(sectored)} with sectors)")
        return stocks

    # Build from hardcoded + try to enrich with CSV
    logger.info("Building universe from hardcoded sector data")
    stocks = _build_from_hardcoded()

    # Also try NSE CSV and append any extra symbols as "Other"
    try:
        csv_stocks = _fetch_nse_csv(session)
        hardcoded_syms = {s["symbol"] for s in stocks}
        for s in csv_stocks:
            if s["symbol"] not in hardcoded_syms:
                stocks.append(s)
    except Exception:
        pass

    cache.set(key, stocks, 86400, disk=True)
    logger.info(f"NSE universe built: {len(stocks)} stocks")
    return stocks


def _build_from_hardcoded() -> List[Dict]:
    """Build stock list from hardcoded sector universe."""
    stocks = []
    for sector, syms in HARDCODED_NSE.items():
        for sym in syms:
            stocks.append({
                "symbol": sym,
                "name":   sym.replace(".NS","").replace(".BO",""),
                "sector": sector,
            })
    return stocks


def _fetch_nse_csv(session: requests.Session) -> List[Dict]:
    """Fetch NSE equity list CSV."""
    try:
        url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
        res = session.get(url, headers=NSE_HEADERS, timeout=15)
        if res.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(res.text))
            stocks = []
            for _, row in df.iterrows():
                sym = str(row.get("SYMBOL","")).strip()
                if sym and sym != "nan":
                    stocks.append({
                        "symbol": sym + ".NS",
                        "name":   str(row.get("NAME OF COMPANY", sym)),
                        "sector": "Other",
                    })
            return stocks
    except Exception as e:
        logger.debug(f"NSE CSV failed: {e}")
    return []


def fetch_sp500_stocks() -> List[Dict]:
    """Fetch S&P 500 from Wikipedia."""
    key    = "sp500_v3"
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
            sym = str(row.get("Symbol","")).strip().replace(".","-")
            if sym and sym != "nan":
                stocks.append({
                    "symbol": sym,
                    "name":   str(row.get("Security", sym)),
                    "sector": US_SECTOR_MAP.get(str(row.get("GICS Sector","")), "Other"),
                })
        if stocks:
            cache.set(key, stocks, 86400, disk=True)
            logger.info(f"S&P 500: {len(stocks)} stocks")
            return stocks
    except Exception as e:
        logger.warning(f"S&P 500 fetch failed: {e}")

    return _us_fallback()


def _us_fallback() -> List[Dict]:
    stocks = []
    base = {
        "Technology": ["AAPL","MSFT","GOOGL","NVDA","META","AMD","INTC","CRM","ORCL","CSCO"],
        "Finance":    ["JPM","BAC","GS","MS","WFC","V","MA","AXP","BLK","C"],
        "Healthcare": ["JNJ","PFE","ABBV","MRK","UNH","LLY","BMY","AMGN","GILD","CVS"],
        "Consumer":   ["AMZN","TSLA","NKE","SBUX","MCD","HD","LOW","TGT","COST","BKNG"],
        "Energy":     ["XOM","CVX","COP","SLB","OXY","PSX","VLO","MPC","HAL","EOG"],
        "Infra":      ["UNP","CAT","DE","EMR","GE","HON","RTX","LMT","NOC","BA"],
        "FMCG":       ["PG","KO","PEP","PM","MO","CL","KMB","GIS","CPB","HSY"],
        "Metals":     ["NEM","FCX","AA","NUE","STLD","CLF","X","ATI","MP","CENX"],
        "ETF":        ["SPY","QQQ","VTI","GLD","AGG","IWM","EFA","VEA","BND","VXUS"],
    }
    for sector, syms in base.items():
        for sym in syms:
            stocks.append({"symbol": sym, "name": sym, "sector": sector})
    return stocks


def get_universe(market: str) -> List[Dict]:
    if market == "india":
        return fetch_nse_all_stocks()
    return fetch_sp500_stocks()


def filter_by_sectors(universe: List[Dict], sectors: List[str]) -> List[Dict]:
    """
    STRICT sector filter — case-insensitive matching.
    """
    if not sectors:
        return universe

    # Normalize sector names for matching
    sector_set = {s.lower().strip() for s in sectors}

    filtered = [
        s for s in universe
        if s.get("sector","").lower().strip() in sector_set
    ]

    logger.info(f"Sector filter {sectors} → {len(filtered)}/{len(universe)} stocks")
    return filtered