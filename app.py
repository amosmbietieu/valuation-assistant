"""
app.py — AI-Powered Valuation Assistant
=========================================
Main Streamlit entry point.
Orchestrates: data loading → cash flow analysis → DCF → Claude AI insights.

Run with:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from src.data_loader import load_financials, get_key_metrics
from src.cashflow import compute_free_cash_flow
from src.dcf import run_scenarios, format_value
from src.claude_ai import generate_insight


# ─── Page Configuration ───────────────────────────────────────────────────────

st.set_page_config(
    page_title="Valuation Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@300;400;500;600&display=swap');

/* ── Root Variables ── */
:root {
    --bg:        #0f1117;
    --surface:   #1a1d26;
    --border:    #2a2e3e;
    --accent:    #00d4aa;
    --accent2:   #4f8ef7;
    --danger:    #f75050;
    --warn:      #f7a650;
    --text:      #e8eaf0;
    --muted:     #7a7f9a;
    --gold:      #f0c040;
}

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background: var(--bg) !important;
    color: var(--text) !important;
}

/* ── Header ── */
.main-header {
    background: linear-gradient(135deg, #0f1117 0%, #1a1d26 50%, #0f1117 100%);
    border-bottom: 1px solid var(--border);
    padding: 2rem 0 1.5rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.main-header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(ellipse at center, rgba(0,212,170,0.04) 0%, transparent 60%);
    pointer-events: none;
}
.main-header h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 2.6rem;
    letter-spacing: -0.5px;
    color: var(--text);
    margin: 0;
}
.main-header .sub {
    font-size: 0.85rem;
    color: var(--muted);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 0.4rem;
}

/* ── Metric Cards ── */
.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    text-align: center;
    transition: border-color 0.2s;
}
.metric-card:hover { border-color: var(--accent); }
.metric-card .label {
    font-size: 0.7rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 0.3rem;
}
.metric-card .value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.4rem;
    font-weight: 500;
    color: var(--accent);
}
.metric-card .sub-value {
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 0.2rem;
}

/* ── Section Headers ── */
.section-header {
    border-left: 3px solid var(--accent);
    padding-left: 0.8rem;
    margin: 2rem 0 1rem;
}
.section-header h2 {
    font-family: 'DM Serif Display', serif;
    font-size: 1.4rem;
    color: var(--text);
    margin: 0;
}

/* ── Scenario Cards ── */
.scenario-bear { border-color: var(--danger) !important; }
.scenario-base { border-color: var(--accent2) !important; }
.scenario-bull { border-color: var(--accent) !important; }

.scenario-label-bear { color: var(--danger); }
.scenario-label-base { color: var(--accent2); }
.scenario-label-bull { color: var(--accent); }

/* ── Red Flag ── */
.red-flag {
    background: rgba(247,80,80,0.08);
    border: 1px solid rgba(247,80,80,0.3);
    border-radius: 8px;
    padding: 0.6rem 1rem;
    margin: 0.4rem 0;
    font-size: 0.85rem;
    color: #f75050;
}

/* ── Info Tag ── */
.info-tag {
    display: inline-block;
    background: rgba(79,142,247,0.1);
    border: 1px solid rgba(79,142,247,0.3);
    border-radius: 20px;
    padding: 0.15rem 0.7rem;
    font-size: 0.75rem;
    color: var(--accent2);
    margin-right: 0.4rem;
    margin-bottom: 0.3rem;
}

/* ── Tables ── */
.stDataFrame { border-radius: 8px; overflow: hidden; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

/* ── Streamlit native overrides ── */
.stTextInput input, .stNumberInput input, .stSelectbox select {
    background: #0f1117 !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 6px !important;
}
.stButton > button {
    background: var(--accent) !important;
    color: #0f1117 !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.5rem 1.5rem !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.5px;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }
.stAlert { border-radius: 8px !important; }

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 1.5rem 0 !important; }

/* ── Matplotlib dark backgrounds ── */
.element-container iframe { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# ─── Header ───────────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
    <h1>📊 AI Valuation Assistant</h1>
    <p class="sub">DCF · Free Cash Flow · Claude AI · Real-Time Data</p>
</div>
""", unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    st.markdown("---")

    # API Key
    st.markdown("**🔑 Claude API Key**")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        help="Get yours at console.anthropic.com",
        label_visibility="collapsed",
    )
    if api_key:
        st.success("✅ Key configured")
    else:
        st.warning("⚠️ Key required for AI insights")

    st.markdown("---")
    st.markdown("**📐 DCF Parameters**")

    discount_rate = st.slider(
        "Discount Rate (WACC)",
        min_value=0.06, max_value=0.20, value=0.10, step=0.01,
        format="%.0f%%",
        help="Required rate of return. Higher = more conservative."
    )
    terminal_growth = st.slider(
        "Terminal Growth Rate",
        min_value=0.01, max_value=0.05, value=0.025, step=0.005,
        format="%.1f%%",
        help="Perpetual growth rate. Must be less than WACC."
    )
    projection_years = st.slider(
        "Projection Horizon (years)",
        min_value=3, max_value=10, value=5,
        help="Number of years to project FCF forward."
    )

    st.markdown("---")
    st.markdown("**📚 About**")
    st.caption(
        "This tool combines real financial data from Yahoo Finance "
        "with a DCF model and Claude AI to generate valuation insights. "
        "Not financial advice — always apply human judgment."
    )


# ─── Main Input ───────────────────────────────────────────────────────────────

col_input, col_btn = st.columns([4, 1])
with col_input:
    ticker = st.text_input(
        "Enter Stock Ticker",
        placeholder="e.g., AAPL  •  MSFT  •  GOOGL  •  AMZN  •  TSLA",
        label_visibility="collapsed",
    )
with col_btn:
    analyze = st.button("🔍 Analyze", use_container_width=True)


# ─── Analysis Pipeline ────────────────────────────────────────────────────────

if ticker and analyze:
    ticker = ticker.strip().upper()

    with st.spinner(f"Fetching financial data for **{ticker}**..."):
        data = load_financials(ticker)

    # ── Error Handling ────────────────────────────────────────────────────────
    if data["error"]:
        st.error(f"❌ {data['error']}")
        st.stop()

    metrics = get_key_metrics(data["info"])
    company_name = metrics.get("company_name", ticker)

    # ── Company Header ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="margin: 1.5rem 0 0.5rem">
        <span class="info-tag">{metrics.get('sector', 'N/A')}</span>
        <span class="info-tag">{metrics.get('industry', 'N/A')}</span>
        <span class="info-tag">{metrics.get('country', 'N/A')}</span>
    </div>
    <h2 style="font-family: 'DM Serif Display', serif; font-size: 2rem; margin: 0 0 1.5rem">
        {company_name} <span style="color: #7a7f9a; font-size: 1rem;">({ticker})</span>
    </h2>
    """, unsafe_allow_html=True)

    # ── Key Market Metrics Row ────────────────────────────────────────────────
    def fmt_metric(val, fmt="plain", prefix="", suffix=""):
        if val is None:
            return "N/A"
        try:
            if fmt == "pct":
                return f"{prefix}{val:.1%}{suffix}"
            elif fmt == "large":
                return format_value(val)
            elif fmt == "2f":
                return f"{prefix}{val:.2f}{suffix}"
            else:
                return f"{prefix}{val}{suffix}"
        except:
            return "N/A"

    cols = st.columns(6)
    metric_data = [
        ("Market Cap",    fmt_metric(metrics.get("market_cap"), "large"),       ""),
        ("Current Price", fmt_metric(metrics.get("current_price"), "2f", "$"),  ""),
        ("Trailing P/E",  fmt_metric(metrics.get("pe_ratio"), "2f"),             ""),
        ("EV/EBITDA",     fmt_metric(metrics.get("ev_ebitda"), "2f"),             ""),
        ("Profit Margin", fmt_metric(metrics.get("profit_margin"), "pct"),        ""),
        ("Beta",          fmt_metric(metrics.get("beta"), "2f"),                  ""),
    ]
    for col, (label, value, sub) in zip(cols, metric_data):
        col.markdown(f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
            <div class="sub-value">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Cash Flow Analysis ────────────────────────────────────────────────────
    st.markdown("""
    <div class="section-header"><h2>💧 Cash Flow Analysis</h2></div>
    """, unsafe_allow_html=True)

    if data["cashflow"] is None:
        st.error("Cash flow statement unavailable for this ticker.")
        st.stop()

    fcf_series, debug = compute_free_cash_flow(data["cashflow"])

    # Debug info (expandable)
    with st.expander("🔧 Cash Flow Debug Info", expanded=False):
        st.write(f"**OCF Key Found:** `{debug['ocf_key_used']}`")
        st.write(f"**CapEx Key Found:** `{debug['capex_key_used']}`")
        st.write(f"**Available Statement Keys:**")
        st.code(str(debug["available_keys"]), language="text")

    if debug["red_flags"]:
        st.markdown("**⚠️ Red Flags Detected:**")
        for flag in debug["red_flags"]:
            st.markdown(f'<div class="red-flag">{flag}</div>', unsafe_allow_html=True)

    if fcf_series is None:
        st.error(
            "Could not compute Free Cash Flow from this ticker's data. "
            f"Warnings: {', '.join(debug['warnings'])}"
        )
        st.stop()

    # FCF Table
    fcf_df = pd.DataFrame({
        "Year":   [str(d)[:10] for d in fcf_series.index],
        "FCF ($)": [format_value(v) for v in fcf_series.values],
        "Raw ($)": fcf_series.values,
    })
    st.dataframe(
        fcf_df[["Year", "FCF ($)"]].set_index("Year"),
        use_container_width=True
    )

    # FCF Bar Chart
    fig, ax = plt.subplots(figsize=(9, 3.5))
    fig.patch.set_facecolor("#1a1d26")
    ax.set_facecolor("#1a1d26")

    years_labels = [str(d)[:4] for d in fcf_series.index]
    colors = ["#00d4aa" if v >= 0 else "#f75050" for v in fcf_series.values]
    bars = ax.bar(years_labels, fcf_series.values / 1e9, color=colors, width=0.6,
                  edgecolor="none", alpha=0.85)

    ax.axhline(0, color="#2a2e3e", linewidth=1)
    ax.set_ylabel("FCF ($ Billions)", color="#7a7f9a", fontsize=9)
    ax.tick_params(colors="#7a7f9a", labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("#2a2e3e")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.1f}B"))

    for bar, val in zip(bars, fcf_series.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (max(fcf_series.values) / 1e9) * 0.02,
            format_value(val),
            ha="center", va="bottom", color="#e8eaf0", fontsize=8
        )
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    # ── DCF Valuation ─────────────────────────────────────────────────────────
    st.markdown("""
    <div class="section-header"><h2>🏦 DCF Valuation — Scenario Analysis</h2></div>
    """, unsafe_allow_html=True)

    # Use most recent valid FCF
    latest_fcf = None
    for v in fcf_series.values:
        if not pd.isna(v) and v != 0:
            latest_fcf = float(v)
            break

    if latest_fcf is None:
        st.error("All FCF values are zero or NaN — cannot run DCF.")
        st.stop()

    shares = metrics.get("shares_outstanding")
    price  = metrics.get("current_price")

    with st.spinner("Running DCF model..."):
        try:
            scenarios = run_scenarios(
                fcf=latest_fcf,
                discount_rate=discount_rate,
                years=projection_years,
                terminal_growth=terminal_growth,
                shares_outstanding=shares,
                current_price=price,
            )
        except ValueError as e:
            st.error(f"DCF Error: {e}")
            st.stop()

    # Scenario Cards
    s_cols = st.columns(3)
    labels  = ["Bear", "Base", "Bull"]
    emojis  = ["🐻", "⚖️", "🚀"]
    colors  = ["scenario-bear", "scenario-base", "scenario-bull"]
    lcolors = ["scenario-label-bear", "scenario-label-base", "scenario-label-bull"]

    for col, name, emoji, cls, lcls in zip(s_cols, labels, emojis, colors, lcolors):
        r = scenarios[name]
        mos_str    = f"{r.margin_of_safety:.1%}" if r.margin_of_safety is not None else "N/A"
        upside_str = f"{r.upside_pct:+.1f}%" if r.upside_pct is not None else "N/A"
        price_str  = f"${r.intrinsic_value_per_share:.2f}" if r.intrinsic_value_per_share else "N/A"

        col.markdown(f"""
        <div class="metric-card {cls}" style="padding: 1.2rem;">
            <div class="label {lcls}" style="font-size:0.8rem; font-weight:600;">
                {emoji} {name} CASE
            </div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:1.3rem;
                        color: var(--text); margin: 0.5rem 0;">
                {format_value(r.firm_value)}
            </div>
            <div style="font-size:0.75rem; color:#7a7f9a; margin-top:0.2rem;">
                Firm Value
            </div>
            <hr style="margin:0.7rem 0; border-color:#2a2e3e;">
            <div style="font-size:0.8rem;">
                <span style="color:#7a7f9a;">Intrinsic / Share:</span>
                <strong style="color:var(--text);">{price_str}</strong>
            </div>
            <div style="font-size:0.8rem; margin-top:0.3rem;">
                <span style="color:#7a7f9a;">Upside:</span>
                <strong style="color:{'#00d4aa' if r.upside_pct and r.upside_pct > 0 else '#f75050'};">
                    {upside_str}
                </strong>
            </div>
            <div style="font-size:0.8rem; margin-top:0.3rem;">
                <span style="color:#7a7f9a;">Margin of Safety:</span>
                <strong>{mos_str}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # FCF Projection Chart (Base Case)
    st.markdown("##### 📈 Base Case FCF Projection")
    base_result = scenarios["Base"]
    proj_years  = list(range(1, projection_years + 1))

    fig2, ax2 = plt.subplots(figsize=(9, 3.5))
    fig2.patch.set_facecolor("#1a1d26")
    ax2.set_facecolor("#1a1d26")

    # Historical FCF (most recent 4 years, reversed)
    hist_vals = list(reversed(fcf_series.dropna().values[:4]))
    hist_yrs  = [f"Y-{len(hist_vals)-i}" for i in range(len(hist_vals))]
    hist_yrs[-1] = "Y0 (LTM)"

    proj_vals = [v / 1e9 for v in base_result.fcf_projections]
    proj_yrs  = [f"Y+{y}" for y in proj_years]

    all_labels = hist_yrs + proj_yrs
    all_vals   = [v / 1e9 for v in hist_vals] + proj_vals
    bar_colors = ["#4f8ef7"] * len(hist_vals) + ["#00d4aa"] * len(proj_vals)

    ax2.bar(all_labels, all_vals, color=bar_colors, alpha=0.8, edgecolor="none", width=0.6)
    ax2.axvline(x=len(hist_vals) - 0.5, color="#2a2e3e", linewidth=1.5, linestyle="--")
    ax2.text(len(hist_vals) - 0.5, max(all_vals) * 0.92,
             " Projection →", color="#7a7f9a", fontsize=8)
    ax2.set_ylabel("FCF ($ Billions)", color="#7a7f9a", fontsize=9)
    ax2.tick_params(colors="#7a7f9a", labelsize=8)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.1f}B"))
    for spine in ax2.spines.values():
        spine.set_color("#2a2e3e")
    plt.tight_layout()
    st.pyplot(fig2)
    plt.close()

    # ── Claude AI Insight ─────────────────────────────────────────────────────
    st.markdown("""
    <div class="section-header"><h2>🤖 Claude AI Analysis</h2></div>
    """, unsafe_allow_html=True)

    if not api_key:
        st.info(
            "💡 Add your **Anthropic API key** in the sidebar to enable AI-powered "
            "investment analysis from Claude."
        )
    else:
        with st.spinner("Claude is analyzing your valuation..."):
            insight = generate_insight(
                ticker=ticker,
                firm_value=scenarios["Base"].firm_value,
                fcf=latest_fcf,
                scenarios=scenarios,
                metrics=metrics,
                red_flags=debug["red_flags"],
                api_key=api_key,
            )

        st.markdown(
            f"""
            <div style="background:#1a1d26; border:1px solid #2a2e3e; border-radius:12px;
                        padding:1.5rem 2rem; line-height:1.8; font-size:0.92rem;">
            {insight.replace(chr(10), '<br>')}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Raw Statements (expandable) ───────────────────────────────────────────
    st.markdown("---")
    with st.expander("📂 Raw Financial Statements", expanded=False):
        tab1, tab2, tab3 = st.tabs(["Cash Flow", "Income Statement", "Balance Sheet"])
        with tab1:
            if data["cashflow"] is not None:
                st.dataframe(data["cashflow"].fillna("—"), use_container_width=True)
        with tab2:
            if data["income"] is not None:
                st.dataframe(data["income"].fillna("—"), use_container_width=True)
        with tab3:
            if data["balance"] is not None:
                st.dataframe(data["balance"].fillna("—"), use_container_width=True)

    # ── Model Assumptions Summary ─────────────────────────────────────────────
    with st.expander("⚙️ Model Assumptions Used", expanded=False):
        st.markdown(f"""
        | Parameter | Value |
        |---|---|
        | Discount Rate (WACC) | `{discount_rate:.1%}` |
        | Terminal Growth Rate | `{terminal_growth:.1%}` |
        | Projection Horizon | `{projection_years} years` |
        | Bear Growth Rate | `2.0%` |
        | Base Growth Rate | `5.0%` |
        | Bull Growth Rate | `10.0%` |
        | Base FCF Used | `{format_value(latest_fcf)}` |
        | Shares Outstanding | `{format_value(shares) if shares else 'N/A'}` |
        | Market Price | `${price:.2f}` if price else `N/A` |
        """)

# ─── Welcome State ────────────────────────────────────────────────────────────

elif not analyze:
    st.markdown("""
    <br>
    <div style="text-align:center; padding: 3rem 1rem; color: #7a7f9a;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">📊</div>
        <div style="font-family: 'DM Serif Display', serif; font-size: 1.4rem;
                    color: #e8eaf0; margin-bottom: 0.8rem;">
            Enter a stock ticker to begin
        </div>
        <div style="font-size: 0.88rem; max-width: 480px; margin: 0 auto; line-height: 1.7;">
            Combines <strong style="color:#00d4aa">real-time Yahoo Finance data</strong>,
            a <strong style="color:#4f8ef7">Discounted Cash Flow model</strong>,
            and <strong style="color:#f0c040">Claude AI</strong> to generate
            professional valuation insights.
        </div>
        <br>
        <div style="font-size: 0.8rem; color: #4a4f6a;">
            Try: AAPL · MSFT · GOOGL · AMZN · TSLA · META · NVDA
        </div>
    </div>
    """, unsafe_allow_html=True)
