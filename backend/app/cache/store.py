"""
Multi-layer cache:
L1: In-memory dict (microseconds)
L2: diskcache (milliseconds, survives restarts)
"""
import hashlib
import json
import logging
import time
import threading
from pathlib import Path
from typing import Any, Optional

import diskcache

logger   = logging.getLogger(__name__)
_l1:     dict  = {}
_l1_lock       = threading.RLock()

# L2: disk cache — survives server restarts
_disk: diskcache.Cache = diskcache.Cache(
    directory=str(Path("data/cache/diskcache")),
    size_limit=512 * 1024 * 1024,  # 512MB max
    eviction_policy="least-recently-used",
)

# TTL constants
TTL_PRICE      = 30
TTL_ANALYTICS  = 600
TTL_BENCHMARK  = 3600
TTL_PREDICTION = 21600
TTL_SYMBOLS    = 604800


def _make_key(prefix: str, data: Any) -> str:
    raw  = json.dumps(data, sort_keys=True, default=str)
    h    = hashlib.sha1(raw.encode()).hexdigest()[:16]
    return f"{prefix}:{h}"


def make_portfolio_key(prefix: str, holdings: list, extra: Any = None) -> str:
    symbols = sorted(h.get("symbol", "") for h in holdings)
    return _make_key(prefix, {"s": symbols, "e": extra})


# ── L1 operations ────────────────────────────────────────────

def l1_get(key: str, ttl: int) -> Optional[Any]:
    with _l1_lock:
        entry = _l1.get(key)
        if not entry:
            return None
        val, ts = entry
        if time.monotonic() - ts > ttl:
            del _l1[key]
            return None
        return val


def l1_set(key: str, val: Any) -> None:
    with _l1_lock:
        _l1[key] = (val, time.monotonic())


# ── L2 operations ────────────────────────────────────────────

def l2_get(key: str) -> Optional[Any]:
    try:
        return _disk.get(key)
    except Exception:
        return None


def l2_set(key: str, val: Any, ttl: int) -> None:
    try:
        _disk.set(key, val, expire=ttl)
    except Exception as e:
        logger.debug(f"Disk cache set failed: {e}")


# ── Unified get/set ──────────────────────────────────────────

def get(key: str, ttl: int, disk: bool = False) -> Optional[Any]:
    val = l1_get(key, ttl)
    if val is not None:
        return val
    if disk:
        val = l2_get(key)
        if val is not None:
            l1_set(key, val)  # promote to L1
            return val
    return None


def set(key: str, val: Any, ttl: int, disk: bool = False) -> None:
    l1_set(key, val)
    if disk:
        l2_set(key, val, ttl)


def invalidate(key: str) -> None:
    with _l1_lock:
        _l1.pop(key, None)
    try:
        _disk.delete(key)
    except Exception:
        pass


def stats() -> dict:
    with _l1_lock:
        l1_size = len(_l1)
    return {
        "l1_entries": l1_size,
        "l2_size_bytes": _disk.volume(),
    }