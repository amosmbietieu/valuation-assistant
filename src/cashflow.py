"""
cashflow.py — Cash Flow Analysis Engine
=========================================
Computes Free Cash Flow (FCF) from Yahoo Finance statements.
Implements multi-key fallback logic to handle Yahoo Finance's
inconsistent naming across tickers and time periods.
"""

import pandas as pd
from typing import Optional, Tuple


# ─── Key Aliases ──────────────────────────────────────────────────────────────
# Yahoo Finance uses different field names across tickers and API versions.
# We attempt each alias in order until one is found.

OCF_KEYS = [
    "Operating Cash Flow",
    "Total Cash From Operating Activities",
    "Cash From Operations",
    "Net Cash Provided By Operating Activities",
    "CashFlowFromContinuingOperatingActivities",
]

CAPEX_KEYS = [
    "Capital Expenditure",
    "Capital Expenditures",
    "CapEx",
    "Purchase Of Property Plant And Equipment",
    "Purchases Of Property And Equipment",
    "Net PPE Purchase And Sale",
]


# ─── Core Function ────────────────────────────────────────────────────────────

def compute_free_cash_flow(
    cashflow_df: Optional[pd.DataFrame],
) -> Tuple[Optional[pd.Series], dict]:
    """
    Compute Free Cash Flow: FCF = Operating Cash Flow − CapEx

    Yahoo Finance reports CapEx as a negative number (cash outflow),
    so the formula FCF = OCF + CapEx (signed) is mathematically correct.

    Args:
        cashflow_df: Cash flow DataFrame from Yahoo Finance
                     (rows = line items, columns = dates)

    Returns:
        Tuple of:
            - pd.Series of FCF values indexed by date (or None on failure)
            - dict with debug info: keys found, warnings, red_flags
    """
    debug = {
        "ocf_key_used": None,
        "capex_key_used": None,
        "available_keys": [],
        "warnings": [],
        "red_flags": [],
    }

    if cashflow_df is None or cashflow_df.empty:
        debug["warnings"].append("Cash flow DataFrame is empty or None.")
        return None, debug

    # Normalize index once
    cashflow_df = cashflow_df.copy()
    cashflow_df.index = cashflow_df.index.astype(str).str.strip()
    debug["available_keys"] = list(cashflow_df.index)

    # ── Find Operating Cash Flow ──────────────────────────────────────────────
    ocf = _find_row(cashflow_df, OCF_KEYS)
    if ocf is None:
        debug["warnings"].append(
            f"Operating Cash Flow not found. Tried: {OCF_KEYS}"
        )
        return None, debug
    debug["ocf_key_used"] = _matching_key(cashflow_df, OCF_KEYS)

    # ── Find Capital Expenditures ─────────────────────────────────────────────
    capex = _find_row(cashflow_df, CAPEX_KEYS)
    if capex is None:
        debug["warnings"].append(
            f"CapEx not found. Tried: {CAPEX_KEYS}. FCF = OCF (CapEx assumed 0)."
        )
        # Fallback: FCF = OCF (conservative)
        fcf = ocf.dropna()
        debug["capex_key_used"] = "NOT FOUND — assumed 0"
    else:
        debug["capex_key_used"] = _matching_key(cashflow_df, CAPEX_KEYS)
        # CapEx is already negative in Yahoo Finance → addition is correct
        fcf = (ocf + capex).dropna()

    # ── Red Flag Detection ────────────────────────────────────────────────────
    if (fcf < 0).all():
        debug["red_flags"].append(
            "🚨 FCF is NEGATIVE across all periods — business burns cash."
        )
    elif (fcf < 0).any():
        debug["red_flags"].append(
            "⚠️  FCF turned negative in some periods — monitor trend."
        )

    if ocf is not None and capex is not None:
        if (ocf > 0).all() and (fcf < 0).any():
            debug["red_flags"].append(
                "⚠️  High CapEx is consuming all operating cash flow."
            )

    return fcf, debug


def compute_ocf_summary(cashflow_df: Optional[pd.DataFrame]) -> Optional[pd.Series]:
    """Return just the Operating Cash Flow series."""
    if cashflow_df is None or cashflow_df.empty:
        return None
    cashflow_df = cashflow_df.copy()
    cashflow_df.index = cashflow_df.index.astype(str).str.strip()
    return _find_row(cashflow_df, OCF_KEYS)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _find_row(df: pd.DataFrame, keys: list) -> Optional[pd.Series]:
    """Return the first matching row from a list of candidate keys."""
    for key in keys:
        if key in df.index:
            return pd.to_numeric(df.loc[key], errors="coerce")
    return None


def _matching_key(df: pd.DataFrame, keys: list) -> Optional[str]:
    """Return the first key from the list that exists in the DataFrame index."""
    for key in keys:
        if key in df.index:
            return key
    return None
