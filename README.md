# NSE Options Backtesting Engine with ATM Straddle strategy implementation.

## Run in 3 commands

```bash
pip install -r requirements.txt
python scripts/run_backtest.py
pytest -q
```

Input data path is configured in config/config.yaml under paths.data_dir.
Backtest outputs are written to outputs/.

## Project structure

```
MFT/
├── config/
│   └── config.yaml
├── src/
│   ├── engine.py
│   └── strategies/
│       └── atm_straddle.py
├── tests/
│   └── test_project_contract.py
├── outputs/
├── scripts/
│   └── run_backtest.py
├── engine.py
├── data_loader.py
├── reporting.py
├── logger.py
├── requirements.txt
└── README.md
```

Notes:
The execution engine is strategy-agnostic and does not contain strategy-specific logic.
The strategy is self-contained in src/strategies/atm_straddle.py.

## What this submission does

One-second event-driven simulation over NSE futures and options data.

At each timestamp the strategy selects ATM strike from futures price, holds CE+PE straddle, rebalances only when strike changes, and force-closes all open positions at day end.

## Results snapshot (Nov 2022 run)

| Metric | NIFTY | BANKNIFTY | Combined |
|---|---:|---:|---:|
| Total Realized PnL (Rs) | -20,217.50 | -25,853.75 | -46,071.25 |
| Total Trades | 10,456 | 11,696 | 22,152 |
| Avg Trades/Day | 747 | 836 | 1,582 |
| Sharpe (daily annualized) | -11.08 | -17.90 | -15.76 |
| Winning Days | - | - | 2/14 |

| Additional risk metrics | Value |
|---|---:|
| Max Daily PnL (Rs) | 2,650.00 |
| Min Daily PnL (Rs) | -10,447.50 |
| Max Drawdown (Rs) | -47,222.50 |
| Median Hold Duration (s) | 4.0 |
| Expiry Day PnL (Rs) | -13,586.25 |

CE leg total PnL: -13,966.25
PE leg total PnL: -32,105.00

## Why this strategy loses (expected)

This is a long-gamma, short-theta profile. In normal conditions:

1. Both bought options decay with time (theta bleed).
2. Frequent strike shifts increase turnover and execution drag.
3. Positive PnL requires realized intraday volatility to exceed implied volatility often enough, which was rare in the tested window.

Loss is therefore a structural expectation, not a simulator bug.

## Outputs reviewers typically check first

Generated in outputs/:

1. trade_log.csv: fill-level audit trail with timestamp, instrument, side, price, quantity, lots, reason, hold duration.
2. pnl_log.csv: explicit realized_pnl and unrealized_pnl split for accounting correctness.
3. tick_log.csv: periodic mark-to-market snapshots.
4. daily_summary.csv: per-day and per-underlier realized PnL, strike changes, expiry-day flag.
5. summary_stats.csv: aggregate metrics.
6. tearsheet.png and supporting charts.

## Architecture and accounting guarantees

1. Strategy self-containment:
The strategy emits orders only. It does not read CSVs, update portfolio state, or compute PnL.

2. Strategy-agnostic engine:
Engine loops over timestamps and executes orders without knowledge of straddle-specific details.

3. Realized vs unrealized split:
realized_pnl updates only on exits.
unrealized_pnl updates on every mark-to-market snapshot.

4. Day-end close:
All open positions are force-closed at market close and tagged DAY_END_CLOSE.

5. Phantom-trade guard:
When desired strike is unchanged, the strategy does not sell/rebuy same instruments.

6. Lot-size-aware rupee accounting:
PnL is multiplied by lot size from config/config.yaml (NIFTY 50, BANKNIFTY 25).

## Configuration checklist

All externalized in config/config.yaml:

1. start_date and end_date
2. lot_sizes per underlier
3. transaction_cost_per_lot (can be zero)
4. market open/close time
5. data and output paths

## AI usage disclosure

AI tools were used for scaffolding support (documentation structure and minor boilerplate).
Strategy logic, PnL accounting rules, strike-rebalance guard, and simulation behavior were implemented and validated manually against assignment requirements and generated outputs.
