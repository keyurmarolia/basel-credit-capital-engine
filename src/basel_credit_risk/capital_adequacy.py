"""Bank-level capital stack, ratios and headroom."""

from __future__ import annotations

import pandas as pd


def calculate_capital_adequacy(
    scenario: str,
    credit_rwa: float,
    market_rwa: float,
    operational_rwa: float,
    stress_loss: float,
    capital_config: dict,
) -> pd.DataFrame:
    """Calculate numerator-only, denominator-only and combined capital effects."""
    cap = capital_config["capital"]
    req = capital_config["requirements"]
    base_cet1 = cap["common_equity"] + cap["retained_earnings"] - cap["cet1_deductions"]
    stressed_cet1 = max(base_cet1 - stress_loss, 0.0)
    tier1 = stressed_cet1 + cap["at1"]
    total_capital = tier1 + cap["tier2"]
    total_rwa = credit_rwa + market_rwa + operational_rwa
    combined_buffer = req["capital_conservation_buffer"] + req["other_buffers"]
    values = [
        ("CET1", stressed_cet1, stressed_cet1 / total_rwa, req["cet1_minimum"] + combined_buffer),
        ("Tier 1", tier1, tier1 / total_rwa, req["tier1_minimum"] + combined_buffer),
        (
            "Total Capital",
            total_capital,
            total_capital / total_rwa,
            req["total_minimum"] + combined_buffer,
        ),
    ]
    return pd.DataFrame(
        [
            {
                "scenario": scenario,
                "capital_measure": name,
                "capital_amount": amount,
                "total_rwa": total_rwa,
                "ratio": ratio,
                "requirement_plus_buffer": requirement,
                "headroom": ratio - requirement,
                "stress_loss": stress_loss,
            }
            for name, amount, ratio, requirement in values
        ]
    )
