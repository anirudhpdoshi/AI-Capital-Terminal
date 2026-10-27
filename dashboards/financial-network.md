# Tab — AI Financial Network & Cash-Flow Risk

Views (per spec §11):
- **A. Executive liquidity dashboard** — cash, net debt, debt due 12m, committed capex, remaining commitments, OCF, FCF, projected closing cash; every figure dated, sourced, historical-vs-forecast labelled. Data: `data/cashflow_model.csv`, `data/credit_maturity_wall.csv`, `data/capex_schedule.csv`
- **B. Interactive financial network** — directed nodes/edges (loans, guarantees, external debt, equity, purchase commitments, customer contracts, cloud/compute, JV/SPV, leases); click an edge for terms + source document; direct + multi-level exposure views. Data: `data/network_entities.csv`, `data/network_edges.csv`
- **C. Cash-flow waterfall** — opening cash → OCF → capex → acquisitions → financing → debt repayment → dividends → closing cash; historical and forecast separated. Data: `data/cashflow_model.csv`
- **D. CAPEX & depreciation timeline** — capex vs depreciation, additions, commissioning, asset-life assumptions, projected net PP&E. Data: `data/capex_schedule.csv`, `data/depreciation_assets.csv`
- **E. Commitment maturity heatmap** — contractual payments, debt maturities, purchase commitments, leases, guarantee expiries by year; filter by company/counterparty/entity/currency/type. Data: `data/order_book.csv`, `data/network_edges.csv`, `data/credit_maturity_wall.csv`
- **F. Scenario comparison** — base / downside / severe: closing cash, FCF, debt, refinancing needs, runway; absolute and vs-base. Data: `data/scenarios.csv`
- **G. Counterparty concentration** — largest customers, suppliers, lenders, guarantors, related-party exposures; failure impact under stated assumptions. Data: `data/network_edges.csv`
- **H. Evidence & data quality** — document-linked ledger with filing date, page/note reference, confidence, unresolved discrepancies; reported / guidance / estimate / scenario visually distinct. Data: `data/evidence_ledger.csv`

Anti-double-counting rule: consolidated subsidiary debt, eliminated intercompany balances, and the same obligation reported by multiple counterparties are counted once, keyed by `double_count_key` on every edge.
