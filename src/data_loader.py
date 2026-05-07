"""
data_loader.py — Alpha Vantage Data Fetcher
=============================================
Replaces FMP with Alpha Vantage — free, no rate-limit issues on Streamlit Cloud.
Get your free API key instantly at: https://alphavantage.co/support/#api-key

Endpoints used (all free tier):
  - CASH_FLOW        → operatingCashflow, capitalExpenditures
  - INCOME_STATEMENT → totalRevenue, netIncome, ebitda
  - BALANCE_SHEET    → totalAssets, totalLiabilities
  - OVERVIEW         → market cap, P/E, sector, beta, shares outstanding
  - GLOBAL_QUOTE     → current price
"""

import requests
import pandas as pd
from typing import Optional

BASE_URL = "https://www.alphavantage.co/query"


def _get(function: str, symbol: str, api_key: str) -> tuple:
    """
    GET request to Alpha Vantage.
    Returns (data: dict | None, error: str | None).
    """
    try:
        resp = requests.get(
            BASE_URL,
            params={"function": function, "symbol": symbol, "apikey": api_key},
            timeout=20,
        )
        body = resp.json()

        # Alpha Vantage signals errors in these keys
        if "Error Message" in body:
            return None, body["Error Message"]
        if "Information" in body:          # rate limit message
            return None, body["Information"]
        if "Note" in body:                 # rate limit note
            return None, body["Note"]

        return body, None

    except requests.exceptions.Timeout:
        return None, "Request timed out. Try again."
    except Exception as e:
        return None, str(e)


def test_api_key(api_key: str) -> tuple:
    """
    Quick test: fetch AAPL OVERVIEW.
    Returns (ok: bool, message: str).
    """
    if not api_key or not api_key.strip():
        return False, "No API key provided."

    data, err = _get("OVERVIEW", "AAPL", api_key)
    if err:
        return False, f"API error: {err}"
    if not data or "Symbol" not in data:
        return False, "Key invalid or no data returned."
    return True, f"✅ Key valid — connected to Alpha Vantage"


def load_financials(ticker: str, api_key: str) -> dict:
    """
    Fetch all financial data for a ticker from Alpha Vantage.

    Returns dict with keys:
        cashflow, income, balance, overview, quote, ticker, error
    """
    result = {
        "cashflow":     None,
        "income":       None,
        "balance":      None,
        "overview":     {},
        "quote":        {},
        "ticker":       ticker.upper().strip(),
        "error":        None,
        "_raw_errors":  [],
    }

    if not api_key or not api_key.strip():
        result["error"] = (
            "Alpha Vantage API key missing.\n"
            "Get your free key instantly at: https://alphavantage.co/support/#api-key"
        )
        return result

    t = ticker.upper().strip()

    # ── Cash Flow ─────────────────────────────────────────────────────────────
    cf, err = _get("CASH_FLOW", t, api_key)
    if err:
        result["_raw_errors"].append(f"CASH_FLOW: {err}")
    elif cf and cf.get("annualReports"):
        result["cashflow"] = cf["annualReports"]   # list of annual dicts

    # ── Income Statement ──────────────────────────────────────────────────────
    inc, err = _get("INCOME_STATEMENT", t, api_key)
    if err:
        result["_raw_errors"].append(f"INCOME_STATEMENT: {err}")
    elif inc and inc.get("annualReports"):
        result["income"] = inc["annualReports"]

    # ── Balance Sheet ─────────────────────────────────────────────────────────
    bal, err = _get("BALANCE_SHEET", t, api_key)
    if err:
        result["_raw_errors"].append(f"BALANCE_SHEET: {err}")
    elif bal and bal.get("annualReports"):
        result["balance"] = bal["annualReports"]

    # ── Company Overview (sector, P/E, market cap, beta…) ────────────────────
    ov, err = _get("OVERVIEW", t, api_key)
    if err:
        result["_raw_errors"].append(f"OVERVIEW: {err}")
    elif ov and "Symbol" in ov:
        result["overview"] = ov

    # ── Current Quote (live price) ────────────────────────────────────────────
    qt, err = _get("GLOBAL_QUOTE", t, api_key)
    if err:
        result["_raw_errors"].append(f"GLOBAL_QUOTE: {err}")
    elif qt and qt.get("Global Quote"):
        result["quote"] = qt["Global Quote"]

    # ── Validity check ────────────────────────────────────────────────────────
    has_data = any([result["cashflow"], result["income"],
                    result["balance"],  result["overview"]])

    if not has_data:
        raw = " | ".join(result["_raw_errors"])
        if "rate limit" in raw.lower() or "api call frequency" in raw.lower():
            result["error"] = (
                "Rate limit reached (25 requests/day on free tier). "
                "Wait until tomorrow or upgrade at alphavantage.co/premium"
            )
        elif "invalid api" in raw.lower() or not result["_raw_errors"]:
            result["error"] = (
                f"No data found for '{ticker}'. "
                "Check the ticker symbol (e.g. AAPL, MSFT, TSLA). "
                "Alpha Vantage covers US stocks and major international tickers."
            )
        else:
            result["error"] = f"Could not fetch data for '{ticker}'. Details: {raw}"

    return result


def _safe_float(value) -> Optional[float]:
    """Convert string or numeric to float, return None if invalid."""
    try:
        v = float(value)
        return None if v == 0 else v
    except (TypeError, ValueError):
        return None


def get_key_metrics(overview: dict, quote: dict) -> dict:
    """
    Build unified metrics dict from Alpha Vantage OVERVIEW + GLOBAL_QUOTE.
    Alpha Vantage returns all numeric fields as strings — we convert here.
    """
    # Current price: prefer live quote, fallback to overview's AnalystTargetPrice
    price = _safe_float(quote.get("05. price")) or _safe_float(overview.get("50DayMovingAverage"))

    return {
        "company_name":       overview.get("Name", "N/A"),
        "sector":             overview.get("Sector", "N/A"),
        "industry":           overview.get("Industry", "N/A"),
        "country":            overview.get("Country", "N/A"),
        "exchange":           overview.get("Exchange", ""),
        "market_cap":         _safe_float(overview.get("MarketCapitalization")),
        "current_price":      price,
        "pe_ratio":           _safe_float(overview.get("PERatio")),
        "forward_pe":         _safe_float(overview.get("ForwardPE")),
        "peg_ratio":          _safe_float(overview.get("PEGRatio")),
        "ev_ebitda":          _safe_float(overview.get("EVToEBITDA")),
        "debt_to_equity":     _safe_float(overview.get("DebtToEquityRatio")),
        "profit_margin":      _safe_float(overview.get("ProfitMargin")),
        "roe":                _safe_float(overview.get("ReturnOnEquityTTM")),
        "beta":               _safe_float(overview.get("Beta")),
        "52w_high":           _safe_float(overview.get("52WeekHigh")),
        "52w_low":            _safe_float(overview.get("52WeekLow")),
        "shares_outstanding": _safe_float(overview.get("SharesOutstanding")),
        "description":        overview.get("Description", ""),
        "website":            "",   # not in AV free tier
    }
