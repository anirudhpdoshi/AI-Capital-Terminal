# Tab 14 — AI Credit & Debt Markets Intelligence

Purpose: reveal how the market prices AI companies' debt, what refinancing may cost, and whether credit evidence supports or contradicts equity valuations. Divergences are investigation signals, not recommendations.

| Panel | Content | Data file |
|---|---|---|
| 1. Debt & borrowing-cost overview | Total/public/private debt, facilities, coupon vs YTM vs refi cost (separate fields), leverage, coverage, rating | `data/credit_company_overview.csv` |
| 2. Public bond trading | Per-bond identifiers, price/bid/ask, YTM/YTW, OAS, benchmark spread, last trade, liquidity | `data/credit_bonds.csv` |
| 3. Private credit & direct lending | Facilities, lenders, drawn/undrawn, pricing or "Not publicly disclosed", collateral, PIK, all-in cost + assumptions | `data/credit_private_facilities.csv` |
| 4. CDS | Single-name spreads by tenor or "No verified CDS quote available"; hazard-rate model outputs labelled model-implied only | `data/credit_cds.csv` |
| 5. Ratings & fundamental risk | Agency ratings/actions, outlook/watch, leverage, liquidity, refi needs, triggers | `data/credit_ratings.csv` |
| 6. Maturity wall & refinancing stress | Due 12m/24m/36m/5y vs cash+liquidity; stress at current/+100/+200/+300bps; leases & cloud obligations kept separate | `data/credit_maturity_wall.csv` |
| 7. Credit vs equity signals | Spread/CDS/rating vs valuation, growth, FCF, leverage; divergence flags | `data/credit_equity_signals.csv` |

Entity discipline: `data/credit_entity_map.csv` maps legal entities, parents, issuers, guarantors and CDS reference entities — a parent's yield/CDS is never presented as a subsidiary's borrowing cost.

Source hierarchy: FINRA TRACE (per its access/licensing terms) · SEC EDGAR · company IR/prospectuses · ICE Data Services (licensed CDS) · DTCC / CDS Kinetics (aggregates only, never executable quotes) · US Treasury / Bank of Canada / FRED benchmarks · S&P / Moody's / Fitch. Licensed-feed fields stay blank/"unavailable" until a feed is connected — never filled from memory.
