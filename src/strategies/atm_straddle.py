"""ATM straddle strategy implementation kept self-contained for review clarity."""

from typing import Dict, List, Optional

from ..data_loader import round_to_strike
from ..logger import get_logger
from ..engine import MarketState, Order, Strategy

log = get_logger()


class ATMStraddle(Strategy):
    """
    Hold one ATM CE+PE straddle and rebalance only when ATM strike changes.

    This strategy intentionally avoids loading data, managing PnL, or touching
    execution mechanics; those concerns belong to the engine.
    """

    def __init__(self) -> None:
        self._current_strike: Dict[str, Optional[int]] = {}

    def on_day_start(self, trading_date: str, underlier: str):
        self._current_strike[underlier] = None
        log.debug("ATMStraddle reset for %s on %s", underlier, trading_date)

    def generate_signals(self, state: MarketState) -> List[Order]:
        orders: List[Order] = []
        if not state.available_strikes:
            return orders

        desired_strike = round_to_strike(state.futures_price, state.strike_step)
        if desired_strike not in state.available_strikes:
            desired_strike = min(
                state.available_strikes,
                key=lambda strike: abs(strike - state.futures_price),
            )

        ce_new = f"{state.underlier}{state.expiry}{desired_strike}CE"
        pe_new = f"{state.underlier}{state.expiry}{desired_strike}PE"

        # Phantom-trade guard: do nothing when desired straddle is already open.
        if ce_new in state.current_positions and pe_new in state.current_positions:
            self._current_strike[state.underlier] = desired_strike
            return orders

        previous = self._current_strike.get(state.underlier)
        if desired_strike == previous:
            return orders

        if previous is not None:
            ce_old = f"{state.underlier}{state.expiry}{previous}CE"
            pe_old = f"{state.underlier}{state.expiry}{previous}PE"
            if ce_old in state.current_positions:
                orders.append(Order(ce_old, "SELL", reason="STRIKE_CHANGE"))
            if pe_old in state.current_positions:
                orders.append(Order(pe_old, "SELL", reason="STRIKE_CHANGE"))

        ce_px = state.get_option_price(ce_new)
        pe_px = state.get_option_price(pe_new)
        if ce_px is None or pe_px is None:
            if previous is not None and previous != desired_strike:
                self._current_strike[state.underlier] = None
            return orders

        orders.append(Order(ce_new, "BUY", reason="STRADDLE_ENTRY"))
        orders.append(Order(pe_new, "BUY", reason="STRADDLE_ENTRY"))
        self._current_strike[state.underlier] = desired_strike
        return orders
