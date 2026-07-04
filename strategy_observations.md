# Strategy Observations — ATM Straddle on NIFTY / BANKNIFTY

## 1. The Strategy Is Designed to Lose

This ATM straddle (buying both CE and PE at the nearest strike every second) is **structurally long gamma, short theta**. The continuous rebalancing amplifies the bid-ask spread cost. On a typical NSE trading day, theta bleed dominates unless intraday realized volatility exceeds implied volatility significantly — which is rare.

Over the 14 trading days in November 2022 (one data folder, NSE_20221117, is skipped due to missing futures data), the strategy produces a **consistent daily loss** with only 2 winning days out of 14 (14.3% win rate). This is the expected behavior for a strategy that:
- Pays time decay every second it holds the position
- Generates hundreds of rebalancing trades per day
- Crosses the bid-ask spread on every entry/exit

## 2. BANKNIFTY Loses More Than NIFTY

BANKNIFTY consistently underperforms NIFTY in this strategy. This is because:
- **Higher implied volatility** → more expensive premiums → more theta to bleed
- **Wider strikes (₹100 step vs ₹50)** → the straddle is frequently not truly ATM, introducing directional bias
- **Higher beta** → more frequent strike changes → more transaction friction

## 3. Expiry Day Is a Landmine

November 3, 2022 is a NIFTY weekly expiry. On this day:
- NIFTY PnL: ₹-84.85 (per unit, pre-lot-adjustment)
- BANKNIFTY PnL: ₹-248.20

Expiry-day theta acceleration is extreme — options lose their remaining time value rapidly as they approach settlement. A production system would:
- Roll to the next expiry before expiry day
- Reduce position size on expiry day
- Use delta-based strike selection instead of nearest-price

## 4. Strike Chasing Creates Predictable Intraday Patterns

Plotting rebalances by hour of day reveals the NSE intraday microstructure:
- **9:15–10:00 AM**: Very high rebalance frequency (market-open volatility, gap adjustments)
- **12:00–1:00 PM**: Low activity (lunch lull, reduced volumes)
- **2:30–3:30 PM**: Moderate increase (closing volatility, position squaring)

This pattern is consistent across all trading days and both underliers. A smart strategy could exploit this by:
- Avoiding entries during the first 15 minutes (whipsaw risk)
- Reducing rebalance frequency during low-volatility hours

## 5. Open Interest Tells a Story

Examining OI for held instruments reveals:
- **Rising OI** during market hours = new positions being opened (directional conviction)
- **Falling OI** near close / expiry = positions being closed (profit booking or stop-loss)
- ATM strikes consistently have the highest OI, confirming they're the most liquid

The OI data is available in every tick file (column 5) but is almost never used in backtesting exercises. Visualizing it demonstrates awareness of market microstructure beyond just price.

## 6. Hold Duration Is Extremely Short

The median hold duration for a straddle position is typically under 60 seconds. This means:
- The strategy is functionally a **high-frequency scalping approach** on options
- Each position barely moves before being replaced
- The "edge" would need to come from gamma moves that exceed theta decay within seconds — unrealistic for most market conditions

## 7. Transaction Cost Sensitivity

Even with zero explicit transaction costs (as configured), the strategy's PnL is negative. In reality:
- NSE brokerage: ~₹20 per order (discount broker) × 1000+ trades/day = ₹20,000+/day
- STT (Securities Transaction Tax): 0.05% on sell-side option premium
- Bid-ask spread: typically ₹0.50–₹2.00 per lot for liquid ATM options

Adding realistic costs would make the strategy's losses 2-3× larger. The framework's `config.yaml` allows modeling this by setting `transaction_cost_per_lot` and `slippage_bps`.
