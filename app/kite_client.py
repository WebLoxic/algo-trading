# app/kite_client.py
import json
import logging
import time
from threading import Lock
from kiteconnect import KiteConnect
from pathlib import Path
from typing import Optional, Dict, List, Any

from .config import KITE_API_KEY, KITE_API_SECRET, TOKEN_FILE

log = logging.getLogger(__name__)


class KiteClient:
    """
    Robust wrapper around KiteConnect:
      - persistent token handling (save/load)
      - instruments caching / lookup helpers with TTL and lock
      - handy passthrough methods for orders/ltp/positions/holdings
    """

    def __init__(self, inst_cache_ttl: int = 60):
        self.kite = KiteConnect(api_key=KITE_API_KEY) if KITE_API_KEY else None
        self.access_token: Optional[str] = None
        self.session_data: Dict[str, Any] = {}

        # instruments cache and lookup map
        self.instruments: List[Dict[str, Any]] = []
        self._inst_map: Dict[str, int] = {}  # keys: "EXCH:SYMBOL" and "SYMBOL"
        self._inst_cache_ts: float = 0.0
        self._inst_cache_ttl = inst_cache_ttl
        self._inst_lock = Lock()

        # ensure token dir exists
        try:
            Path(TOKEN_FILE).parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        # load token from disk (if present)
        self._load_token()

    # ---------------------------
    # Token management / login
    # ---------------------------
    def login_url(self, redirect: Optional[str] = None) -> str:
        if not self.kite:
            raise RuntimeError("KITE_API_KEY not configured")
        if redirect:
            return self.kite.login_url(redirect_url=redirect)
        return self.kite.login_url()

    def _load_token(self):
        p = Path(TOKEN_FILE)
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            at = data.get("access_token") or data.get("accessToken")
            if not at:
                log.warning("Token file found but no access_token present")
                return
            self.access_token = at
            if self.kite:
                try:
                    self.kite.set_access_token(self.access_token)
                except Exception:
                    log.exception("kite.set_access_token failed during _load_token")
            self.session_data = data
            if not self.is_token_valid():
                log.warning("Loaded token invalid or expired; clearing token file.")
                self.clear_token()
            else:
                log.info("Kite token loaded and validated from %s", TOKEN_FILE)
                # Try to load instruments now that token is valid (best-effort)
                try:
                    self.load_instruments(force_refresh=True)
                except Exception:
                    log.exception("Failed to load instruments during _load_token")
        except Exception:
            log.exception("Failed to load/validate token file %s", TOKEN_FILE)

    def save_token(self, data: Dict[str, Any]):
        """
        Persist session data returned by kite.generate_session(...) and ensure kite client has token.
        Also triggers instrument load so get_instrument_token works right after login.
        """
        try:
            p = Path(TOKEN_FILE)
            p.parent.mkdir(parents=True, exist_ok=True)
            data_to_save = dict(data)
            at = data_to_save.get("access_token") or data_to_save.get("accessToken")
            if at:
                self.access_token = at
                if self.kite:
                    try:
                        self.kite.set_access_token(self.access_token)
                    except Exception:
                        log.exception("kite.set_access_token failed in save_token")
            p.write_text(json.dumps(data_to_save, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
            self.session_data = data_to_save
            log.info("Kite token saved to %s", str(p))
            # Load instruments immediately (best-effort)
            try:
                self.load_instruments(force_refresh=True)
            except Exception:
                log.exception("Failed to load instruments after saving token")
        except Exception as e:
            log.exception("Failed to write token file %s: %s", TOKEN_FILE, e)
            raise

    def set_access_token(self, token: str):
        if not token:
            raise ValueError("token must be non-empty")
        self.access_token = token
        if self.kite:
            self.kite.set_access_token(token)
        # attempt to refresh instrument list (best-effort, non-blocking)
        try:
            self.load_instruments(force_refresh=True)
        except Exception:
            log.debug("load_instruments failed after set_access_token")

    def is_token_valid(self) -> bool:
        if not self.access_token or not self.kite:
            return False
        try:
            _ = self.kite.profile()
            return True
        except Exception as e:
            log.debug("Token validation failed: %s", e)
            return False

    def clear_token(self):
        try:
            p = Path(TOKEN_FILE)
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    log.exception("Failed to delete token file %s", TOKEN_FILE)
            self.access_token = None
            self.session_data = {}
            try:
                if self.kite:
                    # set invalid token to prevent accidental use
                    self.kite.set_access_token("")
            except Exception:
                log.debug("kite.set_access_token('') may not be supported; ignoring")
            log.info("Kite token cleared from disk and memory")
        except Exception:
            log.exception("clear_token encountered an error")

    # ---------------------------
    # Instruments / lookup helpers
    # ---------------------------
    def load_instruments(self, exchanges: Optional[List[str]] = None, force_refresh: bool = False) -> bool:
        """
        Load instruments from Kite for the given exchanges (default: ["NSE","NFO","BSE"]).
        Builds a fast lookup map self._inst_map with keys:
            - "NSE:RELIANCE" -> instrument_token
            - "RELIANCE" -> instrument_token  (first match wins)
        Returns True on success.
        """
        if not self.kite:
            raise RuntimeError("KITE_API_KEY not configured")

        exchanges = exchanges or ["NSE", "NFO", "BSE"]
        now = time.time()

        # fast-path: if cache still valid and not forced, do nothing
        if not force_refresh and (now - self._inst_cache_ts) < self._inst_cache_ttl and self._inst_map:
            log.debug("load_instruments: cache valid, skipping refresh (ttl=%s)", self._inst_cache_ttl)
            return True

        # acquire lock to avoid concurrent loads
        if not self._inst_lock.acquire(blocking=False):
            # someone else is refreshing; wait a short time and return current cache
            log.debug("load_instruments: another thread refreshing; returning existing cache")
            return True

        try:
            instruments: List[Dict[str, Any]] = []
            inst_map: Dict[str, int] = {}
            try:
                for exch in exchanges:
                    try:
                        lst = self.kite.instruments(exch)
                    except Exception as e:
                        log.warning("Failed to fetch instruments for exchange %s: %s", exch, e)
                        lst = []
                    if not lst:
                        continue
                    instruments.extend(lst)
                    for inst in lst:
                        try:
                            ts = inst.get("tradingsymbol")
                            token_raw = inst.get("instrument_token")
                            ex = (inst.get("exchange") or exch).upper()
                            if not ts or token_raw is None:
                                continue
                            token = int(token_raw)
                            key1 = f"{ex}:{ts}".upper()
                            inst_map[key1] = token
                            # also map plain symbol if not set (first occurrence wins)
                            short = ts.upper()
                            if short not in inst_map:
                                inst_map[short] = token
                        except Exception:
                            # skip problematic record
                            continue
                # commit
                self.instruments = instruments
                self._inst_map = inst_map
                self._inst_cache_ts = time.time()
                log.info("Loaded instruments: total=%d, lookup_map=%d", len(self.instruments), len(self._inst_map))
                return True
            except Exception as e:
                log.exception("load_instruments inner failure: %s", e)
                raise
        finally:
            try:
                self._inst_lock.release()
            except Exception:
                pass

    def get_instrument_token(self, symbol: str, exchange: Optional[str] = None) -> int:
        """
        Resolve symbol to instrument token using cached instrument map.
        Accepts:
          - "RELIANCE"
          - "NSE:RELIANCE"
          - symbol + exchange param
        Tries a single load refresh if cache miss occurs. Raises ValueError if not found.
        """
        if not self.kite:
            raise RuntimeError("KITE_API_KEY not configured")

        if not symbol:
            raise ValueError("symbol required")

        s = str(symbol).strip().upper()

        # direct EXACT key (EXCHANGE:SYMBOL) or plain symbol
        if s in self._inst_map:
            try:
                return int(self._inst_map[s])
            except Exception:
                # fallthrough to refresh
                log.debug("Instrument token present but conversion failed for key %s", s)

        # if user passed exchange param
        if exchange:
            key = f"{exchange.strip().upper()}:{s}"
            if key in self._inst_map:
                try:
                    return int(self._inst_map[key])
                except Exception:
                    log.debug("Instrument token present but conversion failed for key %s", key)

        # attempt refresh once if cache is stale or previously missed
        try:
            log.debug("get_instrument_token: cache miss for %s; attempting a refresh", symbol)
            self.load_instruments(force_refresh=True)
        except Exception:
            log.debug("get_instrument_token: instruments refresh failed")

        # try again after refresh
        if s in self._inst_map:
            try:
                return int(self._inst_map[s])
            except Exception:
                pass
        if exchange:
            key = f"{exchange.strip().upper()}:{s}"
            if key in self._inst_map:
                try:
                    return int(self._inst_map[key])
                except Exception:
                    pass

        # try case-insensitive contains / substring match (last resort)
        lowered = s.lower()
        for k, tok in self._inst_map.items():
            try:
                # k looks like "NSE:RELIANCE" or "RELIANCE"
                tsym = k.split(":", 1)[-1]
                if tsym.lower() == lowered:
                    return int(tok)
            except Exception:
                continue
        for k, tok in self._inst_map.items():
            try:
                tsym = k.split(":", 1)[-1]
                if lowered in tsym.lower():
                    return int(tok)
            except Exception:
                continue

        # not found
        raise ValueError(f"Instrument token not found for symbol: {symbol}")

    # ---------------------------
    # Passthrough helpers
    # ---------------------------
    def place_order(self, **kwargs):
        if not self.kite:
            return {"status": "failed", "error": "KITE_API_KEY not configured"}
        try:
            if "variety" not in kwargs:
                kwargs["variety"] = "regular"
            if "product" not in kwargs:
                kwargs["product"] = "MIS"
            order_id = self.kite.place_order(**kwargs)
            return {"status": "success", "order_id": order_id}
        except Exception as e:
            log.error(f"Order failed: {e}")
            return {"status": "failed", "error": str(e)}

    def ltp(self, instruments):
        if not self.kite:
            raise RuntimeError("KITE_API_KEY not configured")
        return self.kite.ltp(instruments)

    def orders(self):
        if not self.kite:
            raise RuntimeError("KITE_API_KEY not configured")
        return self.kite.orders()

    def positions(self):
        if not self.kite:
            raise RuntimeError("KITE_API_KEY not configured")
        return self.kite.positions()

    def holdings(self):
        if not self.kite:
            raise RuntimeError("KITE_API_KEY not configured")
        return self.kite.holdings()

    # convenience
    @property
    def instruments_count(self) -> int:
        return len(self.instruments or [])


# singleton
kite_client = KiteClient()
