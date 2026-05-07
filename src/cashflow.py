"""
cashflow.py — Cash Flow Analysis Engine (Alpha Vantage version)
================================================================
Alpha Vantage CASH_FLOW annualReports fields:
  - operatingCashflow       (positive = cash in)
  - capitalExpenditures     (positive number — AV reports CapEx as POSITIVE)

FCF = operatingCashflow - capitalExpenditures
"""

import pandas as pd
from typing import Optional, Tuple


def compute_free_cash_flow(
    cashflow_data: Optional[list],
) -> Tuple[Optional[pd.Series], dict]:
    """
    Compute Free Cash Flow from Alpha Vantage annualReports list.

    Args:
        cashflow_data: list of annual cash flow dicts from Alpha Vantage
                       (most recent first, fields are STRING values)

    Returns:
        Tuple of:
            - pd.Series  FCF indexed by fiscalDateEnding (or None)
            - dict       debug / red flags
    """
    debug = {
        "ocf_key_used":   "operatingCashflow",
        "capex_key_used": "capitalExpenditures",
        "available_keys": [],
        "warnings":       [],
        "red_flags":      [],
    }

    if not cashflow_data:
        debug["warnings"].append("Cash flow data is empty or None.")
        return None, debug

    dates, fcf_values = [], []

    for entry in cashflow_data[:5]:   # max 5 years
        if not debug["available_keys"]:
            debug["available_keys"] = list(entry.keys())

        date  = entry.get("fiscalDateEnding", "N/A")

        # Alpha Vantage returns numeric strings — "None" means missing
        ocf_raw   = entry.get("operatingCashflow", "None")
        capex_raw = entry.get("capitalExpenditures", "None")

        try:
            ocf = float(ocf_raw) if ocf_raw not in ("None", "", None) else None
        except ValueError:
            ocf = None

        try:
            # AV reports CapEx as a POSITIVE number — subtract from OCF
            capex = float(capex_raw) if capex_raw not in ("None", "", None) else None
        except ValueError:
            capex = None

        if ocf is None:
            debug["warnings"].append(f"operatingCashflow missing for {date}")
            continue

        if capex is None:
            debug["warnings"].append(f"capitalExpenditures missing for {date} — using OCF as FCF")
            capex = 0

        fcf = ocf - capex    # Note: subtract because AV CapEx is positive
        dates.append(date)
        fcf_values.append(fcf)

    if not fcf_values:
        debug["warnings"].append("Could not compute FCF for any period.")
        return None, debug

    fcf_series = pd.Series(data=fcf_values, index=dates)

    # ── Red Flag Detection ─────────────────────────────────────────────────────
    if (fcf_series < 0).all():
        debug["red_flags"].append(
            "🚨 FCF NEGATIVE across ALL periods — business is burning cash."
        )
    elif (fcf_series < 0).any():
        debug["red_flags"].append(
            "⚠️ FCF turned negative in some periods — monitor the trend."
        )

    # Check if CapEx is eroding strong OCF
    if len(fcf_values) >= 2:
        if fcf_values[0] < fcf_values[1] * 0.8:
            debug["red_flags"].append(
                "⚠️ FCF declining year-over-year — investigate CapEx or revenue trends."
            )

    return fcf_series, debug
