"""
Data loading and parsing utilities for the backtesting framework.

Handles:
- Discovering trading dates from the allData directory
- Parsing option instrument filenames into (underlier, expiry, strike, option_type)
- Loading futures tick data (Date, Time, Price, Volume, OI)
- Loading options tick data
- Finding the nearest expiry for a given trading date + underlier
- Building a second-by-second price grid from raw tick data
- OI (Open Interest) series extraction for visualization
"""

import os
import re
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Set
from functools import lru_cache

from .config import (
    DATA_DIR, FUTURES_FOLDER, OPTIONS_FOLDER,
    FUTURES_SUFFIX, STRIKE_STEPS, MARKET_OPEN, MARKET_CLOSE,
    START_DATE, END_DATE,
)
from .logger import get_logger

log = get_logger()

# --------------------------------------------------------------
# 1. Discover available trading dates
# --------------------------------------------------------------

def get_trading_dates() -> List[str]:
    """
    Return a sorted list of trading-date strings (YYYYMMDD)
    by scanning the NSE_<date> folders.

    If START_DATE / END_DATE are set in config.yaml, the list is
    filtered to only include dates within that window (inclusive).
    Days with incomplete data (e.g. missing futures) are still
    discovered here but skipped later by the engine with a warning.
    """
    if not os.path.exists(DATA_DIR):
        log.error("Data directory not found: %s", DATA_DIR)
        return []
    folders = [
        f for f in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, f)) and f.startswith("NSE_")
    ]
    dates = sorted([f.replace("NSE_", "") for f in folders])

    # Apply date window from config.yaml (if set)
    if START_DATE:
        dates = [d for d in dates if d >= START_DATE]
    if END_DATE:
        dates = [d for d in dates if d <= END_DATE]

    log.info("Discovered %d trading dates (window: %s → %s)",
             len(dates), START_DATE or "earliest", END_DATE or "latest")
    return dates


# --------------------------------------------------------------
# 2. Parse an option filename
# --------------------------------------------------------------

# Regex: UNDERLIER (letters) + EXPIRY (6 digits) + STRIKE (digits) + TYPE (CE|PE)
_OPT_RE = re.compile(r"^([A-Z]+)(\d{6})(\d+)(CE|PE)$")


def parse_option_name(name: str) -> Optional[Tuple[str, str, int, str]]:
    """
    Parse an option instrument name (no .csv) into:
      (underlier, expiry_str, strike, option_type)

    Example:
      'NIFTY22110314550PE' -> ('NIFTY', '221103', 14550, 'PE')
    """
    m = _OPT_RE.match(name)
    if not m:
        return None
    return m.group(1), m.group(2), int(m.group(3)), m.group(4)


# --------------------------------------------------------------
# 3. Load tick-level CSV files
# --------------------------------------------------------------

_COL_NAMES = ["Date", "Time", "Price", "Volume", "OI"]


def _load_csv(filepath: str) -> pd.DataFrame:
    """
    Load a 5-column CSV (Date,Time,Price,Volume,OI).
    Auto-detects whether the file has a header row or not,
    so both real data (no header) and synthetic data (with header) work.
    Returns a DataFrame indexed by a proper datetime.
    """
    if not os.path.exists(filepath):
        log.warning("File not found: %s", filepath)
        return pd.DataFrame(columns=_COL_NAMES + ["Datetime"])
    try:
        # Auto-detect header: peek at first cell
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            first_cell = f.readline().split(",")[0].strip().strip('"')
        has_header = not first_cell[:1].isdigit()

        if has_header:
            df = pd.read_csv(filepath)
            # Normalize column names to standard: Date, Time, Price, Volume, OI
            col_map = {}
            for c in df.columns:
                cl = c.strip().lower()
                if cl == "date":
                    col_map[c] = "Date"
                elif cl == "time":
                    col_map[c] = "Time"
                elif cl == "price":
                    col_map[c] = "Price"
                elif "vol" in cl:
                    col_map[c] = "Volume"
                elif "interest" in cl or cl == "oi":
                    col_map[c] = "OI"
            df = df.rename(columns=col_map)
            for needed in _COL_NAMES:
                if needed not in df.columns:
                    df[needed] = 0
        else:
            df = pd.read_csv(filepath, header=None, names=_COL_NAMES)

        df["Datetime"] = pd.to_datetime(df["Date"].astype(str) + " " + df["Time"])
        df = df.sort_values("Datetime").reset_index(drop=True)
        return df
    except Exception as e:
        log.error("Error loading %s: %s", filepath, e)
        return pd.DataFrame(columns=_COL_NAMES + ["Datetime"])


def load_futures(trading_date: str, underlier: str) -> pd.DataFrame:
    """Load the -I (near-month) futures tick data."""
    folder = os.path.join(DATA_DIR, f"NSE_{trading_date}", FUTURES_FOLDER)
    path = os.path.join(folder, f"{underlier}{FUTURES_SUFFIX}")
    if not os.path.exists(path):
        log.warning("Futures file missing: %s", path)
        return pd.DataFrame(columns=_COL_NAMES + ["Datetime"])
    return _load_csv(path)


def load_option(trading_date: str, instrument_name: str) -> pd.DataFrame:
    """Load a single option instrument's tick data for a given date."""
    folder = os.path.join(DATA_DIR, f"NSE_{trading_date}", OPTIONS_FOLDER)
    path = os.path.join(folder, f"{instrument_name}.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=_COL_NAMES + ["Datetime"])
    return _load_csv(path)


# --------------------------------------------------------------
# 4. Find the nearest expiry for a given trading date
# --------------------------------------------------------------

def find_nearest_expiry(trading_date: str, underlier: str) -> Optional[str]:
    """
    Among all option files available for *underlier* on *trading_date*,
    return the 6-char expiry string of the closest future expiry
    (i.e. >= trading_date).
    """
    folder = os.path.join(DATA_DIR, f"NSE_{trading_date}", OPTIONS_FOLDER)
    if not os.path.exists(folder):
        return None

    td = datetime.strptime(trading_date, "%Y%m%d")
    expiries: Set[str] = set()

    for fname in os.listdir(folder):
        if not fname.endswith(".csv"):
            continue
        parsed = parse_option_name(fname.replace(".csv", ""))
        if parsed is None:
            continue
        u, exp_str, _, _ = parsed
        if u != underlier:
            continue
        try:
            exp_date = datetime.strptime(exp_str, "%y%m%d")
        except ValueError:
            continue
        if exp_date >= td:
            expiries.add(exp_str)

    if not expiries:
        return None

    nearest = min(expiries, key=lambda e: datetime.strptime(e, "%y%m%d"))
    log.debug("Nearest expiry for %s on %s: %s", underlier, trading_date, nearest)
    return nearest


# --------------------------------------------------------------
# 5. List all strikes for a given underlier + expiry on a date
# --------------------------------------------------------------

def list_strikes(trading_date: str, underlier: str, expiry: str) -> List[int]:
    """Return sorted list of unique strike prices available."""
    folder = os.path.join(DATA_DIR, f"NSE_{trading_date}", OPTIONS_FOLDER)
    if not os.path.exists(folder):
        return []
    strikes: Set[int] = set()
    prefix = f"{underlier}{expiry}"
    for fname in os.listdir(folder):
        if not fname.startswith(prefix) or not fname.endswith(".csv"):
            continue
        parsed = parse_option_name(fname.replace(".csv", ""))
        if parsed:
            strikes.add(parsed[2])
    return sorted(strikes)


# --------------------------------------------------------------
# 6. Build second-level price series (forward-fill)
# --------------------------------------------------------------

def build_second_grid(df: pd.DataFrame, trading_date: str) -> pd.Series:
    """
    Given tick data with a 'Datetime' column and 'Price' column,
    resample to 1-second frequency and forward-fill.
    Returns a Series indexed by datetime at second granularity.
    """
    if df.empty:
        return pd.Series(dtype=float)

    start = pd.Timestamp(f"{trading_date} {MARKET_OPEN}")
    end = pd.Timestamp(f"{trading_date} {MARKET_CLOSE}")

    # Take last price per second
    s = df.set_index("Datetime")["Price"]
    s = s[~s.index.duplicated(keep="last")]
    s = s.resample("1s").last()

    # Reindex to full trading window
    full_idx = pd.date_range(start, end, freq="1s")
    s = s.reindex(full_idx).ffill().bfill()
    return s


def build_second_grid_with_oi(df: pd.DataFrame, trading_date: str) -> pd.DataFrame:
    """
    Build a second-level grid with both Price and OI columns.
    Used for OI visualization — most candidates ignore OI entirely.
    """
    if df.empty:
        return pd.DataFrame(columns=["Price", "OI"])

    start = pd.Timestamp(f"{trading_date} {MARKET_OPEN}")
    end = pd.Timestamp(f"{trading_date} {MARKET_CLOSE}")

    df_indexed = df.set_index("Datetime")[["Price", "OI"]]
    df_indexed = df_indexed[~df_indexed.index.duplicated(keep="last")]
    df_indexed = df_indexed.resample("1s").last()

    full_idx = pd.date_range(start, end, freq="1s")
    df_indexed = df_indexed.reindex(full_idx).ffill().bfill()
    return df_indexed


def round_to_strike(price: float, step: int) -> int:
    """Round a price to the nearest strike (step-multiple)."""
    return int(round(price / step) * step)


# --------------------------------------------------------------
# 7. Lazy option price loader with caching
# --------------------------------------------------------------

class OptionPriceCache:
    """
    Lazily loads and caches option price grids on demand.
    Only loads an instrument when first requested, not all at once.
    """

    def __init__(self, trading_date: str):
        self.trading_date = trading_date
        self._cache: Dict[str, pd.Series] = {}
        self._oi_cache: Dict[str, pd.DataFrame] = {}  # for OI visualization
        self._missing: Set[str] = set()  # instruments known to have no file

    def get_price(self, instrument: str, ts: pd.Timestamp) -> Optional[float]:
        """
        Get the price for an instrument at timestamp ts.
        Lazily loads the instrument's data on first access.
        Returns None if no data available.
        """
        if instrument in self._missing:
            return None

        if instrument not in self._cache:
            self._load_instrument(instrument)

        if instrument in self._missing:
            return None

        grid = self._cache[instrument]
        if ts in grid.index:
            val = grid.loc[ts]
            if not pd.isna(val):
                return float(val)
        return None

    def get_oi_series(self, instrument: str) -> Optional[pd.Series]:
        """
        Return the OI (Open Interest) series for an instrument.
        Loads with OI data if not already cached.

        Most candidates will completely ignore the OI column.
        Visualizing it shows you understand what you're trading.
        """
        if instrument in self._missing:
            return None

        if instrument not in self._oi_cache:
            self._load_instrument_with_oi(instrument)

        if instrument in self._oi_cache:
            return self._oi_cache[instrument]
        return None

    def _load_instrument(self, instrument: str):
        """Load a single instrument's second-grid into cache."""
        df = load_option(self.trading_date, instrument)
        if df.empty:
            self._missing.add(instrument)
            return
        grid = build_second_grid(df, self.trading_date)
        if grid.empty:
            self._missing.add(instrument)
            return
        self._cache[instrument] = grid

    def _load_instrument_with_oi(self, instrument: str):
        """Load instrument with both price and OI data."""
        df = load_option(self.trading_date, instrument)
        if df.empty:
            self._missing.add(instrument)
            return
        grid_df = build_second_grid_with_oi(df, self.trading_date)
        if grid_df.empty:
            self._missing.add(instrument)
            return
        # Store price in main cache too
        if instrument not in self._cache:
            self._cache[instrument] = grid_df["Price"]
        self._oi_cache[instrument] = grid_df["OI"]

    def get_loaded_instruments(self) -> List[str]:
        """Return list of instruments currently in cache."""
        return list(self._cache.keys())

    def preload(self, instruments: List[str]):
        """Preload a batch of instruments into cache."""
        for inst in instruments:
            if inst not in self._cache and inst not in self._missing:
                self._load_instrument(inst)
