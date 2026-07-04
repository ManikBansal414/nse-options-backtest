"""Script entrypoint for running the backtest from scripts/."""

import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine import BacktestEngine
from logger import get_logger
from reporting import clear_results_dir, generate_full_report
from src.strategies.atm_straddle import ATMStraddle


def main() -> None:
    clear_results_dir()

    log = get_logger()
    log.info("  OPTIONS BACKTESTING FRAMEWORK")
    log.info("  Strategy: ATM Straddle (Nearest Expiry)")
    log.info("  Underliers: NIFTY, BANKNIFTY")
    log.info("=" * 60)

    strategy = ATMStraddle()
    engine = BacktestEngine(strategy=strategy)

    log.info("Trading dates: %s", engine.trading_dates)
    log.info("Underliers:    %s", engine.underliers)

    t0 = time.time()
    results = engine.run()
    t_exec = time.time() - t0
    log.info("[TIMER] Backtest execution: %.1fs", t_exec)

    t1 = time.time()
    generate_full_report(results)
    t_report = time.time() - t1
    log.info("[TIMER] Report generation: %.1fs", t_report)
    log.info("[TIMER] Total elapsed: %.1fs", time.time() - t0)


if __name__ == "__main__":
    main()
