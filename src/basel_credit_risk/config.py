"""Configuration loading with explicit project-root resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_yaml(name: str, config_dir: Path | None = None) -> dict[str, Any]:
    """Load one named YAML configuration file."""
    path = (config_dir or PROJECT_ROOT / "config") / name
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_all_config(config_dir: Path | None = None) -> dict[str, Any]:
    """Load the calculation configuration used by an end-to-end run."""
    names = [
        "regulatory_scope.yaml",
        "regulatory_sources.yaml",
        "ccf_parameters.yaml",
        "crm_parameters.yaml",
        "sa_risk_weights.yaml",
        "irb_parameters.yaml",
        "pd_transition_assumptions.yaml",
        "capital_parameters.yaml",
        "stress_scenarios.yaml",
    ]
    return {Path(name).stem: load_yaml(name, config_dir) for name in names}
