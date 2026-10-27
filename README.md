# Global AI Capital Terminal

A living, evidence-based map of global AI capital — who is raising money, who is investing, how valuations are changing, which companies are winning business, and how financial performance supports (or challenges) those valuations.

**Baseline date:** 27 October 2026 · **Currency:** USD unless stated · **Coverage:** disclosed information only, labelled as such

## The four mandatory rankings (never combined)

| Ranking | File | Basis |
|---|---|---|
| A — Cumulative fundraising | `data/ranking_a_cumulative_fundraising.csv` | Total external capital raised, inception → reporting date |
| B — Latest valuation | `data/ranking_b_valuation_private.csv` / `data/ranking_b_valuation_public.csv` | Latest funding/tender valuation (private) vs market cap/EV (public) — separate tables, then a labelled cross-market view |
| C — Largest single rounds | `data/ranking_c_largest_rounds.csv` | Announced vs actually contributed; equity vs debt vs convertible; primary vs secondary |
| D — Investor activity | `data/ranking_d_investors.csv` | Disclosed AI investment, trailing 12 months and cumulative where measurable, by investor type |

## Evidence rules (non-negotiable)

1. **Hierarchy:** filings/exchange disclosures → company IR/announcements → government procurement/court → investor announcements → Reuters/Bloomberg/FT/WSJ → VC/private-market databases → specialist press → broker indications (with limitations).
2. **Labels on every figure:** `CONFIRMED` / `REPORTED` / `INDICATIVE` / `RUMOUR` / `ANALYST ESTIMATE` / `UNKNOWN`, with event date *and* publication date and a direct source link.
3. **Cross-check:** every figure verified against ≥2 independent sources before publication. Disagreements are shown, explained (date/methodology), and the best-supported value identified. Irreconcilable = labelled and held, never published blind.
4. **No invention:** no fabricated amounts, valuations, stakes, timelines, or grey-market quotes. Grey-market quotes are unofficial, illiquid, indicative-only, and may be inaccessible to ordinary investors.
5. **No double counting:** operating-company fundraising is separated from parent/subsidiary/project-vehicle financing; contract value ≠ revenue ≠ cash ≠ profit; a funding valuation ≠ independently established fair value.

## Layout

- `SPEC.md` — full terminal specification (sections 1–13)
- `RUNBOOK.md` — daily / weekly / monthly / quarterly cadence and change-detection rules
- `data/` — the rankings and trackers (CSV, one row per observation, dated and sourced)
- `companies/` — per-company historical financing & valuation timelines
- `dashboards/` — the five required dashboards (fundraising, valuation evolution, investor activity, IPO pipeline, commercial traction)
- `sources/registry.yaml` — source register: every source used, tier, and what it supports
- `reports/` — dated editions (baseline first, then weekly/monthly)

## Status

Baseline build in progress (27 Oct 2026). Rankings populate from the baseline research pass; nothing is published until dual-source verified.

## Tab 14 — AI Credit & Debt Markets Intelligence

Dedicated credit dashboard (added 27 Oct 2026): borrowing costs, public bond trading, private credit, CDS, ratings, maturity walls with +100/+200/+300bps refinancing stress, and credit-vs-equity divergence flags. Schemas in `data/credit_*.csv`, entity map in `data/credit_entity_map.csv`, panel map in `dashboards/tab14-credit.md`. Integrity rule: no manufactured yields, private rates, CDS premiums, volumes, or ratings — licensed-feed fields stay "unavailable" until a feed is connected, and an absent CDS quote is never zero risk or a sector index in disguise.

## Tab — AI Financial Network & Cash-Flow Risk

Added 27 Oct 2026: a connected obligations model — intercompany loans, guarantees, SPV debt, order-book quality (firm vs conditional vs cancellable), depreciation & asset lives, capex schedules, reconciled forward cash-flow models, base/downside/severe stress tests, and counterparty contagion, all on a directed network graph with a document-linked evidence ledger. Schemas: `data/network_entities.csv`, `data/network_edges.csv`, `data/order_book.csv`, `data/depreciation_assets.csv`, `data/capex_schedule.csv`, `data/cashflow_model.csv`, `data/scenarios.csv`, `data/evidence_ledger.csv`; views in `dashboards/financial-network.md`. Rules: backlog ≠ RPO ≠ receivables ≠ cash; guarantee notional ≠ expected loss; no double counting of consolidated/eliminated obligations.

## AI Selloff, Price Shock & Fundamental Risk Monitor

Detection thresholds, severity rules and the monitored universe live in
`engine/shock_config.yaml`; alerts in `data/shock_alerts.csv`; shock & recovery
history in `data/shock_history.csv`; private-company material events (no daily
prices — never fabricated) in `data/private_watchlist_events.csv`. Catalysts are
classified A–H; causation is never claimed from simultaneity — insufficient
evidence reads "cause not confirmed". Critical severity requires verified
liquidity/default/covenant/contractual risk, never price alone. Design:
`dashboards/selloff-monitor.md`.

## Refresh engine

`engine/refresh_engine.py` implements the source-governance spec: EDGAR watch
(15-minute cadence, declared User-Agent, backoff, amendment supersede, dedupe by
accession + obligation key, outage-never-zero), state in `engine/state/`,
acceptance tests in `engine/tests/test_acceptance.py`, source registry in
`engine/sources.yaml`, dependency graph in `engine/dependency_graph.yaml`,
current per-company freshness in `data/refresh_state.csv`.

## Publishing (encrypted)

The readable page lives only on your machine in `src/terminal.src.html`
(git-ignored, never committed). The site serves an encrypted build:

```
pip install cryptography
python tools/encrypt_page.py          # writes index.html (ciphertext only)
git add index.html && git commit -m "Update terminal" && git push
```

You are asked for the passcode twice. Optional typo guard: put the passcode's
SHA-256 in `src/passcode.sha256` (also git-ignored). See `GATE.md`.

## UI tests

`python tests/test_terminal_ui.py` (needs `pip install playwright cryptography` and
`python -m playwright install chromium`) checks navigation, event filters,
sorting, CSV export, search, the evidence panel, story merging, responsive
layout and an encrypted-build round trip, against your local `src/terminal.src.html`.
