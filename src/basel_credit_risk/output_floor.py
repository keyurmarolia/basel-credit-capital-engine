"""Aggregate Basel output-floor comparison."""

from __future__ import annotations

import pandas as pd


def calculate_output_floor(
    sa_credit_rwa: float,
    irb_credit_rwa: float,
    market_rwa: float,
    operational_rwa: float,
    floor_rate: float,
) -> pd.DataFrame:
    """Apply the floor to aggregate standardised RWA, not credit RWA alone."""
    standardised_total = sa_credit_rwa + market_rwa + operational_rwa
    model_total = irb_credit_rwa + market_rwa + operational_rwa
    floor_amount = floor_rate * standardised_total
    final_total = max(model_total, floor_amount)
    return pd.DataFrame(
        {
            "metric": [
                "SA Credit RWA",
                "IRB Credit RWA",
                "Standardised aggregate RWA base",
                "Pre-floor model aggregate RWA",
                "Output-floor rate",
                "Output-floor amount",
                "Final aggregate RWA",
                "Floor uplift",
            ],
            "value": [sa_credit_rwa, irb_credit_rwa, standardised_total, model_total, floor_rate, floor_amount, final_total, final_total - model_total],
        }
    ).assign(floor_binding=final_total > model_total)

