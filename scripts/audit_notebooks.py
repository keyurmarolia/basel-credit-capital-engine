#!/usr/bin/env python3
"""Check saved notebook execution and beginner-facing structure."""

from __future__ import annotations

import re
from pathlib import Path

import nbformat


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    notebooks = sorted((root / "notebooks").glob("*.ipynb"))
    expected = [
        "00_complete_calculation_map.ipynb",
        "01_basel_exposure_classes.ipynb",
        "02_synthetic_bank_loan_portfolio.ipynb",
        "03_sa_loan_classification.ipynb",
        "04_sa_ead_and_ccf.ipynb",
        "05_sa_risk_weights_and_mortgage_ltv.ipynb",
        "06_sa_loan_level_rwa_and_total.ipynb",
        "07_irb_scope_and_parameter_sources.ipynb",
        "08_how_irb_parameters_are_estimated.ipynb",
        "09_irb_long_run_pd_and_transitions.ipynb",
        "10_irb_downturn_lgd.ipynb",
        "11_irb_ead_and_maturity.ipynb",
        "12_irb_correlation_vasicek_and_k.ipynb",
        "13_irb_loan_level_rwa_and_total.ipynb",
        "14_market_and_operational_rwa.ipynb",
        "15_sa_irb_comparison_and_output_floor.ipynb",
        "16_stress_scenario_design.ipynb",
        "17_stress_loan_level_transmission.ipynb",
        "18_stress_testing_and_capital_adequacy.ipynb",
        "19_end_to_end_loan_trace_and_controls.ipynb",
    ]
    found = [path.name for path in notebooks]
    if found != expected:
        raise SystemExit(f"Notebook sequence differs. Expected {expected}; found {found}.")
    prohibited_phrases = [
        "Previous](",
        "Next](",
        "Run top to bottom",
        "Purpose:",
        "Inputs:",
        "## Key point",
    ]
    for path in notebooks:
        notebook = nbformat.read(path, as_version=4)
        code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
        errors = [
            output
            for cell in code_cells
            for output in cell.get("outputs", [])
            if output.output_type == "error"
        ]
        executed = [cell for cell in code_cells if cell.get("execution_count") is not None]
        if errors:
            raise SystemExit(f"{path.name} contains {len(errors)} saved execution errors.")
        for cell in code_cells:
            for output in cell.get("outputs", []):
                html = output.get("data", {}).get("text/html", "")
                if re.search(r">\s*(?:\.\.\.|…)\s*</t[dh]>", html):
                    raise SystemExit(f"{path.name} contains a truncated HTML table.")
        if len(executed) != len(code_cells):
            raise SystemExit(f"{path.name} contains unexecuted code cells.")
        if not any(cell.get("outputs") for cell in code_cells):
            raise SystemExit(f"{path.name} contains no saved outputs.")
        for position, cell in enumerate(notebook.cells):
            if cell.cell_type != "code":
                continue
            if position == 0 or notebook.cells[position - 1].cell_type != "markdown":
                raise SystemExit(f"{path.name} has a code cell without a preceding explanation.")
        markdown_text = "\n".join(
            cell.source for cell in notebook.cells if cell.cell_type == "markdown"
        )
        found_phrases = [phrase for phrase in prohibited_phrases if phrase in markdown_text]
        if found_phrases:
            raise SystemExit(f"{path.name} contains prohibited wording: {found_phrases}.")
        print(f"PASS {path.name}: {len(code_cells)} executed code cells")


if __name__ == "__main__":
    main()
