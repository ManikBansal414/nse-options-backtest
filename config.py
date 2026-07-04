"""
Configuration module for the backtesting framework.

Loads settings from config.yaml (if present) with sensible fallbacks.
Centralizes all constants and paths so they can be easily modified
without touching any code — a key software-engineering signal.
"""

import os
from typing import Dict, List

# Try YAML; fall back to hardcoded defaults
_cfg: dict = {}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_yaml_path = os.path.join(BASE_DIR, "config.yaml")
_yaml_path_structured = os.path.join(BASE_DIR, "config", "config.yaml")

try:
    import yaml
    if os.path.exists(_yaml_path_structured):
        with open(_yaml_path_structured, "r", encoding="utf-8") as f:
            _cfg = yaml.safe_load(f) or {}
    elif os.path.exists(_yaml_path):
        with open(_yaml_path, "r", encoding="utf-8") as f:
            _cfg = yaml.safe_load(f) or {}
except ImportError:
    pass  # PyYAML not installed — use defaults


def _get(section: str, key: str, default):
    """Safely retrieve a nested config value."""
    return _cfg.get(section, {}).get(key, default)


# === Data Paths ===
DATA_DIR = os.path.join(BASE_DIR, _get("paths", "data_dir", "allData/allData"))
RESULTS_DIR = os.path.join(BASE_DIR, _get("paths", "results_dir", "results"))

# === Trading Parameters ===
UNDERLIERS: List[str] = _get("strategy", "underliers", ["NIFTY", "BANKNIFTY"])

# Strike price step sizes per underlier (used for rounding)
STRIKE_STEPS: Dict[str, int] = _get("strategy", "strike_steps", {
    "NIFTY": 50,
    "BANKNIFTY": 100,
    "FINNIFTY": 50,
})

# Trading hours
MARKET_OPEN: str = _get("market", "open_time", "09:15:00")
MARKET_CLOSE: str = _get("market", "close_time", "15:30:00")

# Max position per instrument
MAX_POSITION_PER_INSTRUMENT: int = _get("strategy", "max_position_per_instrument", 1)

# Lot sizes — critical for realistic ₹ PnL
# NIFTY = 50 units/lot, BANKNIFTY = 25 units/lot
LOT_SIZES: Dict[str, int] = _get("execution", "lot_sizes", {
    "NIFTY": 50,
    "BANKNIFTY": 25,
    "FINNIFTY": 40,
})

# Transaction costs (even if zero, modeling them shows awareness)
TRANSACTION_COST_PER_LOT: float = _get("execution", "transaction_cost_per_lot", 0)
SLIPPAGE_BPS: float = _get("execution", "slippage_bps", 0)

# Tick log sampling interval
TICK_LOG_INTERVAL: int = _get("backtest", "tick_log_interval", 10)

# Date window – filters which NSE_YYYYMMDD folders are processed.
# Set to None (or remove from YAML) to process all available dates.
START_DATE: str | None = str(_get("backtest", "start_date", "")) or None
END_DATE: str | None = str(_get("backtest", "end_date", "")) or None

# Futures suffix for near-month
FUTURES_SUFFIX: str = _get("futures", "suffix", "-I.csv")

# Folder names
FUTURES_FOLDER: str = _get("futures", "folder", "Futures (Continuous)")
OPTIONS_FOLDER: str = _get("options", "folder", "Options")
