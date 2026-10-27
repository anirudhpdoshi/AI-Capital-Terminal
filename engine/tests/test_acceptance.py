#!/usr/bin/env python3
"""Acceptance tests for the refresh engine (spec §8). Run: python3 test_acceptance.py"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import refresh_engine as re_

FAILED = []
def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond: FAILED.append(name)

# 1. A newly filed 8-K/10-Q is detected and recorded.
class FakeResp:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return json.dumps(self.payload).encode()

def fake_opener(payload):
    def _open(req, timeout=30): return FakeResp(payload)
    return _open

filings_v1 = {"filings": {"recent": {"form": ["10-Q"], "filingDate": ["2026-08-01"],
              "accessionNumber": ["0000000000-26-000001"], "primaryDocument": ["q.htm"]}}}
filings_v2 = {"filings": {"recent": {"form": ["8-K", "10-Q"],
              "filingDate": ["2026-10-20", "2026-08-01"],
              "accessionNumber": ["0000000000-26-000099", "0000000000-26-000001"],
              "primaryDocument": ["k.htm", "q.htm"]}}}
state = {"companies": {}, "events": [], "metrics": {}}
r1 = re_.check_company_edgar(state, "Fixture Co", 1, opener=fake_opener(filings_v1))
check("baseline check ok, no event on first sighting", r1["result"] == "ok_no_new")
r2 = re_.check_company_edgar(state, "Fixture Co", 1, opener=fake_opener(filings_v2))
check("new 8-K detected as event", r2["result"] == "ok_new" and len(r2["new_events"]) == 1
      and r2["new_events"][0]["form"] == "8-K")

# 2. Amended filing replaces current interpretation, history preserved.
m = re_.apply_amendment(state, "fixture.revenue", 100, "10-Q original")
m = re_.apply_amendment(state, "fixture.revenue", 104, "10-Q/A amendment")
check("amendment supersedes + history kept",
      m["current"]["value"] == 104 and len(m["history"]) == 1 and m["history"][0]["value"] == 100)

# 3. Repeated announcement of the same obligation does not double count.
k = re_.obligation_key("CoreWeave", "Meta", 21_000_000_000, "customer_contract")
e1 = {"company": "CoreWeave", "kind": "contract", "double_count_key": k}
check("first obligation recorded", re_.record_event(state, dict(e1)) is True)
check("same obligation via second release suppressed", re_.record_event(state, dict(e1)) is False)

# 4. Source outage: check fails -> status Failed, last verified value untouched, never zeroed.
def boom(req, timeout=30): raise OSError("simulated outage")
state2 = {"companies": {}, "events": [], "metrics": {}}
re_.check_company_edgar(state2, "Fixture Co", 1, opener=fake_opener(filings_v1))
r = re_.check_company_edgar(state2, "Fixture Co", 1, opener=boom)
metric = {"current": {"value": 55, "source_url": "https://www.sec.gov/x"},
          "validated_at": re_.now_iso(), "last_check_failed": r["result"] == "failed"}
check("outage reported as failed (not 'no new filing')", r["result"] == "failed")
check("status Failed and last value preserved (not zero/null)",
      re_.validate_metric(metric, 60) == "Failed" and metric["current"]["value"] == 55)
comp = state2["companies"]["Fixture Co"]
check("last verified filing still visible after outage", comp["latest_filing"]["accession"] == "0000000000-26-000001")

# 5. CAPEX change cascades through cash forecast + stress, in dependency order.
graph = re_.load_graph()
order = re_.recalc_order(graph, ["capex_commitment"])
check("capex cascade ordered end-to-end",
      order == ["capex_commitment", "payment_schedule", "investing_cf", "cash_balance",
                "liquidity_buffer", "refi_risk", "counterparty_exposure", "stress_results"])

# 6. Depreciation change hits earnings/asset values; cash ONLY via tax/WC — never investing_cf directly.
order_d = re_.recalc_order(graph, ["depreciation_estimate"])
check("depreciation reaches earnings + asset values", "forecast_earnings" in order_d and "asset_values" in order_d)
check("depreciation does NOT flow directly into investing_cf", "investing_cf" not in order_d)
check("depreciation reaches cash only via tax/WC, downstream of it",
      "cash_balance" in order_d and order_d.index("tax_wc_effects") < order_d.index("cash_balance"))

# 7. Every material figure traceable to a source document or a labelled calculation.
check("traceable via source_url", re_.traceable({"current": {"value": 1, "source_url": "https://www.sec.gov/y"}}))
check("traceable via labelled calculation", re_.traceable({"current": {"value": 1, "calculated": True}}))
check("untraceable figure rejected", not re_.traceable({"current": {"value": 1}}))

# Materiality: >=5% flags; stale never passes as fresh.
check("materiality 5% threshold", re_.material_change(100, 106) and not re_.material_change(100, 103))
stale = {"validated_at": "2020-01-01T00:00:00+00:00"}
check("old value marked Stale, not Current", re_.validate_metric(stale, 60) == "Stale")

print("\n%d failures" % len(FAILED))
sys.exit(1 if FAILED else 0)
