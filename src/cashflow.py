"""
cashflow.py — Cash Flow Analysis Engine (FMP version)
======================================================
Computes Free Cash Flow from FMP cash-flow-statement data.

FMP returns a clean list of dicts with standardised field names,
so no more multi-key fallback parsing needed.

FCF = operatingCashFlow + capitalExpenditure
(FMP reports capitalExpenditure as a NEGATIVE number — addition is correct)
"""

import pandas as pd
from typing import Optional, Tuple


def compute_free_cash_flow(
    cashflow_data: Optional[list],
) -> Tuple[Optional[pd.Series], dict]:
    """
    Compute Free Cash Flow from FMP cash-flow-statement list.

    Args:
        cashflow_data: list of annual cash flow dicts from FMP API
                       (most recent first)

    Returns:
        Tuple of:
            - pd.Series  FCF values indexed by fiscal year date (or None)
            - dict       debug info with warnings and red_flags
    """
    debug = {
        "ocf_key_used":   "operatingCashFlow",
        "capex_key_used": "capitalExpenditure",
        "available_keys": [],
        "warnings":       [],
        "red_flags":      [],
    }

    if not cashflow_data:
        debug["warnings"].append("Cash flow data is empty or None.")
        return None, debug

    dates, fcf_values = [], []

    for entry in cashflow_data:
        debug["available_keys"] = list(entry.keys())

        ocf   = entry.get("operatingCashFlow")
        capex = entry.get("capitalExpenditure")   # negative in FMP
        date  = entry.get("date", "N/A")

        if ocf is None:
            debug["warnings"].append(f"operatingCashFlow missing for {date}")
            continue
        if capex is None:
            # Fallback: FCF = OCF only
            debug["warnings"].append(
                f"capitalExpenditure missing for {date} — using OCF as FCF."
            )
            capex = 0

        try:
            fcf = float(ocf) + float(capex)   # capex is already negative
            dates.append(date)
            fcf_values.append(fcf)
        except (ValueError, TypeError):
            debug["warnings"].append(f"Non-numeric cash flow values for {date}")

    if not fcf_values:
        debug["warnings"].append("Could not compute FCF for any period.")
        return None, debug

    fcf_series = pd.Series(data=fcf_values, index=dates)

    # ── Red Flag Detection ────────────────────────────────────────────────────
    if (fcf_series < 0).all():
        debug["red_flags"].append(
            "🚨 FCF is NEGATIVE across ALL periods — business is burning cash."
        )
    elif (fcf_series < 0).any():
        debug["red_flags"].append(
            "⚠️ FCF turned negative in some periods — monitor the trend closely."
        )

    ocf_vals = [
        float(e.get("operatingCashFlow", 0))
        for e in cashflow_data
        if e.get("operatingCashFlow") is not None
    ]
    if ocf_vals and all(o > 0 for o in ocf_vals):
        if (fcf_series < 0).any():
            debug["red_flags"].append(
                "⚠️ High CapEx is consuming operating cash flow — growth investment phase."
            )

    return fcf_series, debug
