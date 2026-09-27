# Europe Start — Free Eurostat Data Engine v0.2

External, zero-additional-cost data engine for Europe Start.

## Controlled test
Spain (ES), Germany (DE), France (FR), Italy (IT), Portugal (PT) × 11 Eurostat mappings verified by Base44 on 2026-09-27.

## Verified mappings
- unemployment_rate -> une_rt_a
- employment_rate -> lfsi_emp_a
- job_vacancy_rate -> jvs_q_nace2
- inflation_rate -> prc_hicp_ainr
- rent_index -> prc_hicp_ainr
- GDP_growth -> nama_10_gdp
- GDP_per_capita -> nama_10_pc
- actual_individual_consumption -> prc_ppp_ind
- price_level -> prc_ppp_ind
- house_price_index -> prc_hpi_q
- population -> demo_pjan

## Status semantics
VERIFIED = mapping configuration verified against Eurostat.
LIVE_CANDIDATE = value actually retrieved by this engine.
The engine does not write to Base44.

## GitHub Actions
Manual: Actions -> Europe Start Eurostat Update -> Run workflow.
Scheduled: daily at 06:17 UTC.

## API
https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data
