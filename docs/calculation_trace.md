# Calculation Trace

Notebook 19 shows the loan-level calculation trail. The pipeline also creates `outputs/tables/exposure_trace_sample.csv` during a full run.

The trail follows this order:

1. Product, balance, limit and undrawn amount.
2. Borrower eligibility fields, performing class, final class and classification rule.
3. Funded exposure, CCF and converted undrawn amount.
4. EAD before credit risk mitigation.
5. Eligible collateral and guarantee treatment.
6. SA exposure, risk weight and RWA.
7. Transition profile, internal grade and long-run PD.
8. Normal recovery, downturn recovery, cost, recovery time and downturn LGD.
9. IRB CCF, IRB EAD and effective maturity.
10. Correlation, 99.9% conditional PD, maturity adjustment and capital K.
11. Expected loss and IRB RWA.
12. Market and operational RWA inputs, aggregate output floor, stress and capital results.

The trace retains rule IDs and intermediate values so each result can be checked.
