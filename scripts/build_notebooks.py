#!/usr/bin/env python3
"""Build the linear Basel credit capital notebook sequence."""

from __future__ import annotations

from inspect import cleandoc
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = ROOT / "notebooks"


def md(text: str):
    return nbf.v4.new_markdown_cell(cleandoc(text))


def code(text: str):
    return nbf.v4.new_code_cell(cleandoc(text))


SETUP = """
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from IPython.display import display as notebook_display
from pandas.io.formats.style import Styler

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))

from basel_credit_risk.config import load_all_config

CRORE = 10_000_000
COLORS = ["#0B3A53", "#1F77B4", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51"]
sns.set_theme(style="whitegrid", context="notebook")

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.max_colwidth", None)
pd.set_option("display.width", 200)
pd.set_option("display.expand_frame_repr", False)


def display(*objects, **kwargs):
    # Show complete table text and wrap long descriptions in saved notebook output.
    wrapped_objects = []
    for displayed_object in objects:
        if isinstance(displayed_object, pd.DataFrame):
            displayed_object = displayed_object.style
        if isinstance(displayed_object, Styler):
            displayed_object = displayed_object.set_properties(**{
                "white-space": "normal",
                "overflow-wrap": "anywhere",
                "text-align": "left",
                "vertical-align": "top",
                "max-width": "420px",
            }).set_table_styles([
                {"selector": "table", "props": [("width", "100%"), ("table-layout", "auto")]},
                {"selector": "th", "props": [
                    ("white-space", "normal"),
                    ("overflow-wrap", "anywhere"),
                    ("word-break", "break-word"),
                    ("text-align", "left"),
                    ("vertical-align", "top"),
                    ("max-width", "180px"),
                ]},
            ], overwrite=False)
        wrapped_objects.append(displayed_object)
    return notebook_display(*wrapped_objects, **kwargs)

configs = load_all_config(ROOT / "config")
raw = pd.read_csv(ROOT / "data/generated/current_portfolio.csv.gz", low_memory=False)
loans = pd.read_csv(ROOT / "data/processed/current_calculated.csv.gz", low_memory=False)

print(f"Portfolio represented below: {len(loans):,} synthetic loan-level exposures")
"""


OPENING_HEADINGS = {
    "00": "How the full calculation fits together",
    "01": "Start with the regulatory categories",
    "02": "Meet the synthetic loan book",
    "03": "From a bank product to a Basel class",
    "04": "Turning balances and limits into EAD",
    "05": "How the prescribed risk weight is selected",
    "06": "Completing the Standardised Approach",
    "07": "Opening the IRB calculation",
    "08": "Building the probability of default",
    "09": "Estimating the loss after default",
    "10": "Measuring exposure and time in IRB",
    "11": "From the four inputs to capital K",
    "12": "Completing loan-level IRB RWA",
    "13": "Bringing the two approaches together",
    "14": "What changes when the portfolio is stressed",
    "15": "Following the calculation back to one loan",
    "16": "Designing a transparent stress scenario",
    "17": "Passing the scenario through individual loans",
    "18": "Measuring the final capital effect",
    "19": "Following the calculation back to one loan",
}

TERM_HEADINGS = {
    "00": "Four ideas that anchor the project",
    "01": "Names used in the classification",
    "02": "Fields that appear in the loan data",
    "03": "Classification language used below",
    "04": "Words used in the EAD calculation",
    "05": "How to read the risk-weight tables",
    "06": "What the final SA calculation contains",
    "07": "The IRB approaches referred to below",
    "08": "How to read the transition tables",
    "09": "Recovery and loss language",
    "10": "The two facility measures built here",
    "11": "The extra terms inside the capital function",
    "12": "Expected loss and unexpected loss",
    "13": "How to read the aggregate comparison",
    "14": "How to read the stress results",
    "15": "How the final checks are described",
    "16": "The scenario terms used below",
    "17": "How shocks change loan calculations",
    "18": "How to read stressed capital",
    "19": "How the final checks are described",
}


def notebook(number, title, position, capital_connection, terms, cells, conclusion):
    glossary_rows = "\n".join(f"| {term} | {meaning} |" for term, meaning in terms)
    opening = "\n\n".join([
        f"# {number} — {title}",
        f"## {OPENING_HEADINGS[number]}",
        position,
        capital_connection,
        f"### {TERM_HEADINGS[number]}",
        "| Term | Simple meaning |\n|---|---|\n" + glossary_rows,
    ])
    result = nbf.v4.new_notebook()
    result.metadata = {
        "kernelspec": {
            "display_name": "Python (Basel Credit Capital Engine)",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.12"},
    }
    result.cells = [md(opening), code(SETUP), *cells, md(conclusion)]
    return result


def build() -> None:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    for old_notebook in NOTEBOOK_DIR.glob("*.ipynb"):
        old_notebook.unlink()

    specs = []

    specs.append(("00_complete_calculation_map.ipynb", notebook(
        "00", "Complete Calculation Map",
        "This notebook separates the project into distinct stages. The Standardised Approach is completed first. IRB begins only after Standardised Approach Credit RWA has been calculated and reconciled.",
        "Both approaches produce Credit RWA. Credit RWA later joins market and operational RWA to form the denominator of the bank's capital ratios.",
        [("Exposure", "one loan, bond or credit facility owed by a borrower"), ("EAD", "Exposure at Default, the amount exposed if default occurs"), ("RWA", "Risk-Weighted Assets, the exposure amount adjusted for regulatory risk"), ("Capital ratio", "eligible capital divided by total RWA")],
        [
            md("""## The linear calculation story

            The table prevents several calculations from appearing at once. The first six calculation stages finish the Standardised Approach. The next six stages build the IRB result one parameter at a time. Comparison, stress and controls appear only after both totals exist."""),
            code("""calculation_map = pd.DataFrame({
                "Stage": range(1, 16),
                "Question answered": [
                    "Which Basel exposure classes exist?",
                    "What loans and necessary variables exist in the synthetic bank?",
                    "Which Basel class contains each loan?",
                    "What is each loan's Standardised Approach EAD?",
                    "Which Standardised Approach risk weight applies?",
                    "What is total Standardised Approach Credit RWA?",
                    "Which IRB treatment and parameters apply?",
                    "What is the long-run one-year PD?",
                    "What is the downturn LGD?",
                    "What are IRB EAD and effective maturity?",
                    "What are correlation, conditional PD and capital K?",
                    "What is total IRB Credit RWA?",
                    "How do SA, IRB and the output floor compare?",
                    "How do stress and capital adequacy change?",
                    "Do all loan and portfolio totals reconcile?",
                ],
                "Main output": [
                    "Exposure-class reference table", "30,000 loan-level records",
                    "Class and classification rule per loan", "CCF and SA EAD per loan",
                    "Risk weight per loan", "Loan-level and total SA RWA",
                    "IRB eligibility and parameter source", "Grade or pool PD per loan",
                    "Recovery-based downturn LGD per loan", "IRB EAD and maturity per loan",
                    "Correlation, conditional PD and K per loan", "Loan-level and total IRB RWA",
                    "Final aggregate RWA", "Stressed RWA and capital ratios",
                    "Calculation trace and PASS controls",
                ],
            })
            display(calculation_map)"""),
            md("""## The project as one visual path

            The diagram separates the two approaches instead of mixing their calculations. The upper route finishes the Standardised Approach. The lower route then builds IRB one risk component at a time. Both routes meet only after each total is complete."""),
            code("""figure, axis = plt.subplots(figsize=(14, 4.5))
            axis.axis("off")

            steps = [
                (0.04, 0.72, "Loan data"), (0.22, 0.72, "Basel class"),
                (0.40, 0.72, "SA EAD + risk weight"), (0.62, 0.72, "SA Credit RWA"),
                (0.22, 0.28, "PD + LGD + EAD + M"), (0.45, 0.28, "Correlation + K"),
                (0.65, 0.28, "IRB Credit RWA"), (0.84, 0.50, "Stress + capital ratios"),
            ]
            for x, y, label in steps:
                axis.text(x, y, label, ha="center", va="center", fontsize=11,
                          bbox={"boxstyle": "round,pad=0.5", "facecolor": "#EAF2F8", "edgecolor": "#1F77B4"})

            arrows = [
                ((0.10, 0.72), (0.16, 0.72)), ((0.29, 0.72), (0.34, 0.72)),
                ((0.50, 0.72), (0.55, 0.72)), ((0.69, 0.72), (0.78, 0.55)),
                ((0.10, 0.66), (0.18, 0.34)), ((0.32, 0.28), (0.38, 0.28)),
                ((0.53, 0.28), (0.58, 0.28)), ((0.72, 0.31), (0.79, 0.45)),
            ]
            for start, end in arrows:
                axis.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "color": "#0B3A53", "lw": 1.8})

            axis.text(0.50, 0.94, "Standardised Approach is completed first", ha="center", weight="bold", color="#0B3A53")
            axis.text(0.48, 0.06, "IRB is built after the SA total exists", ha="center", weight="bold", color="#0B3A53")
            plt.tight_layout()
            plt.show()"""),
            md("""The important reading is left to right: raw balances never become capital directly. Classification and exposure measurement come first; the chosen risk method then converts that exposure into RWA; stress and capital ratios appear at the end."""),
            md("""The sequence shows why total Credit RWA is not calculated directly. Classification determines the applicable rule, EAD determines the rupee exposure, and the selected approach determines how risk is applied to that exposure."""),
            md("""## One numerical preview

            A loan with EAD of INR 0.80 crore and a 30% risk weight produces INR 0.24 crore of Standardised Approach RWA. IRB replaces the prescribed risk weight with a capital function built from PD, LGD, EAD, maturity and correlation."""),
            code("""example_ead = 0.80
            example_risk_weight = 0.30
            example_rwa = example_ead * example_risk_weight

            display(pd.Series({
                "Loan EAD (INR crore)": example_ead,
                "Risk weight": example_risk_weight,
                "Loan RWA (INR crore)": example_rwa,
            }).to_frame("Value"))"""),
            md("""The INR 0.24 crore result is one loan's contribution to the capital denominator. The same calculation is repeated for every loan before aggregation."""),
        ],
        "The project order is fixed: exposure classes, synthetic loans, complete Standardised Approach, complete IRB, comparison, stress, capital adequacy and controls.",
    )))

    specs.append(("01_basel_exposure_classes.ipynb", notebook(
        "01", "Basel Exposure Classes Before the Loan Data",
        "The regulatory categories are defined before the synthetic loans are generated or classified. This keeps business products such as credit cards separate from the Basel classes used for capital.",
        "An exposure class selects the CCF, risk-weight table or IRB risk function. A wrong class can change the capital requirement even when the loan balance is correct.",
        [("Exposure class", "a regulatory group with a defined capital treatment"), ("Regulatory retail", "qualifying exposures to individuals or SMEs managed as part of a granular pool"), ("Transactor", "a qualifying card or charge-card borrower who has repaid in full at each scheduled date for the previous 12 months"), ("Defaulted exposure", "a loan already meeting the project's default rule")],
        [
            md("""## Exposure classes represented in the synthetic bank

            The table states the class before showing any loan records. `CRE20` is the Basel chapter for the Standardised Approach. `CRE30–CRE32` cover IRB classification, risk functions and parameters."""),
            code("""exposure_classes = pd.DataFrame([
                ["Sovereign", "Central government or central bank", "Government bond or loan", "CRE20 / CRE30"],
                ["Bank", "Regulated bank or qualifying financial institution", "Interbank loan", "CRE20 / CRE30"],
                ["Corporate", "Company not meeting a more specific class", "Corporate term loan or revolver", "CRE20 / CRE30"],
                ["Corporate SME", "SME managed as a corporate exposure", "SME working-capital line", "CRE20 / CRE30"],
                ["Regulatory retail", "Eligible granular exposure managed as retail", "Personal loan", "CRE20 / CRE30"],
                ["Retail transactor", "Eligible retail borrower who regularly repays in full", "Qualifying credit card", "CRE20"],
                ["Revolving retail", "Retail balance that can be borrowed and repaid repeatedly", "Credit card revolver", "CRE20 / CRE30"],
                ["Residential real estate", "Eligible exposure secured by residential property", "Home mortgage", "CRE20 / CRE30"],
                ["Defaulted", "Exposure meeting the default definition", "Any product after default", "CRE20 / CRE31"],
                ["Other", "Exposure outside the selected classes", "Other lending", "CRE20"],
            ], columns=["Basel exposure class", "Simple definition", "Example product", "Basel reference"])
            display(exposure_classes)"""),
            md("""## The order used to classify a loan

            Classification is a sequence of questions. Default is checked first because it overrides performing treatment. The remaining questions identify the borrower and facility before a residual corporate or other class is used."""),
            code("""decision_steps = [
                "Default?", "Sovereign?", "Bank?", "Eligible mortgage?",
                "Retail conditions?", "Corporate / SME", "Other",
            ]
            figure, axis = plt.subplots(figsize=(13, 2.8))
            axis.axis("off")
            x_positions = np.linspace(0.06, 0.94, len(decision_steps))
            for index, (x, label) in enumerate(zip(x_positions, decision_steps)):
                colour = "#E76F51" if index == 0 else "#EAF2F8"
                axis.text(x, 0.52, label, ha="center", va="center", fontsize=10,
                          bbox={"boxstyle": "round,pad=0.45", "facecolor": colour, "edgecolor": "#0B3A53"})
                if index < len(decision_steps) - 1:
                    axis.annotate("", xy=(x_positions[index + 1] - 0.055, 0.52), xytext=(x + 0.055, 0.52),
                                  arrowprops={"arrowstyle": "->", "color": "#0B3A53"})
            axis.set_title("Simplified classification decision order", color="#0B3A53", weight="bold")
            plt.tight_layout()
            plt.show()"""),
            md("""The diagram is deliberately a summary rather than a substitute for the detailed rules. Its implication is that a product label alone is not enough: a mortgage can fail property eligibility, a card can be a transactor or revolver, and any class can be replaced by defaulted treatment."""),
            md("""The same product can require different treatment when eligibility changes. A credit card may be a transactor or a revolving retail exposure. A mortgage uses real-estate treatment only when the property and underwriting conditions are satisfied. Default is an override because a defaulted loan no longer receives the performing treatment."""),
            md("""## Business products are not regulatory classes

            The next table shows the intended starting mapping. The classification notebook later tests the actual fields on every row rather than relying only on this label."""),
            code("""starting_map = pd.DataFrame([
                ["Sovereign bond", "Sovereign"], ["Bank loan", "Bank"],
                ["Corporate revolver", "Corporate"], ["SME revolver", "Corporate SME"],
                ["Personal loan", "Regulatory retail"], ["Credit card paid in full", "Retail transactor"],
                ["Credit card revolver", "Revolving retail"], ["Mortgage", "Residential real estate"],
            ], columns=["Business product", "Expected Basel class"])
            display(starting_map)"""),
            md("""This is an expectation rather than the final result. Borrower type, SME status, retail management, property eligibility, repayment behaviour and default status determine the final class stored on each loan."""),
        ],
        "The regulatory vocabulary is established. The next notebook creates the loan records and the variables required to test these definitions.",
    )))

    specs.append(("02_synthetic_bank_loan_portfolio.ipynb", notebook(
        "02", "Synthetic Bank Loans and Necessary Variables",
        "This notebook makes the complete loan-level dataset visible. It contains different products and the contractual, borrower, collateral, rating, recovery and maturity fields required later.",
        "Balances and commitments determine EAD. Borrower and collateral fields determine classification and risk weights. Rating, recovery and maturity fields determine the IRB capital function.",
        [("Drawn amount", "the amount already borrowed"), ("Undrawn amount", "the unused portion of a committed limit"), ("Commitment type", "the contractual category used to select a CCF"), ("Revolving facility", "credit that may be borrowed, repaid and borrowed again within a limit"), ("Synthetic", "artificial and reproducible rather than real customer data")],
        [
            md("""## One representative loan from every segment

            The sample prevents the backend file from remaining invisible. Monetary columns are displayed in INR crore. Revolving facilities show both drawn and undrawn amounts; term products generally have no unused commitment."""),
            code("""sample_columns = [
                "exposure_id", "segment", "product_type", "borrower_type",
                "internal_grade", "outstanding_balance", "credit_limit", "undrawn_amount",
                "commitment_type", "revolving_flag", "collateral_type",
                "property_value_current", "contractual_maturity_years", "default_flag",
            ]
            examples = (
                raw.sort_values(["segment", "exposure_id"])
                .groupby("segment", as_index=False)
                .first()[sample_columns]
                .copy()
            )
            money_columns = ["outstanding_balance", "credit_limit", "undrawn_amount", "property_value_current"]
            examples[money_columns] /= CRORE
            examples = examples.rename(columns={column: f"{column} (INR crore)" for column in money_columns})
            display(examples)"""),
            md("""The table shows why one uniform rule is insufficient. A corporate revolver and credit card both have undrawn capacity, but their borrower type and commitment terms differ. A mortgage has property values needed for LTV. A sovereign bond has no retail or property test."""),
            md("""## Dataset variable groups

            The major dataset contains inputs as well as calculated fields. The table below groups the most important variables by the question they answer."""),
            code("""variable_groups = pd.DataFrame({
                "Question": ["Which record?", "Who owes the money?", "What is the contract?", "What protection exists?", "What is the credit quality?", "What is needed for IRB recovery?"],
                "Important variables": [
                    "exposure_id, borrower_id, reporting_date",
                    "borrower_type, is_sme, managed_as_retail, annual_revenue",
                    "product_type, outstanding, limit, undrawn, commitment_type, maturity",
                    "collateral_type, property values, guarantee, senior lien",
                    "internal grade, external rating, default flag, days past due",
                    "normal/downturn recovery rates, costs, recovery time and LGD",
                ],
            })
            display(variable_groups)"""),
            md("""Every later parameter can therefore be traced to a loan characteristic. Regulatory outputs such as CCF, EAD, risk weight, PD, downturn LGD, correlation, K and RWA are added to the calculated loan file rather than hidden in a separate aggregate table."""),
            md("""## Record mix and monetary size

            The left measure counts loans. The right measure sums drawn balances. Corporate and sovereign records can be few but large, while retail segments can be numerous but individually small."""),
            code("""portfolio_mix = raw.groupby("segment").agg(
                loan_count=("exposure_id", "count"),
                drawn_balance=("outstanding_balance", "sum"),
            ).sort_values("drawn_balance")
            portfolio_mix["drawn_balance"] /= CRORE

            figure, axes = plt.subplots(1, 2, figsize=(14, 5))
            portfolio_mix["loan_count"].plot.barh(ax=axes[0], color=COLORS[2], title="Number of loans")
            portfolio_mix["drawn_balance"].plot.barh(ax=axes[1], color=COLORS[1], title="Drawn balance")
            axes[0].set_xlabel("Loan records")
            axes[1].set_xlabel("INR crore")
            axes[0].set_ylabel("")
            axes[1].set_ylabel("")
            plt.tight_layout()
            plt.show()"""),
            md("""Record count reflects operating volume. Drawn balance is closer to financial size, but it is still not EAD because undrawn commitments have not yet been converted. The next stages perform classification and EAD separately."""),
        ],
        "The bank now contains 30,000 visible loan-level records with the variables needed for both approaches. No aggregate risk weight has been assumed at this stage.",
    )))

    specs.append(("03_sa_loan_classification.ipynb", notebook(
        "03", "Standardised Approach Loan Classification",
        "This is the first Standardised Approach calculation. Every synthetic loan is tested against borrower, retail, property and default fields and assigned to one Basel class.",
        "The selected class determines the relevant CCF and risk-weight rule. Classification therefore controls the route to Standardised Approach Credit RWA.",
        [("Classification rule ID", "an audit label recording the rule that assigned a loan's class"), ("Performing class", "the class before a default override"), ("Default override", "replacement of performing treatment when the loan has defaulted")],
        [
            md("""## Loan-level classification examples

            One row from each final class shows the original segment, borrower information, final class and exact rule ID. The rule ID is project lineage; it is not itself a Basel category."""),
            code("""classification_columns = [
                "exposure_id", "segment", "product_type", "borrower_type", "is_sme",
                "managed_as_retail", "retail_transactor", "regulatory_real_estate_eligible",
                "default_flag", "performing_exposure_class", "basel_exposure_class",
                "classification_rule_id",
            ]
            classification_examples = (
                loans.sort_values(["basel_exposure_class", "exposure_id"])
                .groupby("basel_exposure_class", as_index=False)
                .first()[classification_columns]
            )
            display(classification_examples)"""),
            md("""The performing class remains visible even when default changes the final class. This preserves the underlying product type for IRB functions and analysis while ensuring the Standardised Approach uses the defaulted treatment."""),
            md("""## Portfolio after classification

            The chart compares the number of loans with EAD before CRM. EAD has already been calculated in the saved engine output, but it is analysed in detail only in the next notebook."""),
            code("""classified_profile = loans.groupby("basel_exposure_class").agg(
                loan_count=("exposure_id", "count"),
                ead=("ead_pre_crm", "sum"),
            ).sort_values("ead")
            classified_profile["ead"] /= CRORE

            figure, axes = plt.subplots(1, 2, figsize=(14, 5))
            classified_profile["loan_count"].plot.barh(ax=axes[0], color=COLORS[2], title="Loans in each Basel class")
            classified_profile["ead"].plot.barh(ax=axes[1], color=COLORS[1], title="EAD in each Basel class")
            axes[0].set_xlabel("Loan records")
            axes[1].set_xlabel("INR crore")
            axes[0].set_ylabel("")
            axes[1].set_ylabel("")
            plt.tight_layout()
            plt.show()"""),
            md("""A class with fewer loans can still dominate EAD because its facilities are larger. The Standardised Approach must therefore calculate each loan's exposure and risk weight before totals are compared."""),
        ],
        "Every loan now has a performing class, final Basel class and traceable classification rule. The next notebook calculates Standardised Approach EAD for each row.",
    )))

    specs.append(("04_sa_ead_and_ccf.ipynb", notebook(
        "04", "Standardised Approach EAD and CCF",
        "Classification is complete. This notebook converts contractual balances and commitments into Standardised Approach Exposure at Default for every loan.",
        "EAD is the rupee amount to which the Standardised Approach risk weight is applied. Understating undrawn exposure would understate RWA and overstate capital ratios.",
        [("CCF", "Credit Conversion Factor, the percentage of committed undrawn exposure included in EAD"), ("Funded exposure", "outstanding balance plus accrued interest"), ("Converted undrawn", "CCF multiplied by the undrawn amount"), ("CRM", "Credit Risk Mitigation recognised after pre-CRM EAD is calculated")],
        [
            md("""## Basel CCF reference table used by the engine

            The contract category selects the CCF. Broad product names do not select it. Most term loans have no undrawn commitment. A revolving facility can be unconditionally cancellable or another commitment, producing a different conversion."""),
            code("""ccf_table = pd.DataFrame(configs["ccf_parameters"]["rules"]).T.reset_index()
            ccf_table = ccf_table.rename(columns={"index": "Commitment type", "ccf": "CCF", "rule_id": "Rule ID", "basel_reference": "Basel reference"})
            display(ccf_table)"""),
            md("""A 40% CCF means 40% of the unused commitment enters EAD. It does not mean a 40% probability of default or a 40% loss. The CCF measures potential additional drawing before default."""),
            md("""## One revolving-loan calculation

            The example selects a loan with an undrawn amount and displays every term in `EAD = outstanding + accrued interest + CCF × undrawn`."""),
            code("""revolving_example = loans.loc[loans["undrawn_amount"].gt(0)].iloc[0]
            manual_ead = (
                revolving_example["outstanding_balance"]
                + revolving_example["accrued_interest"]
                + revolving_example["ccf"] * revolving_example["undrawn_amount"]
            )
            display(pd.Series({
                "Product": revolving_example["product_type"],
                "Commitment type": revolving_example["commitment_type"],
                "Outstanding (INR crore)": revolving_example["outstanding_balance"] / CRORE,
                "Accrued interest (INR crore)": revolving_example["accrued_interest"] / CRORE,
                "Undrawn (INR crore)": revolving_example["undrawn_amount"] / CRORE,
                "CCF": revolving_example["ccf"],
                "Converted undrawn (INR crore)": revolving_example["converted_undrawn"] / CRORE,
                "EAD before CRM (INR crore)": revolving_example["ead_pre_crm"] / CRORE,
            }).to_frame("Value"))
            assert np.isclose(manual_ead, revolving_example["ead_pre_crm"])"""),
            md("""The calculated EAD is larger than the current balance because the facility can be drawn further. That full EAD now becomes the exposure base for the risk-weight rules."""),
            md("""## Where converted undrawn exposure matters

            The stacked chart separates funded exposure from the CCF-converted undrawn amount by product. A visible second section identifies products whose current balances do not capture all potential exposure."""),
            code("""ead_parts = loans.groupby("product_type").agg(
                funded=("funded_exposure", "sum"),
                converted_undrawn=("converted_undrawn", "sum"),
            ).sort_values("funded") / CRORE
            ead_parts.plot.barh(stacked=True, figsize=(10, 5), color=[COLORS[1], COLORS[3]], title="Funded and converted-undrawn parts of EAD")
            plt.xlabel("INR crore")
            plt.ylabel("")
            plt.tight_layout()
            plt.show()"""),
            md("""Corporate and SME revolvers can produce large converted-undrawn exposure even when they are fewer in number. Credit cards can be numerous but small. The risk weight applied next acts on the combined EAD, not only on the current balance."""),
        ],
        "Every loan has a funded amount, commitment type, CCF, converted undrawn amount and Standardised Approach EAD before CRM.",
    )))

    specs.append(("05_sa_risk_weights_and_mortgage_ltv.ipynb", notebook(
        "05", "Standardised Approach Risk Weights and Mortgage LTV",
        "EAD is available for every loan. This notebook selects the applicable prescribed risk weight from the relevant Basel grid.",
        "The risk weight converts EAD into RWA. Higher risk weights create more RWA and require more capital for the same exposure amount.",
        [("Risk weight", "the prescribed percentage applied to EAD"), ("LTV", "loan amount divided by prudent property value"), ("Prudent property value", "the lower of the synthetic origination and current values in this implementation"), ("Income-dependent property", "a mortgage whose repayment materially depends on cash flow generated by the property")],
        [
            md("""## Rating-based and fixed risk-weight grids

            Sovereign, bank and corporate exposures use rating tables in this selected global Basel scope. Retail and SME classes use fixed weights. National implementation and external-rating eligibility can change these treatments."""),
            code("""for exposure_class, weights in configs["sa_risk_weights"]["rating_risk_weights"].items():
                print(exposure_class.upper())
                display(pd.Series(weights, name="Risk weight").to_frame())

            print("FIXED WEIGHTS")
            display(pd.Series(configs["sa_risk_weights"]["fixed_risk_weights"], name="Risk weight").to_frame())"""),
            md("""The tables are rule references, not portfolio results. Each loan retrieves one value after its class, rating and other eligibility fields are known."""),
            md("""## Residential mortgage LTV grids

            Mortgage EAD is not caused by LTV. LTV selects the risk weight. The loan amount used in LTV includes outstanding principal plus committed undrawn mortgage exposure. The engine then divides by prudent property value."""),
            code("""owner_grid = pd.DataFrame(configs["sa_risk_weights"]["mortgage_ltv_bands_not_income_dependent"])
            income_grid = pd.DataFrame(configs["sa_risk_weights"]["mortgage_ltv_bands_income_dependent"])
            for grid in (owner_grid, income_grid):
                grid["LTV band"] = grid["display_band"].fillna(
                    "Up to " + grid["max_ltv"].map(lambda value: f"{value:.0%}")
                )
            owner_grid["Mortgage repayment"] = "Not materially dependent on property cash flow"
            income_grid["Mortgage repayment"] = "Materially dependent on property cash flow"
            ltv_table = pd.concat([owner_grid, income_grid], ignore_index=True)
            display(ltv_table[["Mortgage repayment", "LTV band", "risk_weight"]].rename(columns={"risk_weight": "Risk weight"}))"""),
            md("""The last row means LTV above 100%. The number `999` exists only inside the lookup configuration to represent an open-ended final band; it is not an LTV and is not used as a customer value."""),
            md("""## What the mortgage grid looks like

            The step chart turns the table into the actual decision applied to a mortgage. Moving right means the loan is larger relative to the prudent property value. Each jump increases the prescribed risk weight, with the income-dependent route remaining higher."""),
            code("""ltv_axis = [0.0, 0.50, 0.60, 0.80, 0.90, 1.00, 1.20]
            owner_weights = [0.20, 0.25, 0.30, 0.40, 0.50, 0.70, 0.70]
            income_weights = [0.30, 0.35, 0.45, 0.60, 0.75, 1.05, 1.05]

            plt.figure(figsize=(10, 5))
            plt.step(ltv_axis, owner_weights, where="post", linewidth=2.5, label="Repayment not dependent on property income", color=COLORS[1])
            plt.step(ltv_axis, income_weights, where="post", linewidth=2.5, label="Repayment dependent on property income", color=COLORS[5])
            plt.xlabel("Loan-to-value ratio")
            plt.ylabel("Standardised Approach risk weight")
            plt.title("Residential mortgage risk weight rises in LTV steps")
            plt.gca().xaxis.set_major_formatter(lambda value, position: f"{value:.0%}")
            plt.gca().yaxis.set_major_formatter(lambda value, position: f"{value:.0%}")
            plt.legend()
            plt.tight_layout()
            plt.show()"""),
            md("""A mortgage just above a band boundary receives the next weight on the whole exposure under this implementation. This is why property value changes can affect Standardised Approach RWA even when the outstanding loan balance does not change."""),
            md("""At the same LTV, an income-dependent mortgage generally receives a higher weight because repayment relies more heavily on the property's cash generation. This is separate from the property value's effect on recovery and downturn LGD in IRB."""),
            md("""## Loan-level mortgage examples

            The table selects one mortgage from each applied risk-weight band and shows the complete LTV-to-risk-weight path."""),
            code("""mortgages = loans.loc[loans["performing_exposure_class"].eq("residential_real_estate")].copy()
            mortgage_examples = (
                mortgages.sort_values(["sa_risk_weight", "ltv"])
                .groupby(["property_cashflow_dependent", "sa_risk_weight"], as_index=False)
                .first()[["exposure_id", "property_cashflow_dependent", "ltv_loan_amount", "property_value_prudent", "ltv", "sa_risk_weight", "sa_rule_id"]]
            )
            mortgage_examples[["ltv_loan_amount", "property_value_prudent"]] /= CRORE
            display(mortgage_examples.rename(columns={"ltv_loan_amount": "Loan amount (INR crore)", "property_value_prudent": "Prudent property value (INR crore)"}))"""),
            md("""The rule ID identifies both the cash-flow dependency treatment and the selected LTV weight. The same fields remain on all mortgage rows, allowing the portfolio total to be traced back to individual properties and loans."""),
        ],
        "Each loan now has an applicable Standardised Approach risk weight and a rule ID explaining its source. Mortgage weights are explicitly linked to LTV bands.",
    )))

    specs.append(("06_sa_loan_level_rwa_and_total.ipynb", notebook(
        "06", "Loan-Level Standardised Approach RWA and Total",
        "This notebook completes the Standardised Approach. It multiplies each loan's post-CRM exposure by its risk weight, recognises any eligible guarantee split and then aggregates all loan results.",
        "Total Standardised Approach Credit RWA is the first completed credit-risk denominator and later provides the aggregate output-floor benchmark.",
        [("Post-CRM EAD", "EAD after eligible credit risk mitigation is recognised"), ("Guarantee substitution", "use of the eligible guarantor's weight on the protected portion"), ("RWA density", "RWA divided by EAD")],
        [
            md("""## Representative loan calculations

            One performing loan from each exposure class shows EAD, risk weight and RWA. `SA RWA before guarantee` is the direct `EAD × risk weight` calculation. Final SA RWA reflects an eligible guarantee split where present."""),
            code("""sa_examples = (
                loans.loc[loans["default_flag"].eq(0)]
                .sort_values(["basel_exposure_class", "exposure_id"])
                .groupby("basel_exposure_class", as_index=False)
                .first()[["exposure_id", "basel_exposure_class", "sa_ead_post_crm", "sa_risk_weight", "sa_rwa_before_guarantee", "guaranteed_portion", "sa_rwa", "sa_rule_id"]]
            )
            money_columns = ["sa_ead_post_crm", "sa_rwa_before_guarantee", "guaranteed_portion", "sa_rwa"]
            sa_examples[money_columns] /= CRORE
            display(sa_examples.rename(columns={column: f"{column} (INR crore)" for column in money_columns}))"""),
            md("""When no guarantee applies, final RWA equals EAD multiplied by the borrower risk weight. A protected portion can use the eligible guarantor's weight. This changes the risk treatment without removing the legal loan exposure."""),
            md("""## Total Standardised Approach Credit RWA

            The chart shows EAD and RWA by class. The gap reflects prescribed risk weights and recognised protection. RWA density isolates the risk intensity from the rupee size of the class."""),
            code("""sa_total = loans.groupby("basel_exposure_class").agg(
                ead=("sa_ead_post_crm", "sum"),
                rwa=("sa_rwa", "sum"),
            ).sort_values("ead")
            sa_total["rwa_density"] = sa_total["rwa"] / sa_total["ead"]
            sa_total[["ead", "rwa"]] /= CRORE

            figure, axes = plt.subplots(1, 2, figsize=(14, 5))
            sa_total[["ead", "rwa"]].plot.barh(ax=axes[0], color=[COLORS[1], COLORS[4]], title="SA EAD and RWA by class")
            sa_total["rwa_density"].plot.barh(ax=axes[1], color=COLORS[5], title="SA RWA density")
            axes[0].set_xlabel("INR crore")
            axes[1].set_xlabel("RWA divided by EAD")
            axes[1].xaxis.set_major_formatter(lambda value, position: f"{value:.0%}")
            axes[0].set_ylabel("")
            axes[1].set_ylabel("")
            plt.tight_layout()
            plt.show()"""),
            md("""A class can drive total RWA because it is large, because its risk weight is high, or both. The two charts distinguish these explanations."""),
            md("""## Loan-to-total reconciliation

            The total below is the direct sum of all 30,000 loan-level SA RWA values. It is compared with the saved class summary to prove that aggregation did not lose or duplicate any loan."""),
            code("""loan_level_total = loans["sa_rwa"].sum()
            saved_summary = pd.read_csv(ROOT / "outputs/tables/sa_summary.csv")
            summary_total = saved_summary["sa_rwa"].sum()
            difference = loan_level_total - summary_total

            display(pd.Series({
                "Loan-level SA Credit RWA (INR crore)": loan_level_total / CRORE,
                "Class-summary SA Credit RWA (INR crore)": summary_total / CRORE,
                "Difference (INR crore)": difference / CRORE,
                "Status": "PASS" if np.isclose(difference, 0) else "FAIL",
            }).to_frame("Value"))
            assert np.isclose(difference, 0)"""),
            md("""The PASS result completes the Standardised Approach. The IRB section begins from the same loan portfolio but develops a different risk-sensitive capital calculation."""),
        ],
        "Standardised Approach Credit RWA is complete at loan, exposure-class and portfolio level and reconciles without an unexplained difference.",
    )))

    specs.append(("07_irb_scope_and_parameter_sources.ipynb", notebook(
        "07", "IRB Scope, Eligibility and Four Risk Components",
        "The Standardised Approach is complete. This notebook begins IRB by separating PD, LGD, EAD and maturity and by showing where own estimates are used or restricted.",
        "The four risk components enter the Basel IRB capital functions. The output is unexpected-loss capital K and IRB Credit RWA.",
        [("IRB", "Internal Ratings-Based approach"), ("A-IRB", "Advanced IRB, using eligible own estimates of LGD and EAD as well as PD"), ("F-IRB", "Foundation IRB, using supervisory LGD or EAD parameters where required"), ("Retail IRB", "retail treatment using pool-level own estimates and retail risk functions")],
        [
            md("""## The four loan-level IRB components

            The table keeps parameter estimation separate from the final formula. Each component receives its own notebook before capital K is calculated."""),
            code("""components = pd.DataFrame([
                ["PD", "Long-run average one-year default rate for a borrower grade or retail pool", "Borrower or pool"],
                ["LGD", "Economic loss percentage under downturn conditions", "Facility"],
                ["EAD", "Funded exposure plus expected conversion of undrawn commitments", "Facility"],
                ["M", "Effective remaining maturity, where the risk function uses it", "Facility"],
            ], columns=["Component", "Meaning", "Primary level"])
            display(components)"""),
            md("""## How the four components meet in the capital formula

            PD describes the borrower or pool. LGD, EAD and maturity describe the facility. PD, LGD and applicable maturity treatment produce capital K through the Basel risk function. EAD then scales K into a monetary capital amount and RWA."""),
            code("""figure, axis = plt.subplots(figsize=(12, 3.5))
            axis.axis("off")
            risk_inputs = [(0.08, "PD\\nDefault chance"), (0.28, "LGD\\nLoss severity"), (0.48, "M\\nTime remaining")]
            for x, label in risk_inputs:
                axis.text(x, 0.68, label, ha="center", va="center", fontsize=11,
                          bbox={"boxstyle": "round,pad=0.5", "facecolor": "#EAF2F8", "edgecolor": "#1F77B4"})
                axis.annotate("", xy=(0.64, 0.62), xytext=(x + 0.055, 0.66),
                              arrowprops={"arrowstyle": "->", "color": "#0B3A53"})
            axis.text(0.70, 0.62, "Basel risk\\nfunction", ha="center", va="center", fontsize=11, weight="bold",
                      bbox={"boxstyle": "round,pad=0.55", "facecolor": "#E9C46A", "edgecolor": "#0B3A53"})
            axis.annotate("", xy=(0.84, 0.62), xytext=(0.76, 0.62), arrowprops={"arrowstyle": "->", "color": "#0B3A53", "lw": 1.8})
            axis.text(0.87, 0.62, "K", ha="center", va="center", fontsize=13, weight="bold")

            axis.text(0.46, 0.20, "EAD\\nExposure amount", ha="center", va="center", fontsize=11,
                      bbox={"boxstyle": "round,pad=0.5", "facecolor": "#EAF2F8", "edgecolor": "#1F77B4"})
            axis.text(0.86, 0.20, "IRB RWA", ha="center", va="center", fontsize=12, weight="bold",
                      bbox={"boxstyle": "round,pad=0.5", "facecolor": "#D8F3DC", "edgecolor": "#2A9D8F"})
            axis.annotate("", xy=(0.80, 0.20), xytext=(0.53, 0.20), arrowprops={"arrowstyle": "->", "color": "#0B3A53"})
            axis.annotate("", xy=(0.84, 0.27), xytext=(0.87, 0.55), arrowprops={"arrowstyle": "->", "color": "#0B3A53"})
            axis.text(0.67, 0.08, "IRB RWA = K × EAD × 12.5", ha="center", fontsize=12, weight="bold", color="#0B3A53")
            plt.tight_layout()
            plt.show()"""),
            md("""The arrows explain the division of work across the following notebooks. PD and LGD measure risk, EAD scales it into money, and maturity modifies applicable non-retail capital. Correlation is prescribed later inside the risk function."""),
            md("""PD is primarily tied to borrower grade for corporate, bank and sovereign exposures and to pools for retail. LGD, EAD and maturity depend more directly on facility structure, collateral, recovery and commitment terms."""),
            md("""## Parameter source used in the educational engine

            Current Basel restrictions mean A-IRB is not permitted for bank exposures and certain large general corporates. Retail has its own IRB treatment. The field below prevents the project from calling every row A-IRB."""),
            code("""parameter_sources = loans.groupby(["performing_exposure_class", "irb_parameter_source", "airb_restriction_flag"], as_index=False).agg(
                loans=("exposure_id", "count"),
                ead=("ead_irb", "sum"),
            )
            parameter_sources["ead"] /= CRORE
            display(parameter_sources.rename(columns={"ead": "IRB EAD (INR crore)"}))"""),
            md("""`AIRB_OWN_ESTIMATES_EDUCATIONAL` marks exposures for which the project demonstrates own PD, LGD and EAD estimates. `FOUNDATION_SUPERVISORY_PARAMETERS` marks current restrictions. The capital function can still be displayed for comparison, but the source label prevents an inaccurate approval claim."""),
        ],
        "Every exposure has a visible IRB family, eligibility flag and parameter source. PD is developed next from synthetic long-run grade or pool experience.",
    )))

    specs.append(("08_irb_long_run_pd_and_transitions.ipynb", notebook(
        "08", "Long-Run PD and Rating Transition Matrices",
        "This notebook estimates the first IRB component. Transparent synthetic one-year transition matrices provide a default-column probability for each borrower grade or retail pool.",
        "PD affects expected loss, correlation, conditional default probability and capital K. A higher assigned PD generally increases IRB RWA, although the formula is nonlinear.",
        [("Long-run PD", "average one-year default experience across representative good and bad years"), ("Transition matrix", "probabilities of staying in a grade, migrating or defaulting over one year"), ("D column", "the probability of moving to default within one year"), ("Count weighted", "based on numbers of borrowers rather than exposure amounts")],
        [
            md("""## Synthetic matrices by IRB exposure family

            Basel does not prescribe these numerical transition probabilities. The project uses deliberately labelled synthetic anchors that follow believable ordering: stronger grades default less often and weaker grades migrate or default more often. Real IRB estimation requires observed multi-year data and validation."""),
            code("""from basel_credit_risk.pd_transition import build_transition_matrix

            transition_config = configs["pd_transition_assumptions"]
            matrices = {}
            for profile_name, profile in transition_config["profiles"].items():
                matrix = build_transition_matrix(
                    profile,
                    transition_config["matrix_method"],
                    transition_config["grade_order"],
                )
                matrices[profile_name] = matrix
                print(profile_name.replace("_", " ").upper())
                display(matrix.style.format("{:.3%}"))"""),
            md("""Each row totals 100%. The D column is carried into the loan dataset as the long-run one-year PD for that grade or retail pool. The matrices are not presented as agency data or a fitted model."""),
            md("""## Long-run PD curves across exposure families

            The chart compares the D-column probabilities. It makes the assumptions visible: the same letter grade can have different default experience across sovereign, bank, corporate and retail families."""),
            code("""pd_curves = pd.DataFrame({
                profile: matrix.loc[matrix.index != "D", "D"]
                for profile, matrix in matrices.items()
            })
            pd_curves.plot(figsize=(11, 5), marker="o", title="Synthetic long-run one-year PD by grade and exposure family")
            plt.yscale("log")
            plt.xlabel("Internal grade or retail risk band")
            plt.ylabel("One-year PD on logarithmic scale")
            plt.tight_layout()
            plt.show()"""),
            md("""The logarithmic axis keeps very small investment-grade PDs visible beside weaker grades. The ordered increase is more important than a false claim of precise historical calibration."""),
            md("""## Assignment to individual loans

            One loan from each profile and grade is shown with the transition profile, internal grade, D-column PD and regulatory PD after any floor or default treatment."""),
            code("""pd_examples = (
                loans.sort_values(["pd_transition_profile", "internal_grade", "exposure_id"])
                .groupby(["pd_transition_profile", "internal_grade"], as_index=False)
                .first()[["exposure_id", "pd_transition_profile", "internal_grade", "pd_long_run", "pd_floor_applied", "pd_regulatory", "pd_source"]]
            )
            display(pd_examples.style.format({"pd_long_run": "{:.3%}", "pd_floor_applied": "{:.3%}", "pd_regulatory": "{:.3%}"}))"""),
            md("""Loans do not receive random independent PDs after this step. They inherit the long-run PD of their grade or retail pool, preserving a coherent connection between the transition table and the capital calculation."""),
        ],
        "Every loan now has a transparent long-run one-year PD, its transition profile, grade and parameter source.",
    )))

    specs.append(("09_irb_downturn_lgd.ipynb", notebook(
        "09", "Facility-Level Downturn LGD",
        "PD is complete. This notebook estimates how much of EAD would be lost after recoveries and costs, with a separate downturn view for each facility.",
        "Downturn LGD enters expected loss and the IRB unexpected-loss capital function. Lower collateral recovery, longer workouts and higher costs increase LGD and usually increase IRB RWA.",
        [("Economic loss", "EAD minus discounted recoveries plus material workout costs"), ("Normal LGD", "loss severity under ordinary recovery assumptions"), ("Downturn LGD", "loss severity reflecting periods of high credit losses where relevant"), ("Workout cost", "legal, servicing and recovery expense associated with default")],
        [
            md("""## Recovery-to-LGD calculation

            For each facility, collateral and unsecured recoveries are estimated, discounted over the recovery period and reduced for workout cost. Downturn assumptions lower recovery rates, increase costs and extend recovery time. Downturn LGD cannot fall below normal LGD in this implementation."""),
            code("""lgd_example = loans.loc[loans["collateral_value"].gt(0)].iloc[0]
            display(pd.Series({
                "Product": lgd_example["product_type"],
                "EAD (INR crore)": lgd_example["ead_pre_crm"] / CRORE,
                "Collateral value (INR crore)": lgd_example["collateral_value"] / CRORE,
                "Normal discounted recovery (INR crore)": lgd_example["normal_discounted_recovery"] / CRORE,
                "Normal workout cost (INR crore)": lgd_example["normal_workout_cost"] / CRORE,
                "Normal LGD": lgd_example["normal_lgd"],
                "Downturn discounted recovery (INR crore)": lgd_example["downturn_discounted_recovery"] / CRORE,
                "Downturn workout cost (INR crore)": lgd_example["downturn_workout_cost"] / CRORE,
                "Downturn LGD": lgd_example["downturn_lgd"],
            }).to_frame("Value"))"""),
            md("""The difference between normal and downturn LGD is not a universal fixed add-on. It comes from the facility's collateral, unsecured recovery, cost and timing assumptions. The values remain explicitly synthetic rather than being described as a bank-calibrated model."""),
            md("""## Normal and downturn LGD by product

            The chart shows EAD-weighted average LGD. Secured products can have lower normal LGD, but downturn collateral and recovery assumptions narrow that benefit."""),
            code("""lgd_by_product = loans.groupby("product_type").apply(
                lambda group: pd.Series({
                    "Normal LGD": np.average(group["normal_lgd"], weights=group["ead_irb"]),
                    "Downturn LGD": np.average(group["downturn_lgd"], weights=group["ead_irb"]),
                }),
                include_groups=False,
            ).sort_values("Downturn LGD")
            lgd_by_product.plot.barh(figsize=(10, 5), color=[COLORS[2], COLORS[5]], title="Normal and downturn LGD by product")
            plt.xlabel("EAD-weighted LGD")
            plt.ylabel("")
            plt.gca().xaxis.set_major_formatter(lambda value, position: f"{value:.0%}")
            plt.tight_layout()
            plt.show()"""),
            md("""The gap between each pair of bars is the downturn effect. A higher downturn LGD means a larger share of EAD is assumed to remain unrecovered during difficult conditions and therefore increases both expected and unexpected loss measures."""),
        ],
        "Every facility has visible recovery rates, recovery time, workout cost, normal LGD and downturn LGD. Downturn LGD is carried into the IRB formula.",
    )))

    specs.append(("10_irb_ead_and_maturity.ipynb", notebook(
        "10", "IRB EAD and Effective Maturity",
        "PD and LGD are available. This notebook estimates IRB EAD for funded and revolving facilities and applies the effective-maturity bounds used by applicable non-retail risk functions.",
        "IRB EAD scales the capital requirement into rupees. Effective maturity adjusts corporate, sovereign and bank capital; the selected retail functions do not use the same maturity adjustment.",
        [("Own CCF estimate", "a synthetic facility-level conversion assumption used where own EAD estimation is represented"), ("Effective maturity", "remaining contractual economic maturity used in the IRB function"), ("Maturity floor", "one year for the ordinary scope represented here"), ("Maturity cap", "five years for the ordinary scope represented here")],
        [
            md("""## Standardised Approach CCF versus IRB CCF

            Foundation-parameter rows retain supervisory CCF treatment. Eligible own-estimate and retail rows use the project's explicit synthetic own CCF assumptions. The source field keeps these routes separate."""),
            code("""ccf_comparison = loans.groupby(["commitment_type", "irb_ccf_source"], as_index=False).agg(
                loans=("exposure_id", "count"),
                average_sa_ccf=("ccf", "mean"),
                average_irb_ccf=("irb_ccf", "mean"),
                undrawn=("undrawn_amount", "sum"),
            )
            ccf_comparison["undrawn"] /= CRORE
            display(ccf_comparison.rename(columns={"undrawn": "Undrawn (INR crore)"}))"""),
            md("""IRB EAD remains `funded exposure + IRB CCF × undrawn`. The difference is the parameter source, not the arithmetic. A higher own CCF assumption increases IRB EAD and therefore IRB RWA."""),
            md("""## Maturity floor and cap

            Contractual maturity is the starting value. Ordinary effective maturity is floored at one year and capped at five years. The table makes the requested examples explicit."""),
            code("""maturity_examples = pd.DataFrame({
                "Contractual maturity": [0.5, 1, 2, 3, 4, 5, 6, 7],
            })
            maturity_examples["Effective maturity"] = maturity_examples["Contractual maturity"].clip(1, 5)
            display(maturity_examples)"""),
            md("""The line below makes both limits visible. Below one year, the ordinary floor lifts M to one. Between one and five years, M follows the contract. Beyond five years, the cap holds M at five."""),
            code("""contractual_years = np.linspace(0, 8, 81)
            effective_years = np.clip(contractual_years, 1, 5)

            plt.figure(figsize=(10, 4.5))
            plt.plot(contractual_years, contractual_years, linestyle="--", color="#9AA0A6", label="No floor or cap")
            plt.plot(contractual_years, effective_years, linewidth=3, color=COLORS[1], label="Effective maturity used")
            plt.axhline(1, color=COLORS[2], linewidth=1, alpha=0.7)
            plt.axhline(5, color=COLORS[5], linewidth=1, alpha=0.7)
            plt.xlabel("Contractual maturity in years")
            plt.ylabel("Effective maturity M")
            plt.title("Ordinary IRB maturity floor and cap")
            plt.legend()
            plt.tight_layout()
            plt.show()"""),
            md("""The flat sections are important for interpretation: a six-year and an eight-year loan both enter this ordinary calculation with M equal to five, while a six-month loan enters with M equal to one."""),
            md("""A six- or seven-year facility therefore enters the ordinary corporate maturity adjustment with M equal to five. Retail risk functions retain the maturity field for traceability but their maturity adjustment is one."""),
            md("""## Loan-level EAD and maturity examples

            The table shows one row for each product and parameter source, including the funded amount, undrawn amount, IRB CCF, resulting EAD and capped maturity."""),
            code("""irb_ead_examples = (
                loans.sort_values(["product_type", "irb_parameter_source", "exposure_id"])
                .groupby(["product_type", "irb_parameter_source"], as_index=False)
                .first()[["exposure_id", "product_type", "irb_parameter_source", "funded_exposure", "undrawn_amount", "irb_ccf", "ead_irb", "maturity_input", "m_effective", "maturity_cap_applied"]]
            )
            money_columns = ["funded_exposure", "undrawn_amount", "ead_irb"]
            irb_ead_examples[money_columns] /= CRORE
            display(irb_ead_examples.rename(columns={column: f"{column} (INR crore)" for column in money_columns}))"""),
            md("""This table completes the four IRB inputs. Each loan now has PD, downturn LGD, IRB EAD and effective maturity before the correlation and Vasicek capital function is applied."""),
        ],
        "IRB EAD and maturity are complete at loan level, with the CCF source, maturity floor and maturity cap recorded explicitly.",
    )))

    specs.append(("11_irb_correlation_vasicek_and_k.ipynb", notebook(
        "11", "IRB Correlation, Conditional PD and Capital K",
        "The four risk components are complete. This notebook applies the Basel correlation relationship and the one-factor Vasicek capital function to each performing loan.",
        "Capital K represents unexpected-loss capital per unit of EAD. Multiplying K by EAD and 12.5 produces IRB RWA.",
        [("Asset correlation R", "the Basel relationship between a borrower or pool and the common systematic risk factor"), ("99.9% conditional PD", "default probability conditional on a severe systematic state used by the regulatory formula"), ("Capital K", "unexpected-loss capital as a fraction of EAD"), ("Maturity adjustment", "the applicable non-retail adjustment for effective maturity")],
        [
            md("""## Correlation treatment by IRB family

            Residential mortgage correlation is 15%. Qualifying revolving retail correlation is 4%. Other retail and corporate-family correlations vary with PD. Eligible corporate SMEs also receive the Basel sales-size adjustment."""),
            code("""correlation_reference = pd.DataFrame([
                ["Corporate, bank and sovereign", "PD-dependent function between approximately 12% and 24%", "Maturity adjustment applies"],
                ["Corporate SME", "Corporate PD function less eligible sales-size adjustment", "Maturity adjustment applies"],
                ["Residential mortgage", "15%", "No full maturity adjustment"],
                ["Qualifying revolving retail", "4%", "No full maturity adjustment"],
                ["Other retail", "PD-dependent function between approximately 3% and 16%", "No full maturity adjustment"],
            ], columns=["IRB family", "Correlation R", "Maturity treatment"])
            display(correlation_reference)"""),
            md("""Correlation is prescribed by the Basel risk function rather than estimated independently for every synthetic loan. Different values explain why two loans with the same PD and LGD can still produce different capital intensity."""),
            md("""## One complete Vasicek calculation

            The selected performing corporate loan shows ordinary PD, 99.9% conditional PD, downturn LGD, maturity adjustment and capital K. The conditional PD is a regulatory tail-state calculation, not a forecast that this borrower will default with that probability."""),
            code("""vasicek_example = loans.loc[
                loans["irb_function"].eq("corporate") & loans["default_flag"].eq(0)
            ].iloc[0]
            base_unexpected_loss = vasicek_example["lgd_regulatory"] * (
                vasicek_example["conditional_pd_999"] - vasicek_example["pd_regulatory"]
            )
            manual_k = max(base_unexpected_loss * vasicek_example["maturity_adjustment"], 0)

            display(pd.Series({
                "PD": vasicek_example["pd_regulatory"],
                "Downturn LGD": vasicek_example["lgd_regulatory"],
                "Correlation R": vasicek_example["asset_correlation_r"],
                "99.9% conditional PD": vasicek_example["conditional_pd_999"],
                "LGD × (conditional PD − PD)": base_unexpected_loss,
                "Maturity adjustment": vasicek_example["maturity_adjustment"],
                "Capital K": vasicek_example["capital_k"],
            }).to_frame("Value"))
            assert np.isclose(manual_k, vasicek_example["capital_k"])"""),
            md("""If conditional PD were 15%, ordinary PD 2% and LGD 40%, the pre-maturity result would be `40% × (15% − 2%) = 5.2%`. Corporate K can then change through the maturity adjustment. Retail K uses its relevant correlation but no full maturity adjustment."""),
            md("""## Loan-level capital intensity

            Each point is a performing loan. The horizontal axis is PD and the vertical axis is K. Colour represents downturn LGD. The chart shows why capital is nonlinear rather than a fixed multiple of PD."""),
            code("""plot_sample = loans.loc[loans["default_flag"].eq(0)].sample(4000, random_state=42)
            plt.figure(figsize=(10, 5))
            points = plt.scatter(plot_sample["pd_regulatory"], plot_sample["capital_k"], c=plot_sample["lgd_regulatory"], s=14, alpha=0.45, cmap="viridis")
            plt.xscale("log")
            plt.xlabel("Long-run regulatory PD on logarithmic scale")
            plt.ylabel("Capital K")
            plt.title("Unexpected-loss capital across PD and downturn LGD")
            plt.colorbar(points, label="Downturn LGD")
            plt.tight_layout()
            plt.show()"""),
            md("""Higher PD and LGD generally move points upward, but correlation and maturity also matter. K is the risk intensity carried into the loan-level IRB RWA calculation next."""),
        ],
        "Every performing loan now has correlation, 99.9% conditional PD, maturity adjustment and capital K. Defaulted rows retain separate expected-loss treatment and zero performing-loan K in this scope.",
    )))

    specs.append(("12_irb_loan_level_rwa_and_total.ipynb", notebook(
        "12", "Loan-Level IRB RWA and Total",
        "This notebook completes IRB by multiplying each loan's capital K by IRB EAD and 12.5, then summing the results.",
        "IRB Credit RWA becomes the model-based credit component of aggregate RWA. The same loan-level records also retain expected loss separately.",
        [("Expected loss", "PD multiplied by LGD and EAD"), ("Unexpected-loss capital", "capital K multiplied by EAD"), ("12.5 conversion", "the inverse of 8%, used to express capital as RWA")],
        [
            md("""## Representative loan-level calculations

            One loan from each IRB family displays PD, downturn LGD, EAD, maturity, correlation, K and RWA. Every loan can therefore be recalculated from visible intermediate fields."""),
            code("""irb_examples = (
                loans.loc[loans["default_flag"].eq(0)]
                .sort_values(["irb_function", "exposure_id"])
                .groupby("irb_function", as_index=False)
                .first()[["exposure_id", "irb_function", "pd_regulatory", "lgd_regulatory", "ead_irb", "m_effective", "asset_correlation_r", "conditional_pd_999", "capital_k", "expected_loss_amount", "irb_rwa"]]
            )
            irb_examples[["ead_irb", "expected_loss_amount", "irb_rwa"]] /= CRORE
            display(irb_examples.rename(columns={"ead_irb": "EAD (INR crore)", "expected_loss_amount": "Expected loss (INR crore)", "irb_rwa": "IRB RWA (INR crore)"}))"""),
            md("""Expected loss and RWA are not interchangeable. Expected loss represents average credit loss. IRB RWA represents the unexpected-loss capital requirement expressed in a common RWA denominator."""),
            md("""## IRB Credit RWA by exposure class

            EAD shows portfolio size. IRB RWA shows capital-weighted risk after the nonlinear function. The difference between the bars varies by PD, downturn LGD, correlation and maturity."""),
            code("""irb_total = loans.groupby("performing_exposure_class").agg(
                ead=("ead_irb", "sum"),
                expected_loss=("expected_loss_amount", "sum"),
                irb_rwa=("irb_rwa", "sum"),
            ).sort_values("ead") / CRORE
            irb_total[["ead", "irb_rwa"]].plot.barh(figsize=(10, 5), color=[COLORS[1], COLORS[4]], title="IRB EAD and Credit RWA by class")
            plt.xlabel("INR crore")
            plt.ylabel("")
            plt.tight_layout()
            plt.show()"""),
            md("""A class can have lower IRB RWA than EAD without being risk free. K is a capital percentage and the 12.5 conversion determines the resulting RWA density."""),
            md("""## Formula and aggregation reconciliation

            The first control proves `IRB RWA = 12.5 × K × EAD` for all loans. The second proves that the saved class summary equals the direct loan-level sum."""),
            code("""formula_rwa = 12.5 * loans["capital_k"] * loans["ead_irb"]
            formula_difference = loans["irb_rwa"] - formula_rwa
            saved_irb_summary = pd.read_csv(ROOT / "outputs/tables/irb_summary.csv")
            aggregation_difference = loans["irb_rwa"].sum() - saved_irb_summary["irb_rwa"].sum()

            display(pd.DataFrame({
                "Control": ["Loan formula", "Loan sum to class summary"],
                "Difference (INR crore)": [formula_difference.abs().max() / CRORE, aggregation_difference / CRORE],
                "Status": ["PASS" if formula_difference.abs().max() < 0.01 else "FAIL", "PASS" if abs(aggregation_difference) < 0.01 else "FAIL"],
            }))
            assert formula_difference.abs().max() < 0.01
            assert abs(aggregation_difference) < 0.01"""),
            md("""Both PASS results complete IRB at loan and portfolio level. The next notebook compares the completed Standardised Approach and IRB totals."""),
        ],
        "Total IRB Credit RWA is the reconciled sum of loan-level `12.5 × K × EAD` calculations. Expected loss remains separately reported.",
    )))

    specs.append(("13_sa_irb_comparison_and_output_floor.ipynb", notebook(
        "13", "SA, IRB and the Aggregate Output Floor",
        "Both credit approaches are now complete. This notebook compares them and applies the output floor after adding market and operational RWA.",
        "Final aggregate RWA is the larger of model aggregate RWA and the configured floor amount. It becomes the denominator used for capital adequacy.",
        [("Model aggregate RWA", "IRB Credit RWA plus market and operational RWA"), ("Standardised aggregate base", "SA Credit RWA plus market and operational RWA"), ("Output floor", "a percentage of the standardised aggregate base"), ("Binding", "the floor exceeds model aggregate RWA and becomes final RWA")],
        [
            md("""## Completed Credit RWA approaches by class

            The paired bars compare two methods on the same synthetic loans. Standardised Approach RWA comes from prescribed weights. IRB RWA comes from risk parameters and capital functions."""),
            code("""approach_comparison = loans.groupby("performing_exposure_class").agg(
                sa_rwa=("sa_rwa", "sum"),
                irb_rwa=("irb_rwa", "sum"),
            ).sort_values("sa_rwa") / CRORE
            approach_comparison.plot.barh(figsize=(10, 5), color=[COLORS[1], COLORS[4]], title="Standardised Approach and IRB Credit RWA")
            plt.xlabel("INR crore")
            plt.ylabel("")
            plt.tight_layout()
            plt.show()"""),
            md("""A lower IRB bar does not mean the loan disappeared or necessarily became safer. The methods translate risk differently. The output floor limits the aggregate capital benefit from model-based RWA."""),
            md("""## Aggregate floor calculation

            The table shows the complete bank-level comparison. The floor is not applied to each loan separately."""),
            code("""floor_table = pd.read_csv(ROOT / "outputs/tables/output_floor.csv")
            base_floor = floor_table.loc[floor_table["scenario"].eq("base")].copy()
            monetary = base_floor["metric"].ne("Output-floor rate")
            base_floor.loc[monetary, "value"] /= CRORE
            display(base_floor.rename(columns={"value": "Value (INR crore, except rate)"}))"""),
            md("""Market and operational RWA appear in both sides of the comparison because capital adequacy covers all three major risk categories. The final aggregate amount is the larger result and is carried into capital ratios."""),
        ],
        "The completed SA and IRB calculations have been compared, and final aggregate RWA has been determined through the configured output floor.",
    )))

    specs.append(("14_stress_testing_and_capital_adequacy.ipynb", notebook(
        "14", "Stress Testing and Capital Adequacy",
        "Only after both approaches and the output floor are complete does the project apply adverse assumptions and recalculate the chain.",
        "Stress can reduce the capital numerator through losses and increase the RWA denominator through PD, LGD, EAD and risk-weight changes.",
        [("Scenario", "a defined set of risk shocks rather than a forecast"), ("Stress loss", "the project loss deduction applied to CET1"), ("CET1 ratio", "Common Equity Tier 1 capital divided by final total RWA"), ("Headroom", "the ratio minus its configured requirement and buffer")],
        [
            md("""## Scenario assumptions and recalculated results

            PD multipliers, LGD add-ons, collateral shocks and additional drawdowns feed back into loan-level calculations. The table reports the resulting EAD, SA RWA, IRB RWA, expected loss and final total RWA."""),
            code("""display(pd.DataFrame(configs["stress_scenarios"]["scenarios"]).T)

            scenario_results = pd.read_csv(ROOT / "outputs/tables/scenario_summary.csv").set_index("scenario").reindex(["base", "adverse", "severe"])
            money_columns = ["ead", "sa_credit_rwa", "irb_credit_rwa", "expected_loss", "final_total_rwa", "stress_loss"]
            scenario_display = scenario_results.copy()
            scenario_display[money_columns] /= CRORE
            display(scenario_display.rename(columns={column: f"{column} (INR crore)" for column in money_columns}))"""),
            md("""The scenarios affect more than one output. Greater drawdown raises EAD; weaker credit raises PD and LGD; lower property value can raise mortgage LTV weights and reduce recoveries. These movements increase expected loss and can increase both RWA approaches."""),
            md("""## Capital ratios after the stressed calculation

            The chart combines the stressed capital numerator and final RWA denominator. The threshold already includes the configured conservation buffer."""),
            code("""capital = pd.read_csv(ROOT / "outputs/tables/capital_adequacy.csv")
            capital_chart = capital.pivot(index="scenario", columns="capital_measure", values="ratio").reindex(["base", "adverse", "severe"])
            capital_chart.plot.bar(figsize=(11, 5), color=COLORS[:3], title="Capital ratios under base and stressed conditions")
            plt.ylabel("Capital ratio")
            plt.xlabel("Scenario")
            plt.gca().yaxis.set_major_formatter(lambda value, position: f"{value:.0%}")
            plt.xticks(rotation=0)
            plt.tight_layout()
            plt.show()"""),
            md("""Falling ratios show less eligible capital for each rupee of RWA. A ratio can decline because capital falls, RWA rises or both occur together. Headroom is therefore calculated against each capital layer's configured threshold."""),
            md("""## Capital amount, RWA and headroom

            The table makes the numerator, denominator and resulting headroom visible for CET1, Tier 1 and total capital."""),
            code("""capital_display = capital.copy()
            capital_display[["capital_amount", "total_rwa", "stress_loss"]] /= CRORE
            display(capital_display.rename(columns={"capital_amount": "Capital (INR crore)", "total_rwa": "Total RWA (INR crore)", "stress_loss": "Stress loss (INR crore)"}))"""),
            md("""The final capital measures now reflect the entire sequence from individual loans through both credit approaches, the output floor and stress effects."""),
        ],
        "Base, adverse and severe loan-level calculations have been translated into final RWA, capital ratios and headroom.",
    )))

    specs.append(("15_end_to_end_loan_trace_and_controls.ipynb", notebook(
        "15", "End-to-End Loan Trace and Controls",
        "The final notebook follows one loan from raw contract fields through Standardised Approach and IRB, then reconciles all loan-level amounts with portfolio summaries.",
        "Traceability and reconciliations do not create capital. They provide evidence that reported RWA and capital ratios are supported by the underlying loan calculations.",
        [("Calculation trace", "ordered inputs, rules, intermediate values and outputs for one loan"), ("Reconciliation", "comparison of independently aggregated totals"), ("Tolerance", "a very small accepted numerical difference"), ("Control status", "PASS when the difference is within tolerance")],
        [
            md("""## One loan from contract to both RWA approaches

            The selected revolving loan shows the chronological path: class, CCF, EAD, risk weight, SA RWA, PD, downturn LGD, IRB EAD, maturity, correlation, conditional PD, K and IRB RWA."""),
            code("""trace_columns = [
                "exposure_id", "borrower_id", "product_type", "commitment_type", "performing_exposure_class", "classification_rule_id",
                "outstanding_balance", "accrued_interest", "undrawn_amount", "ccf", "converted_undrawn", "ead_pre_crm",
                "ltv", "sa_risk_weight", "sa_rule_id", "sa_rwa",
                "pd_transition_profile", "internal_grade", "pd_long_run", "pd_regulatory",
                "normal_lgd", "downturn_lgd", "lgd_regulatory", "irb_ccf", "ead_irb", "m_effective",
                "asset_correlation_r", "conditional_pd_999", "maturity_adjustment", "capital_k", "expected_loss_amount", "irb_rwa",
            ]
            amount_columns = ["outstanding_balance", "accrued_interest", "undrawn_amount", "converted_undrawn", "ead_pre_crm", "sa_rwa", "ead_irb", "expected_loss_amount", "irb_rwa"]
            trace_filter = loans["undrawn_amount"].gt(0) & loans["default_flag"].eq(0) & loans["capital_k"].gt(0)
            traced_loan = loans.loc[trace_filter, trace_columns].head(1).copy()
            traced_loan[amount_columns] /= CRORE
            traced_loan = traced_loan.rename(columns={column: f"{column} (INR crore)" for column in amount_columns})
            display(traced_loan.T.rename(columns={traced_loan.index[0]: "Value"}))"""),
            md("""## The selected loan in four monetary measures

            The bars reduce the long trace to four comparable amounts. EAD is the exposure base. SA RWA and IRB RWA are two different capital-weighted views of that base. Expected loss is shown separately because it is not RWA."""),
            code("""selected = loans.loc[trace_filter].iloc[0]
            trace_amounts = pd.Series({
                "SA EAD": selected["ead_pre_crm"] / CRORE,
                "SA RWA": selected["sa_rwa"] / CRORE,
                "IRB RWA": selected["irb_rwa"] / CRORE,
                "Expected loss": selected["expected_loss_amount"] / CRORE,
            })
            axis = trace_amounts.plot.bar(figsize=(9, 4.5), color=[COLORS[1], COLORS[2], COLORS[4], COLORS[5]], title=f"Loan {selected['exposure_id']}: exposure, RWA and expected loss")
            axis.set_ylabel("INR crore")
            axis.set_xlabel("")
            axis.tick_params(axis="x", rotation=0)
            for position, value in enumerate(trace_amounts):
                axis.text(position, value, f"{value:,.2f}", ha="center", va="bottom", fontsize=9)
            plt.tight_layout()
            plt.show()"""),
            md("""The comparison shows why the trace keeps all four measures. A large EAD does not mechanically produce the same SA and IRB RWA, because the approaches apply different risk logic. Expected loss remains a separate average-loss measure."""),
            md("""Every important output remains on the same loan row. A surprising RWA can therefore be followed back to a commitment type, rating grade, recovery assumption, maturity or regulatory rule rather than appearing only as a portfolio total."""),
            md("""## Final portfolio controls

            The controls compare direct loan-level sums with saved exposure-class summaries and confirm the formula identities used by both approaches."""),
            code("""sa_summary = pd.read_csv(ROOT / "outputs/tables/sa_summary.csv")
            irb_summary = pd.read_csv(ROOT / "outputs/tables/irb_summary.csv")

            controls = pd.DataFrame({
                "Control": [
                    "SA EAD formula", "SA loan sum to class summary",
                    "IRB RWA formula", "IRB loan sum to class summary",
                    "Downturn LGD not below normal LGD", "Maturity within one-to-five-year ordinary bounds",
                ],
                "Difference or failed rows": [
                    (loans["ead_pre_crm"] - loans["funded_exposure"] - loans["ccf"] * loans["undrawn_amount"]).abs().max() / CRORE,
                    (loans["sa_rwa"].sum() - sa_summary["sa_rwa"].sum()) / CRORE,
                    (loans["irb_rwa"] - 12.5 * loans["capital_k"] * loans["ead_irb"]).abs().max() / CRORE,
                    (loans["irb_rwa"].sum() - irb_summary["irb_rwa"].sum()) / CRORE,
                    int((loans["downturn_lgd"] < loans["normal_lgd"]).sum()),
                    int((~loans["m_effective"].between(1, 5)).sum()),
                ],
            })
            controls["Status"] = np.where(controls["Difference or failed rows"].abs() < 1e-8, "PASS", "FAIL")
            display(controls)
            assert controls["Status"].eq("PASS").all()"""),
            md("""All controls must pass before the portfolio totals are treated as internally complete. These checks validate arithmetic and aggregation; they do not replace supervisory approval or empirical model validation."""),
            md("""## Completed project boundary

            The engine now contains Basel exposure-class references, a necessary-variable synthetic portfolio, loan-level Standardised Approach CCF/EAD/risk weights/RWA, synthetic long-run PD transitions, recovery-based downturn LGD, IRB EAD and maturity, Basel correlations, conditional PD, capital K, loan-level IRB RWA, the output floor, stress testing, capital adequacy and reconciliation controls.

            It does not claim confidential bank data, a fitted production rating model, A-IRB supervisory approval or a jurisdiction-specific regulatory filing."""),
        ],
        "The calculation chain is complete and internally reconciled from individual synthetic loans to Standardised Approach Credit RWA, IRB Credit RWA and capital adequacy.",
    )))

    # Insert the estimation and non-credit risk explanations before their values are used.
    specs.append(("08_how_irb_parameters_are_estimated.ipynb", notebook(
        "08", "How IRB Risk Parameters Would Be Estimated",
        "The project uses synthetic PD, LGD and own CCF values so the complete capital calculation can be demonstrated. This notebook shows the data and estimation route a bank would need before those parameters could be treated as internal estimates.",
        "This step separates parameter estimation from parameter use. The following notebooks apply the synthetic values at loan level; they do not claim that a production model has been fitted.",
        [("Observation window", "the historical period used to estimate a parameter"), ("Reference date", "the date from which a one-year default outcome or pre-default drawdown is measured"), ("Margin of conservatism", "an adjustment for data or estimation uncertainty"), ("Downturn", "a period in which defaults or credit losses are materially above normal")],
        [
            md("""## What is synthetic and what a bank would calculate

            The values used in this project are visible assumptions. A bank would replace them with estimates built from governed historical data, documented definitions, independent validation and supervisory approval where required."""),
            code("""estimation_map = pd.DataFrame([
                ["Long-run PD", "Synthetic transition-matrix default column", "Borrowers in each grade at annual reference dates; defaults during the next 12 months; migrations; overrides; cured defaults", "Calculate annual one-year default rates by grade or pool, cover representative good and bad years, then form a long-run average and add conservatism"],
                ["Downturn LGD", "Synthetic recoveries, costs and recovery times", "Defaulted facilities; EAD at default; dated cash recoveries; collateral proceeds; direct and indirect workout costs", "Calculate discounted economic loss for each default, estimate a long-run default-weighted LGD, then reflect periods of high loss severity"],
                ["IRB CCF / EAD", "Synthetic own CCF by facility", "Drawn and undrawn amounts at fixed pre-default dates; limits; cancellations; drawings at default", "Calculate realised conversion of unused limits, estimate long-run default-weighted EAD or CCF and reflect downturn dependence where material"],
                ["Effective maturity", "Contractual maturity with represented Basel bounds", "Cash-flow schedule, repricing and contractual maturity", "Calculate the applicable effective maturity under the relevant rule, including permitted floors, caps and exemptions"],
            ], columns=["Parameter", "Value used here", "Data a bank needs", "Ideal estimation route"])
            display(estimation_map)"""),
            md("""The first row is primarily a borrower or retail-pool estimate. LGD and EAD are facility estimates because collateral, seniority and undrawn commitments can differ even for the same borrower."""),
            md("""## Small PD example

            Suppose a grade contains 10,000 borrowers at the start of each year. The observed one-year default rate is the number that defaults within the following year divided by the starting borrower count. The example averages across years only to show the arithmetic; a bank would also test representativeness, grade philosophy, overrides, missing years and uncertainty."""),
            code("""pd_history = pd.DataFrame({
                "Year": [2021, 2022, 2023, 2024, 2025],
                "Borrowers at start": [10000, 10400, 10800, 11100, 11400],
                "Defaults within one year": [70, 83, 162, 122, 91],
            })
            pd_history["Observed one-year default rate"] = pd_history["Defaults within one year"] / pd_history["Borrowers at start"]
            long_run_example = pd_history["Defaults within one year"].sum() / pd_history["Borrowers at start"].sum()
            display(pd_history.style.format({"Observed one-year default rate": "{:.2%}"}))
            print(f"Count-weighted long-run example: {long_run_example:.2%}")"""),
            md("""## Small LGD and CCF examples

            Economic LGD uses discounted recoveries and workout costs. Realised CCF measures how much of the unused commitment was drawn before default. These two examples show the core arithmetic, not a fitted model."""),
            code("""examples = pd.DataFrame({
                "Calculation": ["LGD", "Realised CCF"],
                "Inputs": ["EAD 1.00; discounted recoveries 0.58; workout costs 0.07", "Drawn at reference 0.40; drawn at default 0.70; undrawn at reference 0.60"],
                "Formula": ["(1.00 - 0.58 + 0.07) / 1.00", "(0.70 - 0.40) / 0.60"],
                "Result": [(1.00 - 0.58 + 0.07) / 1.00, (0.70 - 0.40) / 0.60],
            })
            display(examples.style.format({"Result": "{:.1%}"}))"""),
            md("""The project now moves from estimation design to the synthetic parameter values actually used in the calculation. Their source remains visible on each loan row."""),
        ],
        "The estimation route is documented separately from the synthetic values used to demonstrate the IRB calculation.",
    )))

    specs.append(("14_market_and_operational_rwa.ipynb", notebook(
        "14", "Market and Operational Risk-Weighted Assets",
        "Credit RWA is complete under both approaches. Before total RWA and the output floor are compared, the other two configured risk categories are shown separately.",
        "Capital ratios use total RWA, not credit RWA alone. Market and operational RWA therefore enter both the standardised aggregate base and the model aggregate total.",
        [("Market RWA", "RWA for trading-book and other market-risk positions"), ("Operational RWA", "RWA for losses from failed processes, people, systems or external events"), ("BIC", "Business Indicator Component in the operational-risk Standardised Approach"), ("ILM", "Internal Loss Multiplier based on operational-loss experience where applicable")],
        [
            md("""## Values used in this project

            The two amounts below are synthetic configured inputs. They are not calculated from a synthetic trading book, financial statements or operational-loss database in this project."""),
            code("""non_credit = pd.DataFrame({
                "Risk category": ["Market risk", "Operational risk"],
                "RWA (INR crore)": [
                    configs["capital_parameters"]["external_rwa"]["market_rwa"] / CRORE,
                    configs["capital_parameters"]["external_rwa"]["operational_rwa"] / CRORE,
                ],
                "Source": ["Synthetic configured input", "Synthetic configured input"],
            })
            non_credit.loc[len(non_credit)] = ["Total non-credit RWA", non_credit["RWA (INR crore)"].sum(), "Sum"]
            display(non_credit)"""),
            md("""INR 11,000 crore market RWA and INR 14,000 crore operational RWA produce INR 25,000 crore of non-credit RWA. These amounts remain unchanged across this project's credit stress scenarios."""),
            md("""## How a bank would calculate the two amounts

            Market RWA is normally 12.5 times the applicable market-risk capital requirement. Under the applicable standardised framework, that requirement combines prescribed components such as sensitivities-based charges, default risk and residual risk. Operational RWA is 12.5 times operational-risk capital; under the Basel Standardised Approach, operational-risk capital equals BIC multiplied by ILM."""),
            code("""real_bank_route = pd.DataFrame([
                ["Market RWA", "Trading positions, sensitivities, risk factors, issuer defaults and residual risks", "12.5 × applicable market-risk capital requirement"],
                ["Operational RWA", "Three-year Business Indicator components and, where applicable, ten-year operational-loss history", "12.5 × BIC × ILM"],
            ], columns=["Output", "Data a bank needs", "Core route"])
            display(real_bank_route)"""),
            md("""The formulas explain how the configured figures would be replaced. They are not used to manufacture false precision without the underlying trading, income, expense and loss data."""),
            code("""capital_charge_equivalent = non_credit.iloc[:2].copy()
            capital_charge_equivalent["Equivalent capital charge (INR crore)"] = capital_charge_equivalent["RWA (INR crore)"] / 12.5
            display(capital_charge_equivalent[["Risk category", "RWA (INR crore)", "Equivalent capital charge (INR crore)"]])"""),
            md("""The 12.5 conversion is the inverse of 8%. The displayed capital-charge equivalents explain the relationship only; they do not replace a full market-risk or operational-risk calculation."""),
        ],
        "The INR 25,000 crore non-credit RWA input is now visible before it is added to either credit approach.",
    )))

    specs.append(("16_stress_scenario_design.ipynb", notebook(
        "16", "Stress Scenario Design and Calibration",
        "The completed base capital calculation is the starting point. This notebook identifies every shock and separates synthetic project sensitivities from Basel requirements.",
        "Stress testing asks how losses, RWA and capital could change under severe but plausible conditions. Basel requires a meaningful and reasonably conservative test but does not prescribe the numerical multipliers used here.",
        [("Macroeconomic path", "a time path for variables such as GDP, unemployment, rates and property prices"), ("Satellite model", "a model linking macroeconomic variables to portfolio risk drivers"), ("Multiplier", "a proportional shock applied to a base value"), ("Add-on", "an absolute increase added to a base value")],
        [
            md("""## Synthetic sensitivities used here

            Every multiplier, add-on, collateral shock, utilisation shock and loss rate below is synthetic. None is a Basel-prescribed adverse or severe value."""),
            code("""scenario_assumptions = pd.DataFrame(configs["stress_scenarios"]["scenarios"]).T
            display(scenario_assumptions.style.format({
                "pd_multiplier": "{:.2f}x", "cyclical_sector_pd_multiplier": "{:.2f}x", "retail_pd_multiplier": "{:.2f}x",
                "lgd_addon": "{:.1%}", "collateral_shock": "{:.1%}", "undrawn_utilisation_addon": "{:.1%}", "loss_rate": "{:.1%}",
            }))"""),
            md("""The general PD multiplier applies first. Higher cyclical-sector or retail multipliers replace it for the named portfolios. LGD and utilisation changes are add-ons, while the collateral shock reduces property and collateral values."""),
            md("""## How a bank would calibrate the shocks

            A bank would begin with approved macroeconomic paths and estimate how those paths change default, recovery, utilisation, revenue, expenses and capital over the stress horizon. Historical data provide the first estimate; expert overlays are documented when the history does not contain a comparable event."""),
            code("""calibration = pd.DataFrame([
                ["PD", "GDP, unemployment, interest rates, sector output, borrower grade history", "Estimate grade or segment default models conditional on the scenario path"],
                ["LGD", "Defaulted-loan recoveries, collateral prices, recovery time and costs", "Link recoveries and collateral haircuts to downturn conditions"],
                ["EAD / utilisation", "Monthly limits, drawings, cancellations and defaults", "Estimate additional drawings before default by product and borrower condition"],
                ["Capital", "Credit losses, market losses, operational losses, income, expenses, taxes and distributions", "Project the capital numerator and RWA denominator across the horizon"],
            ], columns=["Risk driver", "Typical data", "Calibration route"])
            display(calibration)"""),
            md("""The project deliberately uses transparent sensitivities because the required historical macroeconomic and bank outcome data are not present. The next notebook applies these assumptions to individual loans and shows the before-and-after changes."""),
        ],
        "The scenario values are explicitly synthetic, while the data and modelling route needed for real calibration are stated beside them.",
    )))

    specs.append(("17_stress_loan_level_transmission.ipynb", notebook(
        "17", "Loan-Level Stress Transmission",
        "The scenario design is complete. This notebook shows how the shocks change PD, LGD, EAD and RWA on the same loans before results are aggregated.",
        "The capital impact can be understood only after the scenario has passed through loan-level risk drivers. This separates the cause of stress from the final ratio movement.",
        [("Transmission", "the path from a scenario shock to a loan calculation"), ("Base", "the unshocked calculation"), ("Adverse", "the moderate synthetic stress"), ("Severe", "the stronger synthetic stress")],
        [
            md("""## Load the three recalculated loan files

            The engine reruns classification, EAD, risk weights, PD, LGD and IRB capital after applying each scenario. The comparison therefore uses the same exposure IDs under three conditions."""),
            code("""scenario_loans = {
                name: pd.read_csv(ROOT / f"data/processed/scenario_{name}.csv.gz", low_memory=False)
                for name in ["base", "adverse", "severe"]
            }
            transmission_summary = []
            for name, frame in scenario_loans.items():
                transmission_summary.append({
                    "Scenario": name, "EAD (INR crore)": frame["ead_pre_crm"].sum() / CRORE,
                    "Expected loss (INR crore)": frame["expected_loss_amount"].sum() / CRORE,
                    "SA RWA (INR crore)": frame["sa_rwa"].sum() / CRORE,
                    "IRB RWA (INR crore)": frame["irb_rwa"].sum() / CRORE,
                })
            transmission_summary = pd.DataFrame(transmission_summary).set_index("Scenario").reindex(["base", "adverse", "severe"])
            display(transmission_summary)"""),
            md("""EAD can rise when unused commitments are drawn. Expected loss rises when PD, LGD or EAD increases. SA RWA changes mainly through EAD and mortgage LTV bands, while IRB RWA also responds to PD, LGD, correlation and maturity mechanics."""),
            code("""change_from_base = transmission_summary.div(transmission_summary.loc["base"]).sub(1).drop(index="base")
            change_from_base.columns = ["EAD", "Expected loss", "SA Credit RWA", "IRB Credit RWA"]
            change_from_base.T.plot.bar(figsize=(11, 5), color=[COLORS[3], COLORS[5]], title="Change from base after loan-level recalculation")
            plt.ylabel("Percentage change")
            plt.xlabel("")
            plt.gca().yaxis.set_major_formatter(lambda value, position: f"{value:.0%}")
            plt.xticks(rotation=20, ha="right")
            plt.tight_layout()
            plt.show()"""),
            md("""Percentage change keeps EAD, expected loss and the two RWA approaches readable on one scale. The chart shows sensitivity rather than absolute portfolio size."""),
            md("""## One revolving loan before and after stress

            A single common exposure makes the transmission concrete. Additional utilisation changes EAD; the PD and LGD shocks then change expected loss and IRB RWA."""),
            code("""candidate = scenario_loans["base"].loc[lambda frame: frame["undrawn_amount"].gt(0) & frame["default_flag"].eq(0), "exposure_id"].iloc[0]
            trace = []
            for name, frame in scenario_loans.items():
                row = frame.loc[frame["exposure_id"].eq(candidate)].iloc[0]
                trace.append([name, row["pd_regulatory"], row["lgd_regulatory"], row["ead_pre_crm"] / CRORE, row["expected_loss_amount"] / CRORE, row["sa_rwa"] / CRORE, row["irb_rwa"] / CRORE])
            trace = pd.DataFrame(trace, columns=["Scenario", "PD", "LGD", "EAD (INR crore)", "Expected loss (INR crore)", "SA RWA (INR crore)", "IRB RWA (INR crore)"])
            display(trace.style.format({"PD": "{:.2%}", "LGD": "{:.2%}"}))"""),
            md("""This trace shows why stress is not a single top-level percentage applied to total RWA. Each affected risk driver is recalculated before the bank-level capital ratios are produced."""),
        ],
        "The synthetic shocks have been translated into visible loan-level and portfolio changes before the capital ratios are assessed.",
    )))

    # Renumber the existing IRB, comparison, stress and control notebooks around the new steps.
    number_map = {"08": "09", "09": "10", "10": "11", "11": "12", "12": "13", "13": "15", "14": "18", "15": "19"}
    renamed_specs = []
    for filename, generated_notebook in specs:
        old_number = filename[:2]
        if old_number in number_map and filename not in {
            "08_how_irb_parameters_are_estimated.ipynb",
            "14_market_and_operational_rwa.ipynb",
        }:
            new_number = number_map[old_number]
            filename = new_number + filename[2:]
            generated_notebook.cells[0].source = generated_notebook.cells[0].source.replace(
                f"# {old_number} —", f"# {new_number} —", 1
            )
        renamed_specs.append((filename, generated_notebook))
    specs = renamed_specs

    synthetic_notes = {
        "02": "The loan records, balances, ratings, defaults, collateral values and recoveries are synthetic. A bank would obtain these fields from governed lending, limit, collateral, rating, default and recovery systems and reconcile them to finance records.",
        "09": "The transition probabilities are synthetic. A bank would estimate long-run one-year PD from multi-year borrower counts and defaults by grade or retail pool, covering representative good and bad years and adding conservatism for uncertainty.",
        "10": "Recovery rates, recovery times and workout costs are synthetic. A bank would estimate LGD from discounted recoveries and costs on defaulted facilities, form a long-run default-weighted average and reflect periods of high loss severity.",
        "11": "Own CCF values are synthetic. A bank would compare drawn amounts before default with EAD at default, estimate realised conversion by facility type and apply representative long-run and downturn treatment where material.",
        "15": "Market and operational RWA used in the floor are synthetic configured inputs. Their amounts and real calculation routes were shown in notebook 14 before they are added here.",
        "18": "The capital stack, stress multipliers, add-ons and loss rates are synthetic. The scenario values are not Basel-prescribed; notebook 16 explains how a bank would calibrate them and notebook 14 separates the non-credit RWA inputs.",
    }

    comparison_code = """approach_comparison = loans.groupby("performing_exposure_class").agg(
                sa_rwa=("sa_rwa", "sum"),
                irb_rwa=("irb_rwa", "sum"),
            ).sort_values("sa_rwa") / CRORE

            figure, axes = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [1.25, 1]})
            approach_comparison.plot.barh(ax=axes[0], color=[COLORS[1], COLORS[4]])
            axes[0].set_xscale("log")
            axes[0].set_xlabel("INR crore on logarithmic scale")
            axes[0].set_ylabel("")
            axes[0].set_title("Absolute Credit RWA: all classes remain visible")

            density = approach_comparison.div(
                loans.groupby("performing_exposure_class")[["ead_pre_crm"]].sum()["ead_pre_crm"] / CRORE,
                axis=0,
            ).rename(columns={"sa_rwa": "SA RWA / EAD", "irb_rwa": "IRB RWA / EAD"})
            readable_labels = approach_comparison.index.str.replace("_", " ").str.title()
            axes[0].set_yticklabels(readable_labels)
            approach_comparison.index = readable_labels
            density.index = readable_labels
            density.sort_values("SA RWA / EAD").plot.barh(ax=axes[1], color=[COLORS[1], COLORS[4]])
            axes[1].set_xlabel("RWA divided by EAD")
            axes[1].set_ylabel("")
            axes[1].set_title("Capital intensity without portfolio-size distortion")
            axes[1].xaxis.set_major_formatter(lambda value, position: f"{value:.0%}")
            plt.tight_layout()
            plt.show()"""

    calculation_map_code = """calculation_map = pd.DataFrame({
                "Stage": range(1, 21),
                "Question answered": [
                    "Which Basel exposure classes exist?", "What loans and variables exist?",
                    "Which Basel class contains each loan?", "What is each loan's SA EAD?",
                    "Which SA risk weight applies?", "What is total SA Credit RWA?",
                    "Which IRB treatment applies?", "How would a bank estimate IRB parameters?",
                    "What is long-run one-year PD?", "What is downturn LGD?",
                    "What are IRB EAD and maturity?", "What are correlation, conditional PD and K?",
                    "What is total IRB Credit RWA?", "What are market and operational RWA?",
                    "How do SA, IRB and the output floor compare?", "How are stress scenarios designed?",
                    "How do shocks change individual loans?", "How do capital ratios change?",
                    "Do loan and portfolio totals reconcile?", "What remains outside the project?",
                ],
                "Main output": [
                    "Exposure-class reference", "30,000 synthetic loan records", "Class per loan",
                    "CCF and SA EAD per loan", "Risk weight per loan", "Total SA Credit RWA",
                    "IRB source per loan", "Real-bank estimation map", "PD per loan", "LGD per loan",
                    "IRB EAD and maturity", "Correlation and K", "Total IRB Credit RWA",
                    "INR 25,000 crore non-credit RWA", "Final aggregate RWA", "Transparent scenario assumptions",
                    "Before-and-after loan calculations", "Stressed ratios and headroom", "PASS controls",
                    "Clear project boundary",
                ],
            })
            display(calculation_map)"""

    for filename, generated_notebook in specs:
        number = filename[:2]
        if filename.startswith("00_complete_calculation_map"):
            for cell in generated_notebook.cells:
                if cell.cell_type == "code" and "calculation_map = pd.DataFrame" in cell.source:
                    cell.source = cleandoc(calculation_map_code)
        if filename.startswith("08_how_irb_parameters"):
            generated_notebook.cells[0].source = generated_notebook.cells[0].source.replace(
                "## Building the probability of default", "## From synthetic assumptions to real estimates"
            ).replace(
                "### How to read the transition tables", "### Estimation language used below"
            )
        if filename.startswith("14_market_and_operational"):
            generated_notebook.cells[0].source = generated_notebook.cells[0].source.replace(
                "## What changes when the portfolio is stressed", "## Completing the total RWA building blocks"
            ).replace(
                "### How to read the stress results", "### Non-credit risk terms used below"
            )
        if number in synthetic_notes:
            generated_notebook.cells.insert(2, md("> " + synthetic_notes[number]))
        if filename.startswith("15_sa_irb_comparison"):
            for cell in generated_notebook.cells:
                if cell.cell_type == "code" and "approach_comparison.plot.barh" in cell.source:
                    cell.source = cleandoc(comparison_code)
            generated_notebook.cells[0].source = generated_notebook.cells[0].source.replace(
                "Both credit approaches are now complete. This notebook compares them and applies the output floor after adding market and operational RWA.",
                "Both credit approaches and the non-credit RWA inputs are now complete. This notebook compares SA and IRB, then applies the aggregate output floor."
            )
        if filename.startswith("18_stress_testing"):
            generated_notebook.cells[0].source = generated_notebook.cells[0].source.replace(
                "# 18 — Stress Testing and Capital Adequacy", "# 18 — Stress Capital Impact and Adequacy"
            )

    specs.sort(key=lambda item: item[0])

    for filename, generated_notebook in specs:
        nbf.write(generated_notebook, NOTEBOOK_DIR / filename)

    print(f"Built {len(specs)} notebooks in {NOTEBOOK_DIR}")


if __name__ == "__main__":
    build()
