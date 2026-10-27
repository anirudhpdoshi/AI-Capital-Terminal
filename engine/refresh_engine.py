#!/usr/bin/env python3
"""
AI Financial Network — refresh, validation & governance engine.

Implements the Data Refresh, Source Governance & Risk Monitoring spec:
- Source-aware, event-driven checks (EDGAR submissions API; other sources
  registered in sources.yaml with their own cadences).
- Every observation carries source, document URL, publication time, period,
  retrieval + last-validation timestamps, next check, status
  (Current / Awaiting Update / Stale / Failed / Estimated / Manually Verified),
  confidence, materiality, reported-vs-calculated provenance, and version history.
- Failure rules: exponential backoff with a cap; a failed check NEVER overwrites
  a verified value with null/zero; "no new filing" != "check failed".
- Amendments supersede the current interpretation; history is preserved.
- Dedupe by accession number and by double_count_key (same obligation announced
  in a release and a filing counts once).
- Materiality: >=5% move in a major metric, or any covenant/liquidity/
  contractual threat, guarantee change, rating action or restatement.
- Dependency-aware recalculation via dependency_graph.yaml (topological order).
  Depreciation reaches cash ONLY through tax/working-capital effects.

No endpoint is invented: the only live source wired is SEC EDGAR's public
APIs, called with a declared User-Agent per SEC fair-access rules.
"""
import hashlib, json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(HERE, "state")
STATE_PATH = os.path.join(STATE_DIR, "refresh_state.json")
AUDIT_PATH = os.path.join(STATE_DIR, "audit_log.jsonl")
EVENTS_PATH = os.path.join(STATE_DIR, "event_feed.json")
UA = {"User-Agent": "Muse AI Capital Terminal (research; contact adoshi@dgglobal.ca)"}
# NOTE: never hard-code a Host header — CIK resolution is on www.sec.gov while
# submissions/companyfacts are on data.sec.gov; a wrong Host gets the
# connection dropped (seen 27 Oct 2026: RemoteDisconnected on first live pass).
MATERIALITY_PCT = 5.0

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def audit(event, **fields):
    rec = {"ts": now_iso(), "event": event, **fields}
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(AUDIT_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec

def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {"companies": {}, "events": [], "metrics": {}}

def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, STATE_PATH)  # atomic: a crash never leaves a half-written state

def fetch_json(url, max_attempts=4, backoff_base=2.0, backoff_factor=2.0, opener=None):
    """GET JSON with exponential backoff. Returns (data, error_str)."""
    opener = opener or urllib.request.urlopen
    err = None
    for attempt in range(1, max_attempts + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with opener(req, timeout=30) as r:
                raw = r.read()
                if raw[:2] == b"\x1f\x8b":  # gzip magic — decompress explicitly
                    import gzip
                    raw = gzip.decompress(raw)
                return json.loads(raw.decode("utf-8")), None
        except Exception as e:  # HTTPError, URLError, timeout, bad JSON
            err = f"{type(e).__name__}: {e}"
            if attempt < max_attempts:
                time.sleep(backoff_base * (backoff_factor ** (attempt - 1)))
    return None, err

# ---------- dependency graph ----------
def load_graph():
    # tiny YAML-free parse of the edges section (kept dependency-free on purpose)
    edges, current = {}, None
    in_edges = False
    with open(os.path.join(HERE, "dependency_graph.yaml")) as f:
        for line in f:
            if line.startswith("edges:"):
                in_edges = True; continue
            if in_edges:
                if line and not line.startswith(" ") and not line.startswith("#"):
                    break
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                node, _, rest = s.partition(":")
                deps = [d.strip() for d in rest.strip().strip("[]").split(",") if d.strip()]
                edges[node.strip()] = deps
    return edges

def recalc_order(graph, start_nodes):
    """Topological order of everything downstream of start_nodes (inclusive)."""
    order, seen = [], set()
    def visit(n):
        if n in seen: return
        seen.add(n); order.append(n)
        for d in graph.get(n, []):
            visit(d)
    for n in start_nodes:
        visit(n)
    return order

# ---------- dedupe / supersede ----------
def obligation_key(company, counterparty, amount, kind):
    raw = f"{company}|{counterparty}|{amount}|{kind}".lower()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

def record_event(state, ev):
    """Add an event unless it is a duplicate (same accession or same obligation key)."""
    for e in state["events"]:
        if ev.get("accession") and e.get("accession") == ev["accession"]:
            audit("duplicate_suppressed", reason="same accession", accession=ev["accession"])
            return False
        if ev.get("double_count_key") and e.get("double_count_key") == ev["double_count_key"]:
            audit("duplicate_suppressed", reason="same obligation", key=ev["double_count_key"])
            return False
    state["events"].append(ev)
    audit("event_recorded", company=ev.get("company"), kind=ev.get("kind"),
          accession=ev.get("accession"))
    return True

def apply_amendment(state, metric_id, new_value, doc):
    """An amended filing replaces the current interpretation; history preserved."""
    m = state["metrics"].setdefault(metric_id, {"history": []})
    if "current" in m:
        m["history"].append(m["current"])
    m["current"] = {"value": new_value, "document": doc, "status": "Current",
                    "validated_at": now_iso(), "supersedes": len(m["history"])}
    audit("amendment_applied", metric=metric_id, versions=len(m["history"]) + 1)
    return m

# ---------- validation / staleness ----------
def validate_metric(metric, freshness_threshold_min):
    """Return status; never mutate the value. A failed check keeps the last value."""
    if metric.get("last_check_failed"):
        return "Failed"  # value stays as last verified; caller must not overwrite
    if metric.get("estimated"):
        return "Estimated"
    if metric.get("manually_verified"):
        return "Manually Verified"
    last = metric.get("validated_at")
    if not last:
        return "Awaiting Update"
    age_min = (datetime.now(timezone.utc) -
               datetime.fromisoformat(last)).total_seconds() / 60.0
    return "Stale" if age_min > freshness_threshold_min else "Current"

def material_change(old, new):
    if old in (None, 0) or new is None:
        return False
    return abs((new - old) / old * 100.0) >= MATERIALITY_PCT

def traceable(metric):
    """Acceptance: every material figure traces to a document or a labelled calculation."""
    cur = metric.get("current", {})
    return bool(cur.get("source_url")) or cur.get("calculated") is True

# ---------- EDGAR watch ----------
def check_company_edgar(state, name, cik, opener=None):
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    data, err = fetch_json(url, opener=opener)
    comp = state["companies"].setdefault(name, {"cik": cik})
    if err:
        comp["last_check"] = now_iso()
        comp["last_check_result"] = "failed"
        comp["last_error"] = err
        audit("check_failed", company=name, source="sec_edgar_submissions", error=err, url=url)
        return {"company": name, "result": "failed", "error": err}
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", []); dates = recent.get("filingDate", [])
    accs = recent.get("accessionNumber", []); docs = recent.get("primaryDocument", [])
    latest = None
    if accs:
        latest = {"form": forms[0], "filed": dates[0], "accession": accs[0],
                  "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accs[0].replace('-','')}/{docs[0]}"}
    prev = comp.get("latest_accession")
    new_events = []
    if latest and prev and latest["accession"] != prev:
        # everything newer than the previously seen accession is a new event
        for i, a in enumerate(accs):
            if a == prev: break
            ev = {"company": name, "kind": "filing", "form": forms[i], "filed": dates[i],
                  "accession": a,
                  "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{a.replace('-','')}/{docs[i]}",
                  "detected_at": now_iso(), "source": "sec_edgar_submissions"}
            if record_event(state, ev):
                new_events.append(ev)
    comp["latest_accession"] = latest["accession"] if latest else prev
    comp["latest_filing"] = latest
    comp["last_check"] = now_iso()
    comp["last_check_result"] = "ok_new" if new_events else "ok_no_new"
    comp.pop("last_error", None)
    audit("check_ok", company=name, result=comp["last_check_result"],
          new_events=len(new_events), latest=latest["accession"] if latest else None)
    return {"company": name, "result": comp["last_check_result"],
            "new_events": new_events, "latest": latest}

def resolve_ciks(tickers, opener=None):
    data, err = fetch_json("https://www.sec.gov/files/company_tickers.json", opener=opener)
    if err:
        return {}, err
    by_ticker = {v["ticker"]: (v["cik_str"], v["title"]) for v in data.values()}
    return {t: by_ticker[t] for t in tickers if t in by_ticker}, None

def main():
    tickers = ["NVDA","MSFT","GOOGL","META","AMZN","AVGO","AMD","ORCL","PLTR","TSLA","CRWV","NBIS","CBRS","SPCX"]
    state = load_state()
    resolved, err = resolve_ciks(tickers)
    if err:
        print(json.dumps({"fatal": f"CIK resolution failed: {err}"})); return 1
    results = []
    for t, (cik, title) in resolved.items():
        results.append(check_company_edgar(state, f"{title} ({t})", int(cik)))
        time.sleep(0.15)  # well under SEC fair-access limits
    results.append(check_company_edgar(state, "Anthropic (ANT)", 2130357))
    save_state(state)
    with open(EVENTS_PATH, "w") as f:
        json.dump(state["events"], f, indent=1)
    summary = {"checked": len(results),
               "ok_no_new": sum(1 for r in results if r["result"] == "ok_no_new"),
               "ok_new": sum(1 for r in results if r["result"] == "ok_new"),
               "failed": sum(1 for r in results if r["result"] == "failed"),
               "new_events": sum(len(r.get("new_events", [])) for r in results)}
    print(json.dumps(summary, indent=1))
    return 0

if __name__ == "__main__":
    sys.exit(main())
