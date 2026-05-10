from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")
ET  = pytz.timezone("America/New_York")


def is_nse_open() -> bool:
    now = datetime.now(tz=IST)
    if now.weekday() >= 5:
        return False
    return (
        (now.hour == 9 and now.minute >= 15) or
        (10 <= now.hour <= 14) or
        (now.hour == 15 and now.minute <= 30)
    )


def is_us_open() -> bool:
    now = datetime.now(tz=ET)
    if now.weekday() >= 5:
        return False
    return (
        (now.hour == 9 and now.minute >= 30) or
        (10 <= now.hour <= 15) or
        (now.hour == 16 and now.minute == 0)
    )


def is_weekend() -> bool:
    return datetime.now(tz=IST).weekday() >= 5


def get_refresh_interval(has_active_connections: bool = False) -> int:
    if is_weekend():
        return 21600
    markets_open = is_nse_open() or is_us_open()
    if has_active_connections:
        return 15 if markets_open else 120
    return 300 if markets_open else 1800


def market_status() -> dict:
    now_ist = datetime.now(tz=IST)
    now_et  = datetime.now(tz=ET)
    return {
        "nse_open":                 is_nse_open(),
        "us_open":                  is_us_open(),
        "is_weekend":               is_weekend(),
        "refresh_interval_seconds": get_refresh_interval(),
        "ist_time":                 now_ist.strftime("%H:%M:%S"),
        "et_time":                  now_et.strftime("%H:%M:%S"),
        "timestamp":                now_ist.isoformat(),
    }