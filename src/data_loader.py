"""
data_loader.py — Yahoo Finance Data Fetcher
============================================
Fetches and normalizes financial statements for a given ticker.
Patches the yfinance session with browser-like headers to bypass
Yahoo Finance rate limiting (HTTP 429 Too Many Requests).
"""

import yfinance as yf
import pandas as pd
import requests

# ─── Browser-like headers to bypass Yahoo Finance rate limiting ───────────────
# Yahoo Finance blocks automated requests that don't look like a real browser.
# We patch the yfinance session with these headers before any request is made.

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest":  "document",
    "Sec-Fetch-Mode":  "navigate",
    "Sec-Fetch-Site":  "none",
    "Sec-Fetch-User":  "?1",
}


def _make_ticker(ticker: str) -> yf.Ticker:
    """
    Create a yfinance Ticker with a patched session that sends
    browser-like headers, bypassing Yahoo Finance rate limits.
    """
    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)
    return yf.Ticker(ticker, session=session)


def load_financials(ticker: str) -> dict:
    """
    Fetch all financial statements for a ticker from Yahoo Finance.

    Args:
        ticker (str): Stock symbol (e.g., "AAPL", "MSFT")

    Returns:
        dict with keys:
            - cashflow     : pd.DataFrame (cash flow statement)
            - income       : pd.DataFrame (income statement)
            - balance      : pd.DataFrame (balance sheet)
            - info         : dict (market cap, sector, P/E, etc.)
            - ticker       : str (the original ticker)
            - error        : str | None (error message if any)
    """
    result = {
        "cashflow": None,
        "income": None,
        "balance": None,
        "info": {},
        "ticker": ticker.upper().strip(),
        "error": None,
    }

    try:
        stock = _make_ticker(ticker)

        # --- Cash Flow Statement ---
        cf = stock.cashflow
        if cf is not None and not cf.empty:
            # Yahoo Finance returns columns as dates, rows as line items
            # We normalize the index to ensure consistent key matching
            cf.index = cf.index.astype(str).str.strip()
            result["cashflow"] = cf

        # --- Income Statement ---
        inc = stock.financials
        if inc is not None and not inc.empty:
            inc.index = inc.index.astype(str).str.strip()
            result["income"] = inc

        # --- Balance Sheet ---
        bal = stock.balance_sheet
        if bal is not None and not bal.empty:
            bal.index = bal.index.astype(str).str.strip()
            result["balance"] = bal

        # --- Company Info (metadata) ---
        info = stock.info
        if info:
            result["info"] = info

        # Basic validity check: if all statements are None, ticker is likely invalid
        if (
            result["cashflow"] is None
            and result["income"] is None
            and result["balance"] is None
        ):
            result["error"] = (
                f"No financial data found for '{ticker}'. "
                "Please verify the ticker symbol is correct and listed on a supported exchange."
            )

    except Exception as e:
        err = str(e)
        if "Too Many Requests" in err or "429" in err or "Rate" in err:
            result["error"] = (
                "Yahoo Finance rate limit reached. "
                "Please wait 30 seconds and try again."
            )
        elif "No data found" in err or "404" in err:
            result["error"] = (
                f"Ticker '{ticker}' not found. Check the symbol and try again."
            )
        else:
            result["error"] = f"Data fetch failed for '{ticker}': {err}"

    return result


def get_key_metrics(info: dict) -> dict:
    """
    Extract key market metrics from the Yahoo Finance info dict.

    Returns a clean dict of the most relevant valuation metrics.
    """
    return {
        "company_name":   info.get("longName", "N/A"),
        "sector":         info.get("sector", "N/A"),
        "industry":       info.get("industry", "N/A"),
        "country":        info.get("country", "N/A"),
        "market_cap":     info.get("marketCap"),
        "current_price":  info.get("currentPrice") or info.get("regularMarketPrice"),
        "pe_ratio":       info.get("trailingPE"),
        "forward_pe":     info.get("forwardPE"),
        "peg_ratio":      info.get("pegRatio"),
        "ev_ebitda":      info.get("enterpriseToEbitda"),
        "debt_to_equity": info.get("debtToEquity"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth":info.get("earningsGrowth"),
        "profit_margin":  info.get("profitMargins"),
        "roe":            info.get("returnOnEquity"),
        "beta":           info.get("beta"),
        "52w_high":       info.get("fiftyTwoWeekHigh"),
        "52w_low":        info.get("fiftyTwoWeekLow"),
        "shares_outstanding": info.get("sharesOutstanding"),
    }
