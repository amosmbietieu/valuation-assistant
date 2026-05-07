"""
data_loader.py — Financial Modeling Prep (FMP) Data Fetcher
=============================================================
Replaces yfinance with the FMP REST API, which works reliably
on Streamlit Cloud without rate-limiting issues.

Free tier: 250 requests/day — sufficient for this app.
Get your free API key at: https://financialmodelingprep.com
"""

import requests
import pandas as pd
from typing import Optional

BASE_URL = "https://financialmodelingprep.com/api/v3"


def _get(endpoint: str, api_key: str, params: dict = None) -> Optional[list]:
    """
    Make a GET request to the FMP API.
    Returns parsed JSON list, or None on any error.
    """
    url = f"{BASE_URL}/{endpoint}"
    p = {"apikey": api_key, **(params or {})}
    try:
        resp = requests.get(url, params=p, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # FMP returns {"Error Message": "..."} on bad key / unknown ticker
        if isinstance(data, dict) and "Error Message" in data:
            return None
        return data if isinstance(data, list) else None
    except Exception:
        return None


def load_financials(ticker: str, api_key: str) -> dict:
    """
    Fetch all financial statements for a ticker from FMP.

    Args:
        ticker  : Stock symbol (e.g., "AAPL", "MSFT")
        api_key : FMP API key

    Returns:
        dict with keys:
            - cashflow  : list of annual cash flow dicts
            - income    : list of annual income statement dicts
            - balance   : list of annual balance sheet dicts
            - profile   : dict with company info + market data
            - metrics   : dict with key valuation metrics
            - ticker    : str
            - error     : str | None
    """
    result = {
        "cashflow": None,
        "income":   None,
        "balance":  None,
        "profile":  {},
        "metrics":  {},
        "ticker":   ticker.upper().strip(),
        "error":    None,
    }

    if not api_key or not api_key.strip():
        result["error"] = (
            "FMP API key is missing. "
            "Please enter your key in the sidebar. "
            "Get a free key at financialmodelingprep.com"
        )
        return result

    t = ticker.upper().strip()

    # ── Cash Flow Statement ───────────────────────────────────────────────────
    cf = _get(f"cash-flow-statement/{t}", api_key, {"limit": 5})
    if cf:
        result["cashflow"] = cf

    # ── Income Statement ──────────────────────────────────────────────────────
    inc = _get(f"income-statement/{t}", api_key, {"limit": 5})
    if inc:
        result["income"] = inc

    # ── Balance Sheet ─────────────────────────────────────────────────────────
    bal = _get(f"balance-sheet-statement/{t}", api_key, {"limit": 5})
    if bal:
        result["balance"] = bal

    # ── Company Profile (includes price, market cap, sector…) ────────────────
    prof = _get(f"profile/{t}", api_key)
    if prof and len(prof) > 0:
        result["profile"] = prof[0]

    # ── Key Metrics (P/E, EV/EBITDA, ROE…) ───────────────────────────────────
    met = _get(f"key-metrics/{t}", api_key, {"limit": 1})
    if met and len(met) > 0:
        result["metrics"] = met[0]

    # ── Validity check ────────────────────────────────────────────────────────
    if (
        result["cashflow"] is None
        and result["income"]  is None
        and result["balance"] is None
        and not result["profile"]
    ):
        result["error"] = (
            f"No data found for '{ticker}'. "
            "Check the ticker symbol. "
            "Note: some non-US tickers require the exchange suffix (e.g. 'VOD.L')."
        )

    return result


def get_key_metrics(profile: dict, metrics: dict) -> dict:
    """
    Build a unified metrics dict from FMP profile + key-metrics endpoints.
    Field names match the rest of the app exactly.
    """
    return {
        "company_name":       profile.get("companyName", "N/A"),
        "sector":             profile.get("sector", "N/A"),
        "industry":           profile.get("industry", "N/A"),
        "country":            profile.get("country", "N/A"),
        "market_cap":         profile.get("mktCap"),
        "current_price":      profile.get("price"),
        "pe_ratio":           metrics.get("peRatio"),
        "forward_pe":         None,   # not in FMP free tier
        "peg_ratio":          metrics.get("pegRatio"),
        "ev_ebitda":          metrics.get("enterpriseValueOverEBITDA"),
        "debt_to_equity":     metrics.get("debtToEquity"),
        "revenue_growth":     None,   # computed from income statements if needed
        "earnings_growth":    None,
        "profit_margin":      metrics.get("netProfitMargin"),
        "roe":                metrics.get("roe"),
        "beta":               profile.get("beta"),
        "52w_high":           profile.get("range", "").split("-")[-1].strip() if profile.get("range") else None,
        "52w_low":            profile.get("range", "").split("-")[0].strip() if profile.get("range") else None,
        "shares_outstanding": profile.get("sharesOutstanding"),
        "description":        profile.get("description", ""),
        "website":            profile.get("website", ""),
        "exchange":           profile.get("exchangeShortName", ""),
    }
