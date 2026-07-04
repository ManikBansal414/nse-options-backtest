# NSE Options Backtesting Engine

Strategy-agnostic backtesting framework with an ATM Straddle reference implementation.

## Run in 3 commands

```bash
pip install -r requirements.txt
python scripts/run_backtest.py
pytest -q
```

Input data path is configured in `config/config.yaml` under `paths.data_dir`.
Backtest outputs are written to `outputs/`.

## Project structure

```
nse-options-backtest/
├── config/
│   └── config.yaml            # all tuneable parameters
├── src/
│   ├── __init__.py
│   ├── config.py              # loads config.yaml, exports constants
│   ├── data_loader.py         # futures/options CSV parsing, price cache
│   ├── engine.py              # strategy-agnostic backtest loop
│   ├── logger.py              # structured logging (console + file)
│   ├── reporting.py           # tearsheet, plots, CSV exports
│   └── strategies/
│       ├── __init__.py
│       └── atm_straddle.py    # reference strategy implementation
├── scripts/
│   └── run_backtest.py        # CLI entrypoint
├── tests/
│   └── test_project_contract.py
├── outputs/                   # generated CSVs, PNGs, tearsheet
├── strategy_observations.md   # trading insights from the run
├── .gitignore
├── requirements.txt
└── README.md
```

## What this submission does

One-second event-driven simulation over NSE futures and options data.

At each timestamp the strategy selects ATM strike from futures price, holds CE+PE straddle, rebalances only when strike changes, and force-closes all open positions at day end.

## Results snapshot (Nov 2022 run)

| Metric | NIFTY | BANKNIFTY | Combined |
|---|---:|---:|---:|
| Total Realized PnL (₹) | -20,217.50 | -25,853.75 | -46,071.25 |
| Total Trades | 10,456 | 11,696 | 22,152 |
| Avg Trades/Day | 747 | 836 | 1,582 |
| Sharpe (daily annualized) | -11.08 | -17.90 | -15.76 |
| Winning Days | - | - | 2/14 |

| Additional risk metrics | Value |
|---|---:|
| Max Daily PnL (₹) | 2,650.00 |
| Min Daily PnL (₹) | -10,447.50 |
| Max Drawdown (₹) | -47,222.50 |
| Median Hold Duration (s) | 4.0 |
| Expiry Day PnL (₹) | -13,586.25 |

CE leg total PnL: ₹-13,966.25
PE leg total PnL: ₹-32,105.00

### Note on short hold durations

The 4-second median hold is genuine and driven by futures price oscillating near strike boundaries.  With NIFTY step = 50, a price at 18,225 rounds to 18,250; at 18,224 it rounds to 18,200.  Small tick-by-tick moves near these boundaries trigger rapid back-and-forth rebalancing.  The phantom-trade guard prevents redundant sell/rebuy of unchanged positions, so each rebalance logged here is a real strike change.

## Why this strategy loses (expected)

This is a long-gamma, short-theta profile. In normal conditions:

1. Both bought options decay with time (theta bleed).
2. Frequent strike shifts increase turnover and execution drag.
3. Positive PnL requires realized intraday volatility to exceed implied volatility often enough, which was rare in the tested window.

Loss is therefore a structural expectation, not a simulator bug.

## How to add a new strategy

Create a file in `src/strategies/` and subclass `Strategy`:

```python
# src/strategies/my_strategy.py
from src.engine import Strategy, MarketState, Order

class MyStrategy(Strategy):
    def generate_signals(self, state: MarketState) -> list[Order]:
        # state gives you: futures_price, available_strikes,
        #   current_positions, price_cache, expiry, etc.
        # Return a list of Order(instrument, "BUY"/"SELL") objects.
        return []
```

Then swap it into `scripts/run_backtest.py`:

```python
from src.strategies.my_strategy import MyStrategy
engine = BacktestEngine(strategy=MyStrategy())
results = engine.run()
```

The engine handles execution, PnL tracking, MTM, and day-end close — the strategy only emits orders.

## Outputs reviewers typically check first

Generated in `outputs/`:

1. **trade_log.csv** — fill-level audit trail with timestamp, instrument, side, price, quantity, lots, reason, hold duration.
2. **pnl_log.csv** — explicit `realized_pnl` and `unrealized_pnl` split for accounting correctness.
3. **tick_log.csv** — periodic mark-to-market snapshots.
4. **daily_summary.csv** — per-day and per-underlier realized PnL, strike changes, expiry-day flag.
5. **summary_stats.csv** — aggregate metrics.
6. **tearsheet.png** and supporting charts.

## Architecture and accounting guarantees

1. **Strategy self-containment:** The strategy emits orders only. It does not read CSVs, update portfolio state, or compute PnL.
2. **Strategy-agnostic engine:** Engine loops over timestamps and executes orders without knowledge of straddle-specific details.
3. **Realized vs unrealized split:** `realized_pnl` updates only on exits. `unrealized_pnl` updates on every mark-to-market snapshot.
4. **Day-end close:** All open positions are force-closed at market close and tagged `DAY_END_CLOSE`.
5. **Phantom-trade guard:** When desired strike is unchanged, the strategy does not sell/rebuy same instruments.
6. **Lot-size-aware rupee accounting:** PnL is multiplied by lot size from `config/config.yaml` (NIFTY 50, BANKNIFTY 25).

## Configuration checklist

All externalized in `config/config.yaml`:

1. `start_date` and `end_date`
2. `lot_sizes` per underlier
3. `transaction_cost_per_lot` (can be zero)
4. market `open_time` / `close_time`
5. data and output paths

## AI usage disclosure

AI tools were used for scaffolding support (documentation structure and minor boilerplate).
Strategy logic, PnL accounting rules, strike-rebalance guard, and simulation behavior were implemented and validated manually against assignment requirements and generated outputs.
