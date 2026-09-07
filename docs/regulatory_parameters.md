# Regulatory Parameters

Parameters are stored in `config/`. Calculation outputs retain rule IDs where applicable.

| File | Purpose | Basel section |
|---|---|---|
| `regulatory_scope.yaml` | Date, portfolio size, currency and output floor | RBC20, RBC90 |
| `sa_risk_weights.yaml` | SA risk weights | CRE20, CRE21 |
| `ccf_parameters.yaml` | Credit conversion factors | CRE20 |
| `classification_parameters.yaml` | Sales, retail size and granularity thresholds; synthetic currency conversion | CRE20.47, CRE20.65, CRE30.23 |
| `crm_parameters.yaml` | Collateral and guarantees | CRE22 |
| `irb_parameters.yaml` | IRB floors and functions | CRE30 to CRE36 |
| `pd_transition_assumptions.yaml` | Synthetic transition matrices and long-run PD anchors | CRE36 estimation concepts |
| `capital_parameters.yaml` | Capital plus synthetic market and operational RWA inputs | RBC20, MAR20, OPE10, OPE25 |
| `stress_scenarios.yaml` | Synthetic stress sensitivities and calibration note | CRE36, BCBS stress-testing principles |
| `regulatory_sources.yaml` | Source records | Basel Framework |

The baseline uses CET1 4.5%, Tier 1 6.0%, Total Capital 8.0%, a 2.5% conservation buffer and a 65% output-floor rate for the configured date.

These values do not assert national implementation. The official Basel source is recorded in `config/regulatory_sources.yaml`.
