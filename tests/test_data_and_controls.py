from __future__ import annotations

from basel_credit_risk.data_generation import generate_portfolio
from basel_credit_risk.data_validation import validate_exposures


def test_generation_is_reproducible() -> None:
    first = generate_portfolio(500, 7).current
    second = generate_portfolio(500, 7).current
    assert first.equals(second)


def test_generated_data_passes_validation() -> None:
    portfolio = generate_portfolio(500, 42)
    assert validate_exposures(portfolio.current).empty
    assert validate_exposures(portfolio.prior).empty


def test_current_portfolio_has_requested_size() -> None:
    assert len(generate_portfolio(1_000, 42).current) == 1_000

