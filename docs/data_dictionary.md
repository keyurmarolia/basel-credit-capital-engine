# Data Dictionary

All identifiers and values are synthetic. Monetary calculation fields are stored in INR. Reports and notebooks display INR crore.

## Source fields

| Field | Description |
|---|---|
| `exposure_id` | Unique exposure ID. |
| `borrower_id` | Borrower ID. |
| `connected_group_id` | Connected-group ID. |
| `reporting_date` | Portfolio date. |
| `segment` | Portfolio segment. |
| `product_type` | Product type. |
| `borrower_type` | Sovereign, bank, corporate, SME or individual borrower type. |
| `is_individual` | Individual-borrower indicator. |
| `is_sme` | SME indicator. |
| `managed_as_retail` | Exposure managed as part of a retail pool. |
| `retail_transactor` | Qualifying full-repayment behaviour indicator. |
| `annual_revenue` | Synthetic borrower annual revenue in INR. |
| `exposure_class_raw` | Source exposure class. |
| `sector` | Economic sector. |
| `geography` | Region. |
| `currency` | Currency. The project uses INR. |
| `external_rating` | External rating band. |
| `internal_grade` | Internal grade. |
| `pd_1y` | One-year probability of default. |
| `lgd` | Loss given default. |
| `maturity_years` | Maturity in years. |
| `contractual_maturity_years` | Contractual maturity before IRB floor or cap. |
| `outstanding_balance` | Drawn principal. |
| `credit_limit` | Facility limit. |
| `undrawn_amount` | Unused commitment. |
| `revolving_flag` | Facility can be drawn, repaid and redrawn. |
| `commitment_type` | Contract category used to select the CCF. |
| `unconditionally_cancellable_flag` | Unconditionally cancellable commitment indicator. |
| `accrued_interest` | Accrued exposure. |
| `collateral_type` | Collateral type. |
| `collateral_value` | Collateral value. |
| `property_value_at_origination` | Synthetic property value at origination. |
| `property_value_current` | Synthetic current property value. |
| `property_cashflow_dependent` | Repayment materially depends on property cash flow. |
| `regulatory_real_estate_eligible` | Basel real-estate eligibility indicator. |
| `senior_lien_amount` | Senior lien amount outside the bank. |
| `guarantee_value` | Guarantee amount. |
| `dpd` | Days past due. |
| `default_flag` | Default indicator. |

## EAD and mitigation fields

| Field | Description |
|---|---|
| `ccf` | Credit conversion factor. |
| `ccf_rule_id` | CCF rule ID. |
| `ccf_basel_reference` | Basel paragraph recorded for the selected CCF. |
| `funded_exposure` | Balance plus accrued interest. |
| `converted_undrawn` | CCF multiplied by undrawn amount. |
| `ead_pre_crm` | EAD before mitigation. |
| `crm_eligible` | Eligible-collateral indicator. |
| `collateral_haircut` | Collateral haircut. |
| `crm_treatment` | Applied treatment. |
| `eligible_collateral_value` | Recognised collateral value. |
| `eligible_guarantee_value` | Recognised guarantee value. |
| `sa_ead_post_crm` | SA EAD after mitigation. |
| `crm_coverage_ratio` | Recognised protection divided by EAD. |
| `lgd_after_crm` | LGD after collateral treatment. |

## RWA fields

| Field | Description |
|---|---|
| `basel_exposure_class` | Regulatory exposure class. |
| `performing_exposure_class` | Regulatory class before the default override. |
| `classification_rule_id` | Rule that assigned the final class. |
| `ltv_loan_amount` | Outstanding plus committed undrawn mortgage amount used in LTV. |
| `property_value_prudent` | Prudent property value used in LTV. |
| `ltv` | Mortgage loan amount divided by prudent property value. |
| `sa_risk_weight` | SA risk weight. |
| `sa_rule_id` | SA rule ID. |
| `sa_rwa` | SA RWA. |
| `sa_rwa_density` | SA RWA divided by SA EAD. |
| `pd_input` | PD before regulatory treatment. |
| `pd_transition_profile` | Sovereign, bank, corporate or retail transition profile. |
| `pd_long_run` | Synthetic long-run one-year grade or pool PD. |
| `pd_source` | PD estimation-source label. |
| `pd_regulatory` | PD used in IRB calculation. |
| `lgd_input` | LGD before regulatory treatment. |
| `normal_lgd` | Recovery-based LGD under normal assumptions. |
| `downturn_lgd` | Recovery-based LGD under downturn assumptions. |
| `normal_discounted_recovery` | Discounted normal recovery amount. |
| `downturn_discounted_recovery` | Discounted downturn recovery amount. |
| `normal_workout_cost` | Normal recovery workout cost. |
| `downturn_workout_cost` | Downturn recovery workout cost. |
| `lgd_regulatory` | LGD used in IRB calculation. |
| `ead_irb` | IRB EAD. |
| `irb_ccf` | CCF used for IRB EAD. |
| `irb_ccf_source` | Foundation or synthetic own-estimate source label. |
| `m_effective` | Effective maturity. |
| `maturity_floor_applied` | One-year floor indicator. |
| `maturity_cap_applied` | Five-year cap indicator. |
| `irb_function` | IRB formula family. |
| `asset_correlation_r` | Asset correlation. |
| `correlation_rule` | Basel correlation family used. |
| `maturity_adjustment` | Maturity adjustment. |
| `conditional_stressed_pd` | Conditional tail PD. |
| `conditional_pd_999` | 99.9% conditional default probability. |
| `expected_loss_rate` | PD multiplied by LGD. |
| `expected_loss_amount` | PD multiplied by LGD and EAD. |
| `capital_k` | Unexpected-loss capital per unit EAD. |
| `irb_rwa` | 12.5 multiplied by K and EAD. |
| `irb_rwa_density` | IRB RWA divided by IRB EAD. |
