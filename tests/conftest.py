"""Shared fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from ballast.data import FactorData
from ballast.synthetic import synthetic_factors

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def synthetic() -> FactorData:
    """Seeded synthetic factors, 1926-07 to 1975-12, to keep the suite quick."""
    return synthetic_factors(end="1975-12-31")
