#!/usr/bin/env python3
"""Run compact end-to-end reconciliation checks."""

from __future__ import annotations

from basel_credit_risk import run_pipeline


def main() -> None:
    result = run_pipeline(portfolio_size=2_000, seed=42, write_outputs=False)
    current = result.exposures
    assert current["exposure_id"].is_unique
    assert abs(current["sa_rwa"].sum() - result.tables["sa_summary"]["sa_rwa"].sum()) < 1.0
    bridge = result.tables["rwa_bridge"]
    prior = float(bridge.loc[bridge["driver"].eq("Prior RWA"), "amount"].iloc[0])
    current_total = float(bridge.loc[bridge["driver"].eq("Current RWA"), "amount"].iloc[0])
    changes = bridge.loc[bridge["kind"].eq("change"), "amount"].sum()
    assert abs(prior + changes - current_total) < 1.0
    print("Project validation passed.")


if __name__ == "__main__":
    main()
