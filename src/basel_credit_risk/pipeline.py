"""End-to-end orchestration for reproducible project outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .capital_adequacy import calculate_capital_adequacy
from .concentration import borrower_concentration, concentration_by, concentration_summary
from .config import PROJECT_ROOT, load_all_config
from .crm import apply_crm
from .data_generation import SyntheticPortfolio, generate_portfolio
from .data_validation import validate_exposures, validation_summary
from .ead_ccf import calculate_ead
from .exposure_classification import classify_exposures
from .irb_parameters import prepare_irb_parameters
from .irb_rwa import calculate_irb_rwa
from .output_floor import calculate_output_floor
from .reporting import portfolio_profile, write_tables
from .rwa_attribution import attribute_rwa
from .sa_rwa import calculate_sa_rwa
from .stress_testing import apply_stress, stress_contribution


@dataclass
class PipelineResult:
    exposures: pd.DataFrame
    prior_exposures: pd.DataFrame
    scenarios: dict[str, pd.DataFrame]
    tables: dict[str, pd.DataFrame]
    configs: dict


def calculate_exposures(raw: pd.DataFrame, configs: dict) -> pd.DataFrame:
    """Run one snapshot through the full exposure-level calculation chain."""
    exceptions = validate_exposures(raw)
    if not exceptions.empty:
        raise ValueError(f"Exposure validation failed: {exceptions['rule'].unique().tolist()}")
    out = classify_exposures(raw, configs["classification_parameters"], configs["ccf_parameters"])
    out = calculate_ead(out, configs["ccf_parameters"])
    out = apply_crm(out, configs["crm_parameters"])
    out = calculate_sa_rwa(out, configs["sa_risk_weights"], configs["crm_parameters"])
    out = prepare_irb_parameters(
        out,
        configs["irb_parameters"],
        configs["pd_transition_assumptions"],
    )
    out = calculate_irb_rwa(out, configs["irb_parameters"])
    return out


def run_pipeline(
    portfolio_size: int | None = None,
    seed: int | None = None,
    write_outputs: bool = True,
    project_root: Path | None = None,
) -> PipelineResult:
    """Generate data, calculate risk/capital, reconcile and optionally write outputs."""
    root = project_root or PROJECT_ROOT
    configs = load_all_config(root / "config")
    scope = configs["regulatory_scope"]
    synthetic: SyntheticPortfolio = generate_portfolio(
        size=int(scope["portfolio_size"]) if portfolio_size is None else portfolio_size,
        seed=seed if seed is not None else int(scope["random_seed"]),
        reporting_date=str(scope["reporting_date"]),
        prior_reporting_date=str(scope["prior_reporting_date"]),
    )
    current_exceptions = validate_exposures(synthetic.current)
    prior_exceptions = validate_exposures(synthetic.prior)
    if not current_exceptions.empty or not prior_exceptions.empty:
        raise ValueError("Synthetic portfolio failed validation; inspect exception output.")
    current = calculate_exposures(synthetic.current, configs)
    prior = calculate_exposures(synthetic.prior, configs)

    cap_config = configs["capital_parameters"]
    market_rwa = float(cap_config["external_rwa"]["market_rwa"])
    operational_rwa = float(cap_config["external_rwa"]["operational_rwa"])
    floor_rate = float(scope["output_floor_rate"])
    scenario_frames: dict[str, pd.DataFrame] = {}
    floor_tables: list[pd.DataFrame] = []
    capital_tables: list[pd.DataFrame] = []
    summary_rows: list[dict[str, float | str | bool]] = []
    for scenario_name, scenario_cfg in configs["stress_scenarios"]["scenarios"].items():
        stressed_raw = apply_stress(synthetic.current, scenario_name, configs["stress_scenarios"])
        frame = calculate_exposures(stressed_raw, configs)
        scenario_frames[scenario_name] = frame
        floor = calculate_output_floor(
            frame["sa_rwa"].sum(), frame["irb_rwa"].sum(), market_rwa, operational_rwa, floor_rate
        )
        floor.insert(0, "scenario", scenario_name)
        floor_tables.append(floor)
        final_total = float(floor.loc[floor["metric"].eq("Final aggregate RWA"), "value"].iloc[0])
        final_credit = final_total - market_rwa - operational_rwa
        stress_loss = float(scenario_cfg["loss_rate"]) * frame["ead_pre_crm"].sum()
        capital_tables.append(
            calculate_capital_adequacy(
                scenario_name, final_credit, market_rwa, operational_rwa, stress_loss, cap_config
            )
        )
        summary_rows.append(
            {
                "scenario": scenario_name,
                "ead": frame["ead_pre_crm"].sum(),
                "sa_credit_rwa": frame["sa_rwa"].sum(),
                "irb_credit_rwa": frame["irb_rwa"].sum(),
                "expected_loss": frame["expected_loss_amount"].sum(),
                "final_total_rwa": final_total,
                "floor_binding": bool(floor["floor_binding"].iloc[0]),
                "stress_loss": stress_loss,
            }
        )

    rating = concentration_by(current, "external_rating")
    order = {x: i for i, x in enumerate(["AAA", "AA", "A", "BBB", "BB", "B", "CCC"])}
    rating = rating.sort_values("external_rating", key=lambda s: s.map(order))
    sector = concentration_by(current, "sector")
    product = concentration_by(current, "product_type")
    tables = {
        "portfolio_profile": portfolio_profile(current),
        "validation_summary": validation_summary(synthetic.current, current_exceptions),
        "sa_summary": current.groupby("basel_exposure_class", as_index=False).agg(
            ead_pre_crm=("ead_pre_crm", "sum"),
            ead_post_crm=("sa_ead_post_crm", "sum"),
            sa_rwa=("sa_rwa", "sum"),
            average_risk_weight=("sa_risk_weight", "mean"),
        ),
        "irb_summary": irb_summary(current),
        "rating_summary": rating,
        "sector_concentration": sector,
        "product_concentration": product,
        "borrower_concentration": borrower_concentration(current).head(100),
        "concentration_summary": concentration_summary(current),
        "rwa_bridge": attribute_rwa(prior, current, configs["irb_parameters"]),
        "scenario_summary": pd.DataFrame(summary_rows),
        "stress_sector_contribution_adverse": stress_contribution(
            scenario_frames["base"], scenario_frames["adverse"], "sector"
        ),
        "stress_sector_contribution_severe": stress_contribution(
            scenario_frames["base"], scenario_frames["severe"], "sector"
        ),
        "output_floor": pd.concat(floor_tables, ignore_index=True),
        "capital_adequacy": pd.concat(capital_tables, ignore_index=True),
        "exposure_trace_sample": representative_sample(current, 25),
    }

    if write_outputs:
        data_generated = root / "data" / "generated"
        data_generated.mkdir(parents=True, exist_ok=True)
        synthetic.current.to_csv(
            data_generated / "current_portfolio.csv.gz", index=False, compression="gzip"
        )
        synthetic.prior.to_csv(
            data_generated / "prior_portfolio.csv.gz", index=False, compression="gzip"
        )
        processed = root / "data" / "processed"
        processed.mkdir(parents=True, exist_ok=True)
        current.to_csv(processed / "current_calculated.csv.gz", index=False, compression="gzip")
        prior.to_csv(processed / "prior_calculated.csv.gz", index=False, compression="gzip")
        for scenario_name, frame in scenario_frames.items():
            frame.to_csv(
                processed / f"scenario_{scenario_name}.csv.gz", index=False, compression="gzip"
            )
        sample = root / "data" / "sample"
        sample.mkdir(parents=True, exist_ok=True)
        representative_sample(synthetic.current, min(500, len(current))).to_csv(
            sample / "synthetic_exposure_sample.csv", index=False
        )
        write_tables(tables, root / "outputs" / "tables")
    return PipelineResult(current, prior, scenario_frames, tables, configs)


def representative_sample(frame: pd.DataFrame, size: int) -> pd.DataFrame:
    """Include every product, then fill with a deterministic random sample."""
    first = frame.groupby("segment", sort=True).head(1)
    remaining = frame.drop(first.index).sample(
        max(0, min(size, len(frame)) - len(first)), random_state=42
    )
    return pd.concat([first, remaining]).sort_values(["segment", "exposure_id"])


def irb_summary(frame: pd.DataFrame) -> pd.DataFrame:
    values = frame.assign(
        pd_ead=frame["pd_regulatory"] * frame["ead_irb"],
        lgd_ead=frame["lgd_regulatory"] * frame["ead_irb"],
    )
    summary = values.groupby("basel_exposure_class", as_index=False).agg(
        ead=("ead_irb", "sum"),
        pd_ead=("pd_ead", "sum"),
        lgd_ead=("lgd_ead", "sum"),
        expected_loss=("expected_loss_amount", "sum"),
        irb_rwa=("irb_rwa", "sum"),
    )
    summary["weighted_pd"] = summary.pop("pd_ead") / summary["ead"]
    summary["weighted_lgd"] = summary.pop("lgd_ead") / summary["ead"]
    return summary[
        ["basel_exposure_class", "ead", "weighted_pd", "weighted_lgd", "expected_loss", "irb_rwa"]
    ]
