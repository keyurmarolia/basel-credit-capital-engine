"""Reporting tables and run metadata."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def portfolio_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Core portfolio metrics for the executive layer."""
    return pd.DataFrame(
        {
            "metric": [
                "Exposure count",
                "Borrower count",
                "Gross exposure",
                "Total EAD",
                "SA Credit RWA",
                "IRB Credit RWA",
                "IRB expected loss",
                "Defaulted EAD share",
            ],
            "value": [
                len(df),
                df["borrower_id"].nunique(),
                df["outstanding_balance"].sum(),
                df["ead_pre_crm"].sum(),
                df["sa_rwa"].sum(),
                df["irb_rwa"].sum(),
                df["expected_loss_amount"].sum(),
                df.loc[df["default_flag"].eq(1), "ead_pre_crm"].sum() / df["ead_pre_crm"].sum(),
            ],
        }
    )


def write_tables(tables: dict[str, pd.DataFrame], output_dir: Path) -> None:
    """Write auditable CSV outputs and a compact manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict[str, int]] = {}
    for name, table in tables.items():
        table.to_csv(output_dir / f"{name}.csv", index=False)
        manifest[name] = {"rows": len(table), "columns": len(table.columns)}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
