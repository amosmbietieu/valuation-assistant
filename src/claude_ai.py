"""
claude_ai.py — Claude API Integration
=======================================
Sends structured financial data to Claude and returns
professional-grade analysis: risks, opportunities,
red flags, and investment recommendations.
"""

import os
import requests
import json
from typing import Optional


# ─── API Configuration ────────────────────────────────────────────────────────

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL             = "claude-opus-4-5"
MAX_TOKENS        = 1200


# ─── Main Analysis Function ───────────────────────────────────────────────────

def generate_insight(
    ticker:         str,
    firm_value:     float,
    fcf:            float,
    scenarios:      dict,
    metrics:        dict,
    red_flags:      list[str],
    api_key:        Optional[str] = None,
) -> str:
    """
    Send enriched financial context to Claude and return structured analysis.

    Args:
        ticker      : Company stock symbol
        firm_value  : Base-case DCF estimated firm value
        fcf         : Latest Free Cash Flow
        scenarios   : Dict of Bear/Base/Bull DCFResult objects
        metrics     : Key market metrics dict (from get_key_metrics)
        red_flags   : List of red flag strings from cashflow analysis
        api_key     : Anthropic API key (falls back to ANTHROPIC_API_KEY env var)

    Returns:
        str: Formatted analysis text from Claude
    """

    # Resolve API key
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return (
            "⚠️ **Claude API key not configured.**\n\n"
            "Add your Anthropic API key in the sidebar to enable AI analysis.\n"
            "Get one at: https://console.anthropic.com/"
        )

    # ── Build the prompt ──────────────────────────────────────────────────────
    bear = scenarios.get("Bear")
    base = scenarios.get("Base")
    bull = scenarios.get("Bull")

    scenario_summary = ""
    for name, result in scenarios.items():
        mos = f"{result.margin_of_safety:.1%}" if result.margin_of_safety is not None else "N/A"
        upside = f"{result.upside_pct:.1f}%" if result.upside_pct is not None else "N/A"
        intrinsic = f"${result.intrinsic_value_per_share:.2f}" if result.intrinsic_value_per_share else "N/A"
        scenario_summary += (
            f"\n  {name}: Firm Value = ${result.firm_value/1e9:.2f}B | "
            f"Intrinsic/Share = {intrinsic} | Upside = {upside} | MoS = {mos}"
        )

    red_flags_text = "\n  ".join(red_flags) if red_flags else "None detected"

    prompt = f"""
You are a senior equity research analyst at a top-tier investment bank.
Analyze the following valuation data for {ticker} and provide a professional, 
structured investment report. Be specific, quantitative, and critical.

═══════════════════════════════════════════════════
COMPANY: {ticker}
Company Name: {metrics.get('company_name', 'N/A')}
Sector: {metrics.get('sector', 'N/A')} | Industry: {metrics.get('industry', 'N/A')}
Country: {metrics.get('country', 'N/A')}

═══════════════════════════════════════════════════
MARKET DATA
Current Price:   ${metrics.get('current_price') or 'N/A'}
Market Cap:      ${(metrics.get('market_cap') or 0)/1e9:.2f}B
Trailing P/E:    {metrics.get('pe_ratio') or 'N/A'}
Forward P/E:     {metrics.get('forward_pe') or 'N/A'}
PEG Ratio:       {metrics.get('peg_ratio') or 'N/A'}
EV/EBITDA:       {metrics.get('ev_ebitda') or 'N/A'}
Debt/Equity:     {metrics.get('debt_to_equity') or 'N/A'}
Revenue Growth:  {f"{metrics.get('revenue_growth'):.1%}" if metrics.get('revenue_growth') else 'N/A'}
Profit Margin:   {f"{metrics.get('profit_margin'):.1%}" if metrics.get('profit_margin') else 'N/A'}
ROE:             {f"{metrics.get('roe'):.1%}" if metrics.get('roe') else 'N/A'}
Beta:            {metrics.get('beta') or 'N/A'}

═══════════════════════════════════════════════════
DCF VALUATION — SCENARIO ANALYSIS
Latest FCF: ${fcf/1e9:.2f}B
{scenario_summary}

═══════════════════════════════════════════════════
CASH FLOW RED FLAGS
  {red_flags_text}

═══════════════════════════════════════════════════
Please structure your response EXACTLY as follows:

## 📊 Earnings Quality Assessment
[2–3 sentences on FCF vs Net Income reliability, accrual accounting risks]

## 🔍 Valuation Analysis
[Compare DCF intrinsic value vs market price. Comment on all 3 scenarios. 
Is the stock over/under/fairly valued?]

## 🚀 Growth Drivers
[Top 2–3 specific, quantified growth catalysts]

## ⚠️ Key Risks
[Top 3 specific risks with probability/impact assessment]

## 🏁 Investment Recommendation
**Rating: [STRONG BUY / BUY / HOLD / SELL / STRONG SELL]**
[2–3 sentence justification with specific price target or range]

## 🤖 AI Model Limitations
[2 sentences on what this model cannot capture — macro shocks, management quality, etc.]
"""

    # ── API Call ──────────────────────────────────────────────────────────────
    try:
        response = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )

        if response.status_code == 200:
            data = response.json()
            return data["content"][0]["text"]

        elif response.status_code == 401:
            return "❌ **Invalid API Key.** Please check your Anthropic API key in the sidebar."

        elif response.status_code == 429:
            return "⏳ **Rate limit reached.** Please wait a moment and try again."

        else:
            error_body = response.json().get("error", {}).get("message", "Unknown error")
            return f"❌ **Claude API Error {response.status_code}:** {error_body}"

    except requests.exceptions.Timeout:
        return "⏳ **Request timed out.** Claude API took too long. Please try again."
    except requests.exceptions.RequestException as e:
        return f"❌ **Network error:** {str(e)}"
    except Exception as e:
        return f"❌ **Unexpected error:** {str(e)}"
