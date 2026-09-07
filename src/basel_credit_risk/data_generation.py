"""Reproducible synthetic bank portfolio generation.

The generator creates economically connected fields. It is intentionally
synthetic: no source record represents a real customer or facility.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

SEGMENTS = {
    "mortgage": 0.30,
    "large_corporate": 0.10,
    "sme": 0.10,
    "personal_loan": 0.20,
    "credit_card": 0.20,
    "bank": 0.035,
    "sovereign": 0.025,
    "other": 0.02,
}

GRADE_PD = {
    "AAA": 0.0003,
    "AA": 0.0006,
    "A": 0.0015,
    "BBB": 0.0040,
    "BB": 0.0150,
    "B": 0.0500,
    "CCC": 0.1800,
}


@dataclass(frozen=True)
class SyntheticPortfolio:
    current: pd.DataFrame
    prior: pd.DataFrame


def _allocate_counts(size: int) -> dict[str, int]:
    counts = {key: int(size * share) for key, share in SEGMENTS.items()}
    counts["mortgage"] += size - sum(counts.values())
    return counts


def _choose_grades(rng: np.random.Generator, segment: str, size: int) -> np.ndarray:
    grades = np.array(list(GRADE_PD))
    weights = {
        "sovereign": [0.30, 0.35, 0.20, 0.10, 0.04, 0.01, 0.00],
        "bank": [0.10, 0.30, 0.30, 0.20, 0.07, 0.025, 0.005],
        "large_corporate": [0.03, 0.12, 0.25, 0.30, 0.18, 0.09, 0.03],
        "sme": [0.00, 0.03, 0.12, 0.30, 0.30, 0.18, 0.07],
        "mortgage": [0.00, 0.05, 0.25, 0.40, 0.20, 0.08, 0.02],
        "personal_loan": [0.00, 0.02, 0.13, 0.35, 0.28, 0.16, 0.06],
        "credit_card": [0.00, 0.02, 0.12, 0.32, 0.30, 0.18, 0.06],
        "other": [0.00, 0.05, 0.20, 0.35, 0.23, 0.12, 0.05],
    }[segment]
    return rng.choice(grades, size=size, p=weights)


def _segment_frame(rng: np.random.Generator, segment: str, size: int, start: int) -> pd.DataFrame:
    product_map = {
        "mortgage": "mortgage",
        "large_corporate": "corporate_revolver",
        "sme": "sme_revolver",
        "personal_loan": "personal_loan",
        "credit_card": "credit_card",
        "bank": "bank_loan",
        "sovereign": "sovereign_bond",
        "other": "other",
    }
    scale_map = {
        "mortgage": 3_500_000,
        "large_corporate": 900_000_000,
        "sme": 45_000_000,
        "personal_loan": 650_000,
        "credit_card": 90_000,
        "bank": 500_000_000,
        "sovereign": 1_500_000_000,
        "other": 12_000_000,
    }
    grades = _choose_grades(rng, segment, size)
    base_pd = np.array([GRADE_PD[g] for g in grades])
    pd_1y = np.clip(base_pd * rng.lognormal(0, 0.18, size), 0.00005, 0.45)
    outstanding = rng.lognormal(np.log(scale_map[segment]), 0.65, size)
    revolving = segment in {"credit_card", "large_corporate", "sme", "bank", "other"}
    utilisation = rng.uniform(0.30, 0.90, size) if revolving else np.ones(size)
    credit_limit = outstanding / utilisation if revolving else outstanding
    undrawn = np.maximum(credit_limit - outstanding, 0)

    if segment == "credit_card":
        commitment_type = np.where(
            rng.random(size) < 0.70,
            "unconditionally_cancellable",
            "other_commitment",
        )
    elif revolving:
        commitment_type = np.full(size, "other_commitment")
    else:
        commitment_type = np.full(size, "no_commitment")

    if segment == "mortgage":
        collateral_type = np.full(size, "residential_property")
        ltv = np.clip(rng.normal(0.67, 0.17, size), 0.20, 1.35)
        collateral_value = outstanding / ltv
        property_value_at_origination = collateral_value * rng.uniform(0.92, 1.08, size)
        property_value_current = collateral_value
        property_cashflow_dependent = rng.random(size) < 0.12
        regulatory_real_estate_eligible = np.ones(size, dtype=bool)
    elif segment in {"large_corporate", "sme"}:
        secured = rng.random(size) < (0.55 if segment == "sme" else 0.40)
        collateral_type = np.where(secured, "commercial_property", "none")
        coverage = rng.uniform(0.40, 1.30, size) * secured
        collateral_value = outstanding * coverage
        property_value_at_origination = collateral_value * rng.uniform(0.90, 1.10, size)
        property_value_current = collateral_value
        property_cashflow_dependent = np.zeros(size, dtype=bool)
        regulatory_real_estate_eligible = np.zeros(size, dtype=bool)
    elif segment == "sovereign":
        collateral_type = np.full(size, "none")
        collateral_value = np.zeros(size)
        property_value_at_origination = np.zeros(size)
        property_value_current = np.zeros(size)
        property_cashflow_dependent = np.zeros(size, dtype=bool)
        regulatory_real_estate_eligible = np.zeros(size, dtype=bool)
    elif segment == "bank":
        cash_secured = rng.random(size) < 0.18
        collateral_type = np.where(cash_secured, "cash", "none")
        collateral_value = outstanding * rng.uniform(0.40, 1.00, size) * cash_secured
        property_value_at_origination = np.zeros(size)
        property_value_current = np.zeros(size)
        property_cashflow_dependent = np.zeros(size, dtype=bool)
        regulatory_real_estate_eligible = np.zeros(size, dtype=bool)
    else:
        collateral_type = np.full(size, "none")
        collateral_value = np.zeros(size)
        property_value_at_origination = np.zeros(size)
        property_value_current = np.zeros(size)
        property_cashflow_dependent = np.zeros(size, dtype=bool)
        regulatory_real_estate_eligible = np.zeros(size, dtype=bool)

    default_flag = rng.random(size) < np.minimum(pd_1y * 0.75, 0.20)
    dpd = np.where(
        default_flag, rng.integers(91, 361, size), rng.choice([0, 0, 0, 5, 15, 30, 60], size=size)
    )
    sectors = np.array(
        [
            "Construction",
            "Real Estate",
            "Metals",
            "Textiles",
            "Auto Components",
            "IT Services",
            "Healthcare",
            "Consumer",
            "Financial Services",
            "Government",
        ]
    )
    if segment == "sovereign":
        sector = np.full(size, "Government")
    elif segment in {"mortgage", "personal_loan", "credit_card"}:
        sector = np.full(size, "Households")
    elif segment == "bank":
        sector = np.full(size, "Financial Services")
    else:
        sector = rng.choice(sectors[:-1], size=size)

    repeat = (
        1
        if segment in {"mortgage", "personal_loan", "credit_card"}
        else (3 if segment in {"large_corporate", "bank"} else 2)
    )
    borrower_numbers = start + np.arange(size) // repeat
    guarantee = np.where(rng.random(size) < 0.08, outstanding * rng.uniform(0.2, 0.8, size), 0.0)
    is_individual = segment in {"mortgage", "personal_loan", "credit_card"}
    is_sme = segment == "sme"
    annual_revenue = np.where(
        segment == "large_corporate",
        rng.lognormal(np.log(35_000_000_000), 0.80, size),
        np.where(segment == "sme", rng.lognormal(np.log(1_200_000_000), 0.70, size), 0.0),
    )
    group_total_assets = np.where(
        segment == "large_corporate",
        annual_revenue * rng.uniform(0.7, 1.8, size),
        np.where(segment == "sme", annual_revenue * rng.uniform(0.6, 1.5, size), 0.0),
    )
    transactor = np.where(segment == "credit_card", rng.random(size) < 0.22, False)
    managed_as_retail = np.full(size, segment in {"mortgage", "personal_loan", "credit_card"})
    origination_months_ago = rng.integers(6, 121, size)
    origination_date = pd.Timestamp("2026-06-30") - pd.to_timedelta(
        origination_months_ago * 30, unit="D"
    )
    contractual_maturity = np.clip(rng.gamma(2.0, 1.3, size), 0.25, 12.0)

    return pd.DataFrame(
        {
            "exposure_id": [f"EXP-{start + i:07d}" for i in range(size)],
            "borrower_id": [f"BOR-{x:07d}" for x in borrower_numbers],
            "connected_group_id": [f"GRP-{x:07d}" for x in borrower_numbers],
            "reporting_date": pd.Timestamp("2026-06-30"),
            "segment": segment,
            "product_type": product_map[segment],
            "borrower_type": np.where(is_individual, "individual", segment),
            "is_individual": is_individual,
            "is_sme": is_sme,
            "managed_as_retail": managed_as_retail,
            "retail_transactor": transactor,
            "annual_revenue": annual_revenue,
            "group_total_assets": group_total_assets,
            "exposure_class_raw": segment,
            "sector": sector,
            "geography": rng.choice(
                ["North", "West", "South", "East", "Central"],
                size=size,
                p=[0.20, 0.30, 0.25, 0.15, 0.10],
            ),
            "currency": "INR",
            "external_rating": grades,
            "internal_grade": grades,
            "pd_1y": pd_1y,
            "origination_date": origination_date,
            "contractual_maturity_years": contractual_maturity,
            "outstanding_balance": outstanding,
            "credit_limit": credit_limit,
            "undrawn_amount": undrawn,
            "revolving_flag": revolving,
            "commitment_type": commitment_type,
            "unconditionally_cancellable_flag": commitment_type == "unconditionally_cancellable",
            "accrued_interest": outstanding * rng.uniform(0.0, 0.012, size),
            "collateral_type": collateral_type,
            "collateral_value": collateral_value,
            "property_value_at_origination": property_value_at_origination,
            "property_value_current": property_value_current,
            "property_cashflow_dependent": property_cashflow_dependent,
            "regulatory_real_estate_eligible": regulatory_real_estate_eligible,
            "senior_lien_amount": np.zeros(size),
            "guarantee_value": guarantee,
            "guarantor_type": np.where(guarantee > 0, "eligible_bank", "none"),
            "guarantor_rating": np.where(guarantee > 0, "AA", "UNRATED"),
            "dpd": dpd,
            "default_flag": default_flag.astype(int),
        }
    )


def _consistent_borrowers(frame: pd.DataFrame) -> pd.DataFrame:
    """One borrower has one sector, region, grade, revenue and default status."""
    out = frame.copy()
    columns = [
        "sector",
        "geography",
        "internal_grade",
        "external_rating",
        "pd_1y",
        "annual_revenue",
        "group_total_assets",
        "default_flag",
        "dpd",
    ]
    out[columns] = out.groupby("borrower_id")[columns].transform("first")
    return out


def generate_portfolio(
    size: int = 30_000,
    seed: int = 42,
    reporting_date: str = "2026-06-30",
    prior_reporting_date: str = "2025-12-31",
) -> SyntheticPortfolio:
    """Generate consistent current/prior snapshots; all inputs are synthetic."""
    if size < 100:
        raise ValueError("Portfolio size must be at least 100 exposures.")
    rng = np.random.default_rng(seed)
    frames: list[pd.DataFrame] = []
    start = 1
    for segment, count in _allocate_counts(size).items():
        frames.append(_segment_frame(rng, segment, count, start))
        start += count
    current = _consistent_borrowers(pd.concat(frames, ignore_index=True))
    date_shift = pd.Timestamp(reporting_date) - pd.Timestamp("2026-06-30")
    current["origination_date"] += date_shift
    current["reporting_date"] = pd.Timestamp(reporting_date)

    prior = current.copy()
    prior["reporting_date"] = pd.Timestamp(prior_reporting_date)
    prior["outstanding_balance"] *= rng.uniform(0.88, 1.12, len(prior))
    prior["credit_limit"] = np.maximum(
        prior["credit_limit"] * rng.uniform(0.95, 1.05, len(prior)), prior["outstanding_balance"]
    )
    prior["undrawn_amount"] = np.maximum(prior["credit_limit"] - prior["outstanding_balance"], 0)
    non_revolving = ~prior["revolving_flag"]
    prior.loc[non_revolving, "credit_limit"] = prior.loc[non_revolving, "outstanding_balance"]
    prior.loc[non_revolving, "undrawn_amount"] = 0.0
    prior["accrued_interest"] *= prior["outstanding_balance"] / current["outstanding_balance"]
    elapsed_years = (
        pd.Timestamp(reporting_date) - pd.Timestamp(prior_reporting_date)
    ).days / 365.25
    prior["contractual_maturity_years"] += elapsed_years
    prior["collateral_value"] *= 1.05
    prior["property_value_current"] *= 1.05
    borrowers = prior["borrower_id"].drop_duplicates()
    migrations = dict(
        zip(borrowers, rng.choice([-1, 0, 1], len(borrowers), p=[0.18, 0.77, 0.05]), strict=True)
    )
    grades = list(GRADE_PD)
    grade_number = prior["internal_grade"].map({grade: i for i, grade in enumerate(grades)})
    prior["internal_grade"] = (
        (grade_number + prior["borrower_id"].map(migrations))
        .clip(0, 6)
        .map(dict(enumerate(grades)))
    )
    prior["external_rating"] = prior["internal_grade"]
    prior["pd_1y"] = prior["internal_grade"].map(GRADE_PD)

    # New facilities must not appear before their origination date.
    new_mask = (rng.random(len(current)) < 0.025) | current["origination_date"].gt(
        pd.Timestamp(prior_reporting_date)
    )
    prior = prior.loc[~new_mask].copy()
    runoff_count = max(1, int(size * 0.02))
    runoff = _consistent_borrowers(_segment_frame(rng, "sme", runoff_count, size + 100_000))
    runoff["reporting_date"] = pd.Timestamp(prior_reporting_date)
    runoff["origination_date"] = pd.Series(
        pd.Timestamp(date.fromisoformat(str(prior_reporting_date)) - timedelta(days=365)),
        index=runoff.index,
        dtype="datetime64[ns]",
    )
    prior = pd.concat([prior, runoff], ignore_index=True)

    return SyntheticPortfolio(current=current, prior=prior)
