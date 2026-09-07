#!/usr/bin/env python3
"""Run the full Basel Credit Capital Engine."""

from __future__ import annotations

import argparse
from pathlib import Path

from basel_credit_risk import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio-size", type=int, default=None, help="Override configured exposure count.")
    parser.add_argument("--seed", type=int, default=None, help="Override configured random seed.")
    parser.add_argument("--no-write", action="store_true", help="Calculate without writing output files.")
    args = parser.parse_args()
    result = run_pipeline(portfolio_size=args.portfolio_size, seed=args.seed, write_outputs=not args.no_write, project_root=Path(__file__).resolve().parents[1])
    summary = result.tables["scenario_summary"]
    display_summary = summary[["scenario", "ead", "final_total_rwa"]].copy()
    display_summary[["ead", "final_total_rwa"]] /= 10_000_000
    display_summary = display_summary.rename(
        columns={"ead": "ead_inr_crore", "final_total_rwa": "final_total_rwa_inr_crore"}
    )
    print("Basel Credit Capital Engine completed successfully.")
    print(display_summary.to_string(index=False, float_format=lambda value: f"{value:,.1f}"))


if __name__ == "__main__":
    main()
