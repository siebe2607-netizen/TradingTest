"""
Sector-Aware Benchmarks
========================
GICS sector profiles providing baseline valuation parameters.
Keys match yfinance ``ticker.info["sector"]`` values exactly.
"""

# Default profile for unknown / missing sectors
DEFAULT_PROFILE: dict = {
    "base_ps_multiple": 3.0,
    "base_ev_ebitda": 10.0,
    "expected_growth": 0.08,
    "discount_rate_adj": 0.0,
    "margin_of_safety": 0.20,
}

SECTOR_PROFILES: dict[str, dict] = {
    "Technology": {
        "base_ps_multiple": 8.0,
        "base_ev_ebitda": 15.0,
        "expected_growth": 0.15,
        "discount_rate_adj": 0.01,
        "margin_of_safety": 0.25,
    },
    "Healthcare": {
        "base_ps_multiple": 5.0,
        "base_ev_ebitda": 12.0,
        "expected_growth": 0.10,
        "discount_rate_adj": 0.005,
        "margin_of_safety": 0.20,
    },
    "Financial Services": {
        "base_ps_multiple": 2.5,
        "base_ev_ebitda": 9.0,
        "expected_growth": 0.06,
        "discount_rate_adj": -0.005,
        "margin_of_safety": 0.15,
    },
    "Consumer Cyclical": {
        "base_ps_multiple": 3.0,
        "base_ev_ebitda": 10.0,
        "expected_growth": 0.08,
        "discount_rate_adj": 0.005,
        "margin_of_safety": 0.20,
    },
    "Consumer Defensive": {
        "base_ps_multiple": 2.5,
        "base_ev_ebitda": 11.0,
        "expected_growth": 0.05,
        "discount_rate_adj": -0.005,
        "margin_of_safety": 0.15,
    },
    "Communication Services": {
        "base_ps_multiple": 5.0,
        "base_ev_ebitda": 10.0,
        "expected_growth": 0.10,
        "discount_rate_adj": 0.005,
        "margin_of_safety": 0.20,
    },
    "Industrials": {
        "base_ps_multiple": 2.5,
        "base_ev_ebitda": 9.0,
        "expected_growth": 0.07,
        "discount_rate_adj": 0.0,
        "margin_of_safety": 0.18,
    },
    "Energy": {
        "base_ps_multiple": 1.5,
        "base_ev_ebitda": 5.0,
        "expected_growth": 0.04,
        "discount_rate_adj": 0.01,
        "margin_of_safety": 0.25,
    },
    "Utilities": {
        "base_ps_multiple": 2.0,
        "base_ev_ebitda": 8.0,
        "expected_growth": 0.03,
        "discount_rate_adj": -0.01,
        "margin_of_safety": 0.12,
    },
    "Real Estate": {
        "base_ps_multiple": 4.0,
        "base_ev_ebitda": 15.0,
        "expected_growth": 0.05,
        "discount_rate_adj": -0.005,
        "margin_of_safety": 0.15,
    },
    "Basic Materials": {
        "base_ps_multiple": 2.0,
        "base_ev_ebitda": 6.0,
        "expected_growth": 0.05,
        "discount_rate_adj": 0.005,
        "margin_of_safety": 0.20,
    },
}


def get_sector_profile(sector: str, industry: str = None) -> dict:
    """Return the profile for a GICS sector, falling back to DEFAULT_PROFILE."""
    return SECTOR_PROFILES.get(sector, DEFAULT_PROFILE)


def get_sector_ps_multiple(sector: str) -> float:
    return get_sector_profile(sector)["base_ps_multiple"]


def get_sector_discount_adjustment(sector: str) -> float:
    return get_sector_profile(sector)["discount_rate_adj"]


def get_sector_margin_of_safety(sector: str) -> float:
    return get_sector_profile(sector)["margin_of_safety"]
