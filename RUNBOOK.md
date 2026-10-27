# Runbook — Global AI Capital Terminal

## Cadence
- **Daily:** change detection only — new funding, investor transactions, material model releases, contracts, IPO developments, financial disclosures, significant market moves. No update = no output.
- **Weekly:** update Rankings A–D, IPO pipeline, contract tracker; diff vs previous week (adds, removals, rank changes, new valuations, stale data, corrections — rank changes only on equivalent datasets).
- **Monthly:** comprehensive capital-flow report — sector/geography allocation, historical trend charts, valuation review.
- **Quarterly:** earnings, revenue quality, capex, cash burn, institutional ownership; test whether valuations remain supported by operating performance.

## Per-edition output order (comprehensive reports)
1. Executive summary 2. Ranking A 3. Ranking B 4. Ranking C 5. Ranking D 6. Trends vs prior periods 7. Institutional flows & strategic relationships (incl. circular-financing flags) 8. IPO / pre-IPO / secondary / grey-market tracker 9. Contracts & orders (firm vs conditional) 10. Financials, multiples, cash requirements 11. Model competition & infrastructure 12. Catalysts, missing information, data-quality warnings

## Data rules
- Every ranking states: reporting date, currency, inclusion criteria, disclosed-only vs comprehensive.
- Private valuations carry their observation date; never compare a stale private valuation with a current public market cap without flagging both dates and methods.
- Debt facilities are not equity rounds; announced round size ≠ cash received.
- Stale check each edition: flag any Top-10 private valuation >6 months old, highlight >12 months.
- Corrections: superseded figures stay in the CSV history with a `superseded` note — never silently overwritten.
