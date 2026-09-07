"""Small shared helpers for readable notebook tables and source data."""

from pathlib import Path

import pandas as pd
from IPython.display import display as notebook_display
from pandas.io.formats.style import Styler

from .pipeline import run_pipeline


def ensure_outputs(root: Path) -> None:
    """Create missing calculated files on a fresh checkout."""
    required = [
        "data/generated/current_portfolio.csv.gz",
        "data/processed/current_calculated.csv.gz",
        "data/processed/scenario_base.csv.gz",
        "data/processed/scenario_adverse.csv.gz",
        "data/processed/scenario_severe.csv.gz",
        "outputs/tables/sa_summary.csv",
        "outputs/tables/irb_summary.csv",
        "outputs/tables/output_floor.csv",
        "outputs/tables/scenario_summary.csv",
        "outputs/tables/capital_adequacy.csv",
    ]
    if any(not (root / name).exists() for name in required):
        run_pipeline(project_root=root)


def display(*objects):
    """Wrap complete cell text; keep table values visible in saved outputs."""
    for value in objects:
        if isinstance(value, pd.DataFrame):
            value = value.style
        if isinstance(value, Styler):
            value = value.set_properties(
                **{
                    "white-space": "normal",
                    "overflow-wrap": "anywhere",
                    "vertical-align": "top",
                    "max-width": "380px",
                }
            ).set_table_styles(
                [
                    {
                        "selector": "th",
                        "props": [
                            ("white-space", "normal"),
                            ("overflow-wrap", "anywhere"),
                            ("max-width", "180px"),
                            ("text-align", "left"),
                        ],
                    }
                ],
                overwrite=False,
            )
        notebook_display(value)
