"""
dcf.py — Discounted Cash Flow Valuation Engine
================================================
Implements a professional DCF model with:
  - Multi-year FCF projection
  - Gordon Growth Terminal Value
  - Three-scenario analysis (Bear / Base / Bull)
  - Per-share intrinsic value computation
  - Margin of safety calculation
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class DCFResult:
    """Full output of a DCF valuation run."""
    scenario:           str
    growth_rate:        float
    discount_rate:      float
    years:              int
    fcf_projections:    list[float]   # nominal FCF per year
    pv_projections:     list[float]   # present value of each year's FCF
    terminal_value:     float         # nominal terminal value
    terminal_value_pv:  float         # PV of terminal value
    firm_value:         float         # total estimated firm value
    # Per-share fields (populated if shares_outstanding provided)
    intrinsic_value_per_share: Optional[float]
    current_price:      Optional[float]
    margin_of_safety:   Optional[float]  # (intrinsic - price) / intrinsic
    upside_pct:         Optional[float]  # (intrinsic / price - 1) * 100


# ─── Main Valuation Function ──────────────────────────────────────────────────

def dcf_valuation(
    fcf:               float,
    growth_rate:       float = 0.05,
    discount_rate:     float = 0.10,
    years:             int   = 5,
    terminal_growth:   float = 0.025,
    shares_outstanding: Optional[float] = None,
    current_price:     Optional[float]  = None,
    scenario:          str   = "Base",
) -> DCFResult:
    """
    Compute DCF valuation for a single scenario.

    Formula:
        Firm Value = Σ [ FCFₜ / (1+r)ᵗ ]  +  Terminal Value / (1+r)ⁿ
        Terminal Value = FCFₙ × (1+g) / (r − g)

    Args:
        fcf              : Latest (base) Free Cash Flow in dollars
        growth_rate      : Annual FCF growth rate during projection period
        discount_rate    : WACC / required rate of return
        years            : Projection horizon (typically 5–10)
        terminal_growth  : Perpetual growth rate post-horizon (< discount_rate)
        shares_outstanding: Number of shares for per-share calculation
        current_price    : Current market price for margin of safety
        scenario         : Label ("Bear", "Base", "Bull")

    Returns:
        DCFResult dataclass
    """

    # ── Validation ────────────────────────────────────────────────────────────
    if discount_rate <= terminal_growth:
        raise ValueError(
            f"Discount rate ({discount_rate:.1%}) must exceed terminal growth "
            f"({terminal_growth:.1%}) to avoid division by zero or negative values."
        )
    if fcf == 0:
        raise ValueError("FCF cannot be zero — no basis for valuation.")

    # ── FCF Projections ───────────────────────────────────────────────────────
    fcf_projections = []
    pv_projections  = []

    for t in range(1, years + 1):
        future_fcf  = fcf * ((1 + growth_rate) ** t)
        pv_fcf      = future_fcf / ((1 + discount_rate) ** t)
        fcf_projections.append(future_fcf)
        pv_projections.append(pv_fcf)

    # ── Terminal Value (Gordon Growth Model) ──────────────────────────────────
    # Terminal value is computed on the LAST projected FCF grown one more year
    terminal_value    = fcf_projections[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
    terminal_value_pv = terminal_value / ((1 + discount_rate) ** years)

    # ── Firm Value ────────────────────────────────────────────────────────────
    firm_value = sum(pv_projections) + terminal_value_pv

    # ── Per-Share Intrinsic Value ─────────────────────────────────────────────
    intrinsic_per_share = None
    margin_of_safety    = None
    upside_pct          = None

    if shares_outstanding and shares_outstanding > 0:
        intrinsic_per_share = firm_value / shares_outstanding

        if current_price and current_price > 0:
            margin_of_safety = (intrinsic_per_share - current_price) / intrinsic_per_share
            upside_pct       = (intrinsic_per_share / current_price - 1) * 100

    return DCFResult(
        scenario=scenario,
        growth_rate=growth_rate,
        discount_rate=discount_rate,
        years=years,
        fcf_projections=fcf_projections,
        pv_projections=pv_projections,
        terminal_value=terminal_value,
        terminal_value_pv=terminal_value_pv,
        firm_value=firm_value,
        intrinsic_value_per_share=intrinsic_per_share,
        current_price=current_price,
        margin_of_safety=margin_of_safety,
        upside_pct=upside_pct,
    )


# ─── Three-Scenario Analysis ──────────────────────────────────────────────────

def run_scenarios(
    fcf:               float,
    discount_rate:     float = 0.10,
    years:             int   = 5,
    terminal_growth:   float = 0.025,
    shares_outstanding: Optional[float] = None,
    current_price:     Optional[float]  = None,
) -> dict[str, DCFResult]:
    """
    Run Bear / Base / Bull scenarios with standardized growth assumptions.

    Returns:
        dict mapping scenario name → DCFResult
    """
    scenarios = {
        "Bear": dcf_valuation(
            fcf, growth_rate=0.02, discount_rate=discount_rate + 0.02,
            years=years, terminal_growth=terminal_growth,
            shares_outstanding=shares_outstanding, current_price=current_price,
            scenario="Bear"
        ),
        "Base": dcf_valuation(
            fcf, growth_rate=0.05, discount_rate=discount_rate,
            years=years, terminal_growth=terminal_growth,
            shares_outstanding=shares_outstanding, current_price=current_price,
            scenario="Base"
        ),
        "Bull": dcf_valuation(
            fcf, growth_rate=0.10, discount_rate=max(discount_rate - 0.01, 0.07),
            years=years, terminal_growth=terminal_growth,
            shares_outstanding=shares_outstanding, current_price=current_price,
            scenario="Bull"
        ),
    }
    return scenarios


def format_value(value: float) -> str:
    """Human-readable large number formatting (B / M / K)."""
    abs_val = abs(value)
    sign    = "-" if value < 0 else ""
    if abs_val >= 1e12:
        return f"{sign}${abs_val/1e12:.2f}T"
    elif abs_val >= 1e9:
        return f"{sign}${abs_val/1e9:.2f}B"
    elif abs_val >= 1e6:
        return f"{sign}${abs_val/1e6:.2f}M"
    elif abs_val >= 1e3:
        return f"{sign}${abs_val/1e3:.2f}K"
    else:
        return f"{sign}${abs_val:.2f}"
