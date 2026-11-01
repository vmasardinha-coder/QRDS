"""Atomic, deterministic spot rebalancing over the accepted accounting kernel.

This is an accounting primitive, not a Gateway strategy or production runner.
It consumes explicit future signal/quote/protocol bindings and never selects
rebalance dates, stop rules, venues, instruments or funding assumptions.
"""
from __future__ import annotations
from dataclasses import asdict, replace
from decimal import Decimal, localcontext, ROUND_FLOOR
import re
from tools import gate_btc_dynamics_spot_accounting as book


def floor_lot(quantity: Decimal, lot: Decimal) -> Decimal:
    if quantity < 0 or lot <= 0:
        raise ValueError("nonnegative quantity and positive lot required")
    return (quantity / lot).to_integral_value(rounding=ROUND_FLOOR) * lot


def rebalance(state: book.SpotState, protocol: book.SpotProtocol, *,
              rebalance_id: str, target_weights: dict[str, str],
              signal_published_at_utc: str, signal_sha256: str,
              quotes: dict[str, book.Mark], executed_at_utc: str):
    """Return a fully accepted new state and receipt, or leave input untouched.

    Sizing policy is explicit: targets use pre-trade reference NAV; sell excess
    lots first; reserve CASH's pre-trade target; scale all requested purchases
    proportionally to affordable cash including fees/adverse slippage, then
    round purchases down to lots. No allocation is silently renormalized.

    Post-trade reference valuation reuses input quotes for reconciliation only.
    It is NOT mark_nav: economic valuation still needs fresh post-fill marks
    under the original kernel's unchanged freshness contract.
    """
    book.require_protocol(state, protocol)
    book.check_hash(signal_sha256)
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", rebalance_id):
        raise ValueError("safe nonempty rebalance id required")
    seal_id = "REBALANCE:" + rebalance_id
    if seal_id in state.event_ids:
        raise ValueError("duplicate rebalance")
    activation = book.timestamp(protocol.activation_at_utc)
    publication = book.timestamp(signal_published_at_utc)
    execution = book.timestamp(executed_at_utc)
    if not activation <= publication < execution or execution < book.timestamp(state.as_of_utc):
        raise ValueError("invalid prospective signal/execution order")
    bindings = {i.asset: i for i in protocol.instruments}
    if "CASH" not in target_weights:
        raise ValueError("explicit CASH target required")
    if set(target_weights) - set(bindings) - {"CASH"}:
        raise ValueError("unbound target asset")
    if len(dict(state.positions)) != len(state.positions):
        raise ValueError("duplicate held asset")
    if set(dict(state.positions)) - set(bindings):
        raise ValueError("unbound held asset")
    with localcontext() as ctx:
        ctx.prec = 40
        weights = {asset: book.number(value) for asset, value in target_weights.items()}
        if any(w < 0 for w in weights.values()) or sum(weights.values()) != 1:
            raise ValueError("spot targets must be nonnegative and sum exactly to1")
        held = dict(state.positions)
        if not state.cash.is_finite() or state.cash < 0:
            raise ValueError("invalid initial cash")
        for asset, quantity in held.items():
            lot = book.number(bindings[asset].lot_size)
            if not quantity.is_finite() or quantity < 0 or quantity % lot:
                raise ValueError("invalid held quantity or lot")
        required = set(held) | {a for a, w in weights.items() if a != "CASH" and w > 0}
        prices = {}
        for asset in sorted(required):
            if asset not in quotes:
                raise ValueError("missing quote: " + asset)
            mark = quotes[asset]
            qt = book.timestamp(mark.at_utc)
            if not publication < qt <= execution or qt < book.timestamp(state.as_of_utc):
                raise ValueError("quote must follow signal/current state and precede execution")
            prices[asset] = book.price_at(mark.price, mark.at_utc, executed_at_utc,
                mark.source_sha256, protocol.max_price_age_seconds)
        nav_before = state.cash + sum(held.get(a, Decimal(0)) * prices[a] for a in required)
        if nav_before <= 0:
            raise ValueError("positive pre-trade reference NAV required")
        desired = {a: floor_lot(nav_before * weights.get(a, Decimal(0)) / prices[a],
                    book.number(bindings[a].lot_size)) for a in required}
        next_state = state
        fills = []
        def execute(asset, quantity, side):
            nonlocal next_state
            mark = quotes[asset]
            fill = book.PaperFill(seal_id + ":" + side + ":" + asset, asset, str(quantity),
                signal_published_at_utc, signal_sha256, mark.price, mark.at_utc,
                mark.source_sha256, executed_at_utc)
            next_state, receipt = book.apply_fill(next_state, protocol, fill)
            fills.append(receipt)
        for asset in sorted(required):
            if desired[asset] < held.get(asset, Decimal(0)):
                execute(asset, desired[asset] - held[asset], "SELL")
        after_sales = dict(next_state.positions)
        requested = {a: desired[a] - after_sales.get(a, Decimal(0))
                     for a in sorted(required) if desired[a] > after_sales.get(a, Decimal(0))}
        def purchase_cost(asset, quantity):
            i = bindings[asset]
            execution_price = prices[asset] * (1 + book.number(i.slippage_bps_per_side) / 10000)
            return quantity * execution_price * (1 + book.number(i.fee_bps_per_side) / 10000)
        requested_cost = sum((purchase_cost(a, q) for a, q in requested.items()), Decimal(0))
        cash_target = weights["CASH"] * nav_before
        available = max(Decimal(0), next_state.cash - cash_target)
        scale = min(Decimal(1), available / requested_cost) if requested_cost else Decimal(1)
        purchases = {a: floor_lot(q * scale, book.number(bindings[a].lot_size))
                     for a, q in requested.items()}
        # Bound the rare Decimal rounding edge without changing asset priority.
        for _ in range(len(purchases) + 1):
            if sum((purchase_cost(a, q) for a, q in purchases.items()), Decimal(0)) <= available:
                break
            nonzero = [a for a, q in purchases.items() if q > 0]
            if not nonzero:
                raise ValueError("purchase sizing cannot fit cash")
            asset = sorted(nonzero, key=lambda a: (-purchase_cost(a, purchases[a]), a))[0]
            purchases[asset] -= book.number(bindings[asset].lot_size)
        else:
            raise ValueError("purchase rounding bound exhausted")
        for asset in sorted(purchases):
            if purchases[asset]:
                execute(asset, purchases[asset], "BUY")
        final_positions = dict(next_state.positions)
        reference_after = next_state.cash + sum(q * prices[a] for a, q in final_positions.items())
        fees = next_state.total_fees - state.total_fees
        slippage = next_state.total_slippage - state.total_slippage
        residual = nav_before - reference_after - fees - slippage
        if abs(residual) > max(Decimal(1), nav_before) * Decimal("1e-35"):
            raise ValueError("rebalance reconciliation failed")
        receipt = {
            "event": "SPOT_REBALANCE_SEAL", "event_id": seal_id,
            "protocol_sha256": protocol.sha256,
            "previous_state_chain_sha256": state.chain_sha256,
            "last_fill_chain_sha256": next_state.chain_sha256,
            "signal_sha256": signal_sha256, "signal_published_at_utc": signal_published_at_utc,
            "executed_at_utc": executed_at_utc,
            "sizing_policy": "PRE_TRADE_NAV_SELL_THEN_CASH_RESERVE_PRO_RATA_BUYS_FLOOR_LOTS",
            "target_weights": {a: str(w) for a, w in sorted(weights.items())},
            "quotes": {a: asdict(quotes[a]) for a in sorted(required)},
            "desired_reference_quantities": {a: str(q) for a, q in sorted(desired.items())},
            "purchase_scale": str(scale), "cash_target_reference": str(cash_target),
            "reference_nav_before": str(nav_before),
            "reference_nav_after": str(reference_after),
            "fresh_post_execution_nav_available": False,
            "economic_result_available": False,
            "achieved_reference_weights": {
                **{a: str(q * prices[a] / reference_after) for a, q in sorted(final_positions.items())},
                "CASH": str(next_state.cash / reference_after)},
            "cash_after": str(next_state.cash),
            "modeled_fees": str(fees), "modeled_slippage_already_in_fills": str(slippage),
            "traded_notional": str(sum((book.number(f["traded_notional"]) for f in fills), Decimal(0))),
            "reconciliation_residual": str(residual), "fills": fills,
            "scientific_credit": 0, "production_activation": False,
            "orders": 0, "real_capital": 0,
        }
        seal_hash = book.digest(receipt)
        final_state = replace(next_state, as_of_utc=executed_at_utc,
            event_ids=next_state.event_ids + (seal_id,), chain_sha256=seal_hash)
        return final_state, dict(receipt, chain_sha256=seal_hash)
