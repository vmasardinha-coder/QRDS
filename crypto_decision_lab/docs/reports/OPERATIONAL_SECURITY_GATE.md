# QRDS/QOS • Gate BTC • Operational Security Review Gate v1

Sprint **8V** adds a research-only operational security review gate to the QRDS/QOS evidence stack.

This gate answers one narrow question:

> Is the research stack still locked away from credentials, authenticated exchange access, execution pathways, order endpoints, signals, recommendations, allocation, and real capital?

It does **not** answer:

- buy;
- sell;
- allocate;
- position size;
- place orders;
- connect to an authenticated exchange;
- use real capital;
- leave `INTERACTIVE_RESEARCH_ONLY` mode.

## Expected upstream inputs

The stack-derived wrapper expects prior artifacts from:

- 8L Evidence Quality;
- 8M Evidence Drilldown;
- 8N Evidence Timeline;
- 8O Research Promotion;
- 8P Human Review / Policy Lock;
- 8Q Out-of-Sample Validation;
- 8R Paper Trading;
- 8U Risk Model.

## Security criteria

The gate checks that:

- policy lock remains active;
- API keys are not present and not required;
- account connections are not required;
- authenticated exchange connections are not used;
- execution layers and order endpoints are absent/disabled;
- Binance remains `SIMULATION_FIXTURE_REPLAY`;
- OKX remains public/cache/offline only;
- Bybit remains blocked/pending;
- secrets scan state is `PASS`;
- upstream reports keep all operational safety flags false;
- security review state is recorded.

## Usage

From the repo root:

```bash
bash qrds_operational_security_from_stack_serve.sh
```

This refreshes the 8L → 8R evidence stack, regenerates the 8U risk-model artifact under the stack output, generates the 8V operational-security packet, starts a local server on a free port, and prints the Codespaces Ports instruction.

Manual use:

```bash
bash qrds_operational_security_serve.sh \
  --output-dir artifacts/operational_security \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Then open:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```

## Safety contract

The following flags must remain false:

- `api_key_required`;
- `api_key_present`;
- `account_connection_required`;
- `authenticated_connection_used`;
- `orders_allowed`;
- `orders_generated`;
- `real_capital_used`;
- `trading_signal_generated`;
- `executable_signal_generated`;
- `recommendation_generated`;
- `allocation_generated`;
- `portfolio_decision_generated`;
- `operational_decision_allowed`.

Even `APPROVED_RESEARCH_ONLY` does not unlock operations. It only records research review state.
