# Methodology

## Calculation authority

Functions in `src/basel_credit_risk/` are authoritative. Notebooks, tables, charts and Excel are reporting outputs.

Calculations retain INR values. Reader-facing reports divide monetary values by 10,000,000 and display INR crore.

## Synthetic data

The generator creates current and prior portfolios with a fixed seed. Every row is one loan or facility. Revolving products include contractual limits, drawn balances, undrawn commitments and cancellability fields. Mortgages include property eligibility, property value and cash-flow-dependency fields.

The generated balances, ratings, defaults, collateral values, recoveries and maturities are synthetic. A bank would source these fields from lending, limit, collateral, rating, default and recovery systems, reconcile them to finance records and retain historical snapshots.

## Classification and EAD

Source classes are retained beside regulatory classes. Unmapped classes create an exception.

```text
Funded exposure = outstanding balance + accrued interest
Converted undrawn = CCF × undrawn amount
EAD before CRM = funded exposure + converted undrawn
```

CCFs come from `config/ccf_parameters.yaml` and are selected from contractual commitment type rather than product name.

## Credit risk mitigation

- Eligible cash-like collateral can reduce exposure after haircuts.
- Guarantees apply a substituted risk weight to the protected amount.
- Property affects mortgage LTV and IRB LGD in this project.
- Pre- and post-mitigation values remain visible.

## Standardised Approach

```text
SA RWA = unguaranteed EAD × borrower risk weight
       + guaranteed EAD × guarantor risk weight
```

Risk weights use regulatory class, rating or mortgage LTV. Mortgage LTV uses outstanding principal plus committed undrawn exposure divided by prudent property value. Separate grids apply when repayment materially depends on property cash flow.

## IRB approach

The engine develops the four IRB components separately.

- Long-run PD is the synthetic transition matrix's one-year default-column rate for the assigned borrower grade or retail pool.
- Downturn LGD is built from discounted collateral and unsecured recoveries, workout cost and recovery time.
- IRB EAD is funded exposure plus an IRB CCF multiplied by undrawn exposure.
- Effective maturity is subject to the ordinary one-year floor and five-year cap represented in this scope.
- Correlation follows the Basel corporate, SME, residential mortgage, qualifying revolving retail or other-retail function.

```text
Expected loss = PD × LGD × EAD
IRB RWA = 12.5 × K × EAD
```

K is unexpected-loss capital after the applicable IRB adjustments. Corporate, sovereign and bank functions use the represented maturity adjustment. Retail functions do not use the full maturity adjustment.

The transition probabilities, recovery assumptions and own CCFs are synthetic. A bank would estimate long-run PD from multi-year one-year default observations by grade or pool; LGD from discounted recoveries, costs and time to recovery on defaulted facilities with downturn adjustment; and CCF/EAD from realised drawings before default. Representative data, validation and a margin of conservatism would be required.

## Market and operational RWA

The demonstration uses synthetic configured inputs of INR 11,000 crore market RWA and INR 14,000 crore operational RWA.

- Market RWA is normally `12.5 × market-risk capital requirement`. Under the applicable standardised framework, the capital requirement combines prescribed market-risk components such as sensitivities-based charges, default risk and residual risk.
- Operational RWA is `12.5 × operational-risk capital`. Under the Basel Standardised Approach, operational-risk capital is `Business Indicator Component × Internal Loss Multiplier`. The calculation uses financial-statement components and, where applicable, a ten-year operational-loss history.

## Output floor

```text
Standardised total = SA Credit RWA + Market RWA + Operational RWA
Model total = IRB Credit RWA + Market RWA + Operational RWA
Floor amount = floor rate × standardised total
Final RWA = maximum of model total and floor amount
```

## Concentration

```text
Exposure share = exposure EAD / total EAD
HHI = sum of squared exposure shares
```

The project also reports Top-10 and Top-20 borrower shares.

## RWA attribution

The bridge starts with prior RWA and explains new business, run-off, EAD, PD, LGD and maturity effects. Nonlinear interaction remains as a residual. The bridge must reconcile to current RWA.

## Stress testing

Adverse and severe scenarios change PD, LGD, collateral and utilisation. The engine then recalculates EAD and RWA.

```text
Stress loss = scenario loss rate × scenario EAD
Stressed CET1 = base CET1 - stress loss
```

The scenario multipliers, add-ons, collateral shocks, utilisation shocks and loss rates are synthetic sensitivities, not Basel-prescribed values. A bank would start with an approved macroeconomic scenario, estimate satellite models linking macro variables to portfolio risk drivers, apply management-reviewed overlays where evidence is weak, and project losses, earnings, RWA and capital across the stress horizon.

## Capital adequacy

```text
Total RWA = final Credit RWA + Market RWA + Operational RWA
Capital ratio = eligible capital / Total RWA
Headroom = capital ratio - requirement
```
