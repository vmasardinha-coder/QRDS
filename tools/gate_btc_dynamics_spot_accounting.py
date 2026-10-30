"""Pure prospective spot accounting, disconnected from production and brokers.

No strategy selection, signals, orders, price fetching, margin, derivatives,
short borrowing or activation of Gateway profiles. All inputs are explicit.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
import re


def number(value: str | Decimal) -> Decimal:
    if not isinstance(value, (str, Decimal)):
        raise ValueError("decimal inputs must be strings or Decimal, never floats")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("nonfinite decimal")
    return result


def timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timezone required")
    return result.astimezone(timezone.utc)


def digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                      allow_nan=False).encode()).hexdigest()


def check_hash(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("exact SHA256 provenance required")


@dataclass(frozen=True)
class SpotInstrument:
    asset: str
    exact_identity: str
    venue: str
    market: str
    quote_currency: str
    lot_size: str
    fee_bps_per_side: str
    slippage_bps_per_side: str
    instrument_type: str = "SPOT"


@dataclass(frozen=True)
class SpotProtocol:
    protocol_id: str
    base_currency: str
    activation_at_utc: str
    initial_cash: str
    max_price_age_seconds: int
    instruments: tuple[SpotInstrument, ...]

    def validate(self) -> None:
        if not self.protocol_id or not self.base_currency or number(self.initial_cash) <= 0:
            raise ValueError("protocol identity, currency and positive seed required")
        timestamp(self.activation_at_utc)
        if type(self.max_price_age_seconds) is not int or self.max_price_age_seconds <= 0:
            raise ValueError("positive integer price-age bound required")
        if not isinstance(self.instruments, tuple) or not self.instruments:
            raise ValueError("nonempty immutable instrument bindings required")
        if len({i.asset for i in self.instruments}) != len(self.instruments):
            raise ValueError("duplicate asset binding")
        if len({(i.venue, i.market) for i in self.instruments}) != len(self.instruments):
            raise ValueError("duplicate venue/market binding")
        for i in self.instruments:
            if not all(isinstance(v, str) and v.strip() for v in
                       [i.asset, i.exact_identity, i.venue, i.market, i.quote_currency]):
                raise ValueError("incomplete exact instrument binding")
            if i.instrument_type != "SPOT" or i.quote_currency != self.base_currency:
                raise ValueError("only same-currency unlevered spot is implemented")
            if i.asset in {"CASH", self.base_currency}:
                raise ValueError("base cash cannot be bound as traded inventory")
            if number(i.lot_size) <= 0:
                raise ValueError("positive lot size required")
            for cost in [i.fee_bps_per_side, i.slippage_bps_per_side]:
                if not 0 <= number(cost) < 10000:
                    raise ValueError("cost must be explicit and in [0, 10000) bps")

    @property
    def sha256(self) -> str:
        self.validate()
        return digest(asdict(self))


@dataclass(frozen=True)
class SpotState:
    protocol_sha256: str
    cash: Decimal
    positions: tuple[tuple[str, Decimal], ...]
    as_of_utc: str
    event_ids: tuple[str, ...]
    chain_sha256: str
    total_fees: Decimal
    total_slippage: Decimal


@dataclass(frozen=True)
class PaperFill:
    event_id: str
    asset: str
    quantity_delta: str
    signal_published_at_utc: str
    signal_sha256: str
    quote_price: str
    quote_at_utc: str
    quote_sha256: str
    executed_at_utc: str


@dataclass(frozen=True)
class Mark:
    price: str
    at_utc: str
    source_sha256: str


def genesis(protocol: SpotProtocol) -> SpotState:
    protocol_hash = protocol.sha256
    return SpotState(protocol_hash, number(protocol.initial_cash), (),
                     protocol.activation_at_utc, (),
                     digest({"protocol_sha256": protocol_hash, "event": "GENESIS_CASH_ONLY"}),
                     Decimal(0), Decimal(0))


def require_protocol(state: SpotState, protocol: SpotProtocol) -> None:
    if state.protocol_sha256 != protocol.sha256:
        raise ValueError("protocol changed; start a new independent ledger")


def price_at(price: str, observed: str, execution: str, provenance: str,
             max_age: int) -> Decimal:
    check_hash(provenance)
    value = number(price)
    age = (timestamp(execution) - timestamp(observed)).total_seconds()
    if value <= 0 or not 0 <= age <= max_age:
        raise ValueError("nonpositive, future or stale price")
    return value


def apply_fill(state: SpotState, protocol: SpotProtocol,
               fill: PaperFill) -> tuple[SpotState, dict]:
    """Return a new state atomically. Modeled slippage is included in fill price."""
    require_protocol(state, protocol)
    check_hash(fill.signal_sha256)
    if not fill.event_id or fill.event_id in state.event_ids:
        raise ValueError("missing or duplicate event id")
    activation = timestamp(protocol.activation_at_utc)
    publication = timestamp(fill.signal_published_at_utc)
    quote_time = timestamp(fill.quote_at_utc)
    execution = timestamp(fill.executed_at_utc)
    if not activation <= publication < quote_time <= execution:
        raise ValueError("signal publication must precede prospective execution quote")
    if execution < timestamp(state.as_of_utc):
        raise ValueError("out-of-order event")
    bindings = {i.asset: i for i in protocol.instruments}
    if fill.asset not in bindings:
        raise ValueError("unbound asset")
    instrument = bindings[fill.asset]
    quote = price_at(fill.quote_price, fill.quote_at_utc, fill.executed_at_utc,
                     fill.quote_sha256, protocol.max_price_age_seconds)
    with localcontext() as ctx:
        ctx.prec = 40
        quantity = number(fill.quantity_delta)
        if not quantity or quantity % number(instrument.lot_size) != 0:
            raise ValueError("nonzero whole-lot quantity required")
        positions = dict(state.positions)
        next_quantity = positions.get(fill.asset, Decimal(0)) + quantity
        if next_quantity < 0:
            raise ValueError("spot short borrowing is not implemented")
        side = Decimal(1) if quantity > 0 else Decimal(-1)
        execution_price = quote * (1 + side * number(instrument.slippage_bps_per_side) / 10000)
        notional = abs(quantity * execution_price)
        fee = notional * number(instrument.fee_bps_per_side) / 10000
        slippage = abs(quantity) * abs(execution_price - quote)
        cash = state.cash - quantity * execution_price - fee
        if cash < 0:
            raise ValueError("insufficient cash; borrowing is not implemented")
        if next_quantity:
            positions[fill.asset] = next_quantity
        else:
            positions.pop(fill.asset, None)
        receipt = {
            "event": asdict(fill), "protocol_sha256": state.protocol_sha256,
            "previous_chain_sha256": state.chain_sha256,
            "quantity_delta": str(quantity), "execution_price": str(execution_price),
            "traded_notional": str(notional), "fee": str(fee),
            "slippage_cost_already_in_execution_price": str(slippage),
            "cash_after": str(cash),
            "positions_after": {k: str(v) for k, v in sorted(positions.items())},
            "research_only": True, "production_activation": False,
            "orders": 0, "real_capital": 0,
        }
        chain = digest(receipt)
        next_state = SpotState(state.protocol_sha256, cash, tuple(sorted(positions.items())),
                               fill.executed_at_utc, state.event_ids + (fill.event_id,), chain,
                               state.total_fees + fee, state.total_slippage + slippage)
        return next_state, dict(receipt, chain_sha256=chain)


def mark_nav(state: SpotState, protocol: SpotProtocol, at_utc: str,
             marks: dict[str, Mark]) -> dict:
    """No missing price becomes zero return; every held asset needs a valid mark."""
    require_protocol(state, protocol)
    if timestamp(at_utc) < timestamp(state.as_of_utc):
        raise ValueError("valuation precedes current ledger state")
    used = {}
    with localcontext() as ctx:
        ctx.prec = 40
        value = state.cash
        for asset, quantity in state.positions:
            if asset not in marks:
                raise ValueError("missing mark for held asset: " + asset)
            mark = marks[asset]
            # A valuation cannot use a quote predating the latest accounting event.
            if timestamp(mark.at_utc) < timestamp(state.as_of_utc):
                raise ValueError("mark precedes latest accounting event")
            price = price_at(mark.price, mark.at_utc, at_utc, mark.source_sha256,
                             protocol.max_price_age_seconds)
            value += quantity * price
            used[asset] = asdict(mark)
        return {
            "nav": str(value), "cash": str(state.cash), "currency": protocol.base_currency,
            "return_since_activation": str(value / number(protocol.initial_cash) - 1),
            "at_utc": at_utc, "marks": used, "total_fees": str(state.total_fees),
            "total_slippage_already_in_fills": str(state.total_slippage),
            "protocol_sha256": state.protocol_sha256, "chain_sha256": state.chain_sha256,
            "scientific_credit": 0, "production_activation": False,
            "orders": 0, "real_capital": 0,
        }
