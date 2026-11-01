"""Atomic research-only rebalance with audited MARKET quantity/notional checks.

No venue/account approval, discovery, calendar, activation or broker calls.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from decimal import Decimal, localcontext

from tools import gate_btc_dynamics_spot_accounting as book
from tools import gate_btc_dynamics_spot_market_audit as market
from tools import gate_btc_dynamics_target_intake as intake


@dataclass(frozen=True)
class NotionalReference:
    asset: str
    exact_identity: str
    quote_currency: str
    price: str
    at_utc: str
    source_sha256: str
    kind: str  # EXCHANGE_REFERENCE, VWAP, or LAST_PRICE
    avg_price_minutes: int | None
    exchange_reference_status: str  # PRESENT or NULL_CONFIRMED
    exchange_reference_status_sha256: str


# These filters are retained in the receipt, but cannot be proved by a pure
# cash-only simulator. Unknown filters (e.g. MAX_POSITION) block this wrapper.
OUTSIDE_CHECKED_SCOPE = {
    "PRICE_FILTER": "MARKET has no limit/stop price",
    "PERCENT_PRICE": "MARKET has no limit/stop price",
    "PERCENT_PRICE_BY_SIDE": "MARKET has no limit/stop price",
    "ICEBERG_PARTS": "no iceberg orders in this simulation",
    "TRAILING_DELTA": "no trailing orders in this simulation",
    "MAX_NUM_ORDERS": "account-wide order counters unavailable",
    "MAX_NUM_ALGO_ORDERS": "account-wide order counters unavailable",
    "MAX_NUM_ICEBERG_ORDERS": "account-wide order counters unavailable",
    "MAX_NUM_ORDER_LISTS": "account-wide order counters unavailable",
    "MAX_NUM_ORDER_AMENDS": "account-wide order counters unavailable",
}
CHECKED = {"LOT_SIZE", "MARKET_LOT_SIZE", "MIN_NOTIONAL", "NOTIONAL"}


def _quantity(quantity: Decimal, filters: dict) -> None:
    for key in ("LOT_SIZE", "MARKET_LOT_SIZE"):
        if key not in filters:
            continue
        f = filters[key]
        lo, hi, step = (book.number(f[k]) for k in ("minQty", "maxQty", "stepSize"))
        if quantity < lo or quantity > hi or (step > 0 and quantity % step != 0):
            raise ValueError("quantity violates " + key)


def _reference(ref: NotionalReference, instrument: book.SpotInstrument,
               minutes: int, publication: str, execution: str, max_age: int) -> Decimal:
    if (ref.asset, ref.exact_identity, ref.quote_currency) != (
            instrument.asset, instrument.exact_identity, instrument.quote_currency):
        raise ValueError("notional reference identity/currency mismatch")
    book.check_hash(ref.exchange_reference_status_sha256)
    if ref.exchange_reference_status == "PRESENT":
        if ref.kind != "EXCHANGE_REFERENCE" or ref.avg_price_minutes is not None:
            raise ValueError("available exchange reference must take precedence")
    elif ref.exchange_reference_status == "NULL_CONFIRMED":
        wanted = "VWAP" if minutes else "LAST_PRICE"
        if ref.kind != wanted or type(ref.avg_price_minutes) is not int or ref.avg_price_minutes != minutes:
            raise ValueError("notional reference window/type mismatch")
    else:
        raise ValueError("explicit exchange reference availability evidence required")
    if book.timestamp(ref.at_utc) <= book.timestamp(publication):
        raise ValueError("notional reference must follow target publication")
    return book.price_at(ref.price, ref.at_utc, execution, ref.source_sha256, max_age)


def rebalance_market_checked(state: book.SpotState, protocol: book.SpotProtocol,
                             admission: dict, profile: str, audit: dict, *,
                             rebalance_id: str, quotes: dict[str, book.Mark],
                             notional_references: dict[str, NotionalReference],
                             executed_at_utc: str, max_metadata_age_seconds: int):
    """Simulate, validate every fill, then return one sealed state or raise.

    Invalid orders abort the whole rebalance. No clipping, splitting, reweighting
    or synthetic cash fallback is added. The input state is immutable and no
    externally visible writes occur, including when a late BUY fails after SELLs.
    """
    book.require_protocol(state, protocol)
    payload = {k: v for k, v in audit.items() if k != "audit_sha256"}
    if book.digest(payload) != audit.get("audit_sha256"):
        raise ValueError("market audit changed")
    if audit.get("schema") != "gate_btc.dynamics_spot_market_audit.v1":
        raise ValueError("unsupported market audit")
    weights = intake.spot_weights(admission, profile)
    if audit["target_admission_sha256"] != admission["admission_sha256"]:
        raise ValueError("market audit belongs to another target admission")
    entry = audit["profiles"].get(profile)
    if not entry or entry["target_weights"] != weights or entry["market_metadata_complete"] is not True:
        raise ValueError("incomplete or mismatched profile metadata")
    if type(max_metadata_age_seconds) is not int or max_metadata_age_seconds <= 0:
        raise ValueError("positive integer execution metadata age bound required")
    if max_metadata_age_seconds > audit["max_metadata_age_seconds"]:
        raise ValueError("execution metadata bound cannot relax audited bound")
    capture, execution = book.timestamp(audit["captured_at_utc"]), book.timestamp(executed_at_utc)
    if book.timestamp(audit["audited_at_utc"]) > execution:
        raise ValueError("audit unavailable at execution")
    if not 0 <= (execution - capture).total_seconds() <= max_metadata_age_seconds:
        raise ValueError("future or stale execution metadata")
    bindings = {i.asset: i for i in protocol.instruments}
    required = set(dict(state.positions)) | {
        a for a, w in weights.items() if a != "CASH" and book.number(w) > 0}
    filters = {}
    for asset in sorted(required):
        spec = audit["markets"].get(asset)
        instrument = bindings.get(asset)
        if not spec or spec["metadata_complete"] is not True or instrument is None:
            raise ValueError("held/target asset has no complete audited binding: " + asset)
        if (instrument.venue, instrument.market, instrument.exact_identity,
                instrument.quote_currency) != (
                "BINANCE", spec["candidate_market"], spec["candidate_identity"], audit["quote_currency"]):
            raise ValueError("protocol/audited market binding mismatch")
        f = market._filters({"filters": list(spec["filters"].values())})
        if set(f) - CHECKED - set(OUTSIDE_CHECKED_SCOPE):
            raise ValueError("unsupported execution filter")
        if book.number(instrument.lot_size) != book.number(f["LOT_SIZE"]["stepSize"]):
            raise ValueError("protocol lot differs from audited LOT_SIZE")
        filters[asset] = f
    next_state, rebalance = intake.rebalance_admitted(state, protocol, admission, profile,
        rebalance_id=rebalance_id, quotes=quotes, executed_at_utc=executed_at_utc)
    checks = []
    used_references = set()
    with localcontext() as ctx:
        ctx.prec = 40
        for fill in rebalance["rebalance_receipt"]["fills"]:
            asset = fill["event"]["asset"]
            quantity = abs(book.number(fill["quantity_delta"]))
            f = filters[asset]
            _quantity(quantity, f)
            key = "NOTIONAL" if "NOTIONAL" in f else "MIN_NOTIONAL"
            n = f[key]
            minimum_applies = n["applyMinToMarket"] if key == "NOTIONAL" else n["applyToMarket"]
            maximum_applies = key == "NOTIONAL" and n["applyMaxToMarket"]
            ref = None
            notional = None
            if minimum_applies or maximum_applies:
                if asset not in notional_references:
                    raise ValueError("missing required notional reference: " + asset)
                ref = notional_references[asset]
                price = _reference(ref, bindings[asset], n["avgPriceMins"],
                    admission["source_available_at_utc"], executed_at_utc, protocol.max_price_age_seconds)
                notional = quantity * price
                if minimum_applies and notional < book.number(n["minNotional"]):
                    raise ValueError("below minimum market notional: " + asset)
                if maximum_applies and notional > book.number(n["maxNotional"]):
                    raise ValueError("above maximum market notional: " + asset)
                used_references.add(asset)
            checks.append(dict(asset=asset, quantity=str(quantity),
                quantity_filters={k: v for k, v in f.items() if k in {"LOT_SIZE", "MARKET_LOT_SIZE"}},
                notional_filter=n, notional_reference=asdict(ref) if ref else None,
                filter_notional=str(notional) if notional is not None else None,
                outside_checked_scope={k: OUTSIDE_CHECKED_SCOPE[k] for k in f if k in OUTSIDE_CHECKED_SCOPE}))
    if set(notional_references) != used_references:
        raise ValueError("unused or unrelated notional reference")
    receipt = dict(event="MARKET_CONSTRAINTS_RESEARCH_SEAL", rebalance_id=rebalance_id,
        previous_state_chain_sha256=state.chain_sha256,
        checked_rebalance_chain_sha256=next_state.chain_sha256,
        market_audit_sha256=audit["audit_sha256"], metadata_sha256=audit["metadata_sha256"],
        executed_at_utc=executed_at_utc, max_metadata_age_seconds=max_metadata_age_seconds,
        checks=checks, rebalance=rebalance, research_only=True, production_activation=False,
        exchange_order_eligibility_proven=False, account_limits_verified=False,
        economic_result_available=False, economic_observations_created=0, orders=0, real_capital=0)
    seal = book.digest(receipt)
    return replace(next_state, chain_sha256=seal,
        event_ids=next_state.event_ids + ("MARKET_CHECK:" + rebalance_id,)), dict(receipt, chain_sha256=seal)
