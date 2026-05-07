"""
cashflow.py — Cash Flow Analysis Engine (Alpha Vantage version)
================================================================
Alpha Vantage CASH_FLOW annualReports field names:
  - operatingCashflow       (positive = cash generated)
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
        cashflow_data : list of annual dicts, most recent first.
                        All numeric fields are STRING values in AV.
    Returns:
        Tuple:
            - pd.Series  FCF indexed by fiscalDateEnding  (or None)
            - dict       debug / red_flags
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

    for entry in cashflow_data[:5]:
        if not debug["available_keys"]:
            debug["available_keys"] = list(entry.keys())

        date      = entry.get("fiscalDateEnding", "N/A")
        ocf_raw   = entry.get("operatingCashflow",    "None")
        capex_raw = entry.get("capitalExpenditures",  "None")

        # Alpha Vantage uses the string "None" for missing values
        def to_float(v):
            if v in (None, "", "None"):
                return None
            try:
                return float(v)
            except ValueError:
                return None

        ocf   = to_float(ocf_raw)
        capex = to_float(capex_raw)

        if ocf is None:
            debug["warnings"].append(f"operatingCashflow missing for {date}")
            continue

        if capex is None:
            debug["warnings"].append(
                f"capitalExpenditures missing for {date} — FCF = OCF only"
            )
            capex = 0.0

        # AV reports CapEx as a POSITIVE number → subtract from OCF
        fcf = ocf - capex
        dates.append(date)
        fcf_values.append(fcf)

    if not fcf_values:
        debug["warnings"].append("Could not compute FCF for any period.")
        return None, debug

    fcf_series = pd.Series(data=fcf_values, index=dates)

    # ── Red Flag Detection ────────────────────────────────────────────────────
    # Only flag truly negative FCF
    negative_count = int((fcf_series < 0).sum())

    if negative_count == len(fcf_series):
        debug["red_flags"].append(
            "🚨 FCF NEGATIVE across ALL periods — business is burning cash."
        )
    elif negative_count > 0:
        debug["red_flags"].append(
            f"⚠️ FCF was negative in {negative_count} of {len(fcf_series)} periods — monitor the trend."
        )

    # "Declining" flag: only if the MOST RECENT year is significantly lower
    # than the prior year (>20% drop). Never trigger on older dips.
    if len(fcf_values) >= 2:
        latest = fcf_values[0]
        prior  = fcf_values[1]
        # Only meaningful if prior year was positive
        if prior > 0 and latest < prior * 0.80:
            debug["red_flags"].append(
                "⚠️ FCF declined >20% year-over-year — investigate CapEx or revenue trends."
            )

    return fcf_series, debug
