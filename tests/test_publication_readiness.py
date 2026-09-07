from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree

import numpy as np

from basel_credit_risk.pipeline import run_pipeline

ROOT = Path(__file__).resolve().parents[1]


def test_defaulted_exposures_receive_default_sa_treatment() -> None:
    df = run_pipeline(portfolio_size=1_000, write_outputs=False).exposures
    defaulted = df[df["default_flag"].eq(1)]
    assert not defaulted.empty
    assert defaulted["basel_exposure_class"].eq("defaulted").all()
    assert defaulted["sa_risk_weight"].eq(1.5).all()


def test_retail_functions_have_no_corporate_maturity_adjustment() -> None:
    df = run_pipeline(portfolio_size=1_000, write_outputs=False).exposures
    retail = df[df["irb_function"].isin(["mortgage", "qrre", "other_retail"])]
    assert np.allclose(retail["maturity_adjustment"], 1.0)


def test_stress_increases_ead_and_expected_loss() -> None:
    scenarios = run_pipeline(portfolio_size=1_000, write_outputs=False).tables["scenario_summary"].set_index("scenario")
    assert scenarios.loc["base", "ead"] < scenarios.loc["adverse", "ead"] < scenarios.loc["severe", "ead"]
    assert scenarios.loc["base", "expected_loss"] < scenarios.loc["adverse", "expected_loss"] < scenarios.loc["severe", "expected_loss"]


def test_concentration_shares_sum_to_one() -> None:
    result = run_pipeline(portfolio_size=1_000, write_outputs=False)
    assert np.isclose(result.tables["sector_concentration"]["ead_share"].sum(), 1.0)
    assert np.isclose(result.tables["product_concentration"]["ead_share"].sum(), 1.0)


def test_sample_contains_only_synthetic_identifiers() -> None:
    sample = ROOT / "data" / "sample" / "synthetic_exposure_sample.csv"
    text = sample.read_text(encoding="utf-8")
    assert "EXP-" in text and "BOR-" in text
    assert "@" not in text


def test_excel_report_contains_required_sheets() -> None:
    report = ROOT / "outputs" / "demo" / "Basel_Credit_Capital_Report.xlsx"
    assert report.exists()
    with zipfile.ZipFile(report) as archive:
        workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
        root = ElementTree.fromstring(workbook_xml)
        namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        sheets = root.findall(".//x:sheet", namespace)
        assert len(sheets) == 11
        for name in ["01_Executive_Summary", "10_Reconciliation", "11_Methodology"]:
            assert name in workbook_xml


def test_repository_does_not_commit_generated_full_portfolio() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/generated/*" in gitignore
    assert "data/processed/*" in gitignore
