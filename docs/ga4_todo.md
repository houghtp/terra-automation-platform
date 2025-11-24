# GA4 Analytics TODO

## Phase 0.5 — Data Expansion (in progress)
- [x] Add schema columns for `new_users`, `avg_engagement_time`, `conversion_rate`, `conversions_per_1k`.
- [x] Extend ingestion client to fetch `newUsers`, `averageSessionDuration`, compute conversion rate and per-1k.
- [x] Wire schemas/services/tests to surface the new fields.
- [ ] Run Alembic migration `ga4_expand_metrics` in target envs.

## Phase 1 — Core KPIs & Trends
- [ ] Add KPI endpoint returning deltas + new fields.
- [ ] Add combined time-series endpoint for sessions/users/conversions/engagement/bounce/new_users.
- [ ] Expose last-synced + available date range metadata.
- [ ] UI: date presets, KPI bar with deltas, trend charts, freshness indicator.

## Phase 2 — Traffic Quality & Visitor Mix
- [ ] Ingest and display new vs returning, avg engagement time highlights.
- [ ] UI: sparkline/additional KPI tiles.

## Phase 3 — Source/Content Insights
- [ ] Add grouped fetch for top channels/pages (small aggregates).
- [ ] UI tables/cards for top channels/pages with sessions/conversions/conv rate.

## Phase 4 — Business Outcomes
- [ ] Add revenue/lead conversion metrics (if available).
- [ ] UI revenue/conversion value KPIs and trend.
