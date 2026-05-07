"""
app.py — AI-Powered Valuation Assistant (FMP + Claude)
=======================================================
Run:  streamlit run app.py
Data: Financial Modeling Prep (FMP) — free at financialmodelingprep.com
AI:   Anthropic Claude API         — free at console.anthropic.com
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from src.data_loader import load_financials, get_key_metrics
from src.cashflow    import compute_free_cash_flow
from src.dcf         import run_scenarios, format_value
from src.claude_ai   import generate_insight

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
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@300;400;500;600&display=swap');
:root{--bg:#0f1117;--surface:#1a1d26;--border:#2a2e3e;--accent:#00d4aa;--accent2:#4f8ef7;--danger:#f75050;--warn:#f7a650;--text:#e8eaf0;--muted:#7a7f9a;}
html,body,[class*="css"]{font-family:'Inter',sans-serif;background:var(--bg)!important;color:var(--text)!important;}
.main-header{background:linear-gradient(135deg,#0f1117 0%,#1a1d26 50%,#0f1117 100%);border-bottom:1px solid var(--border);padding:2rem 0 1.5rem;text-align:center;}
.main-header h1{font-family:'DM Serif Display',serif;font-size:2.6rem;color:var(--text);margin:0;}
.main-header .sub{font-size:.85rem;color:var(--muted);letter-spacing:2px;text-transform:uppercase;margin-top:.4rem;}
.metric-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1rem 1.2rem;text-align:center;}
.metric-card:hover{border-color:var(--accent);}
.metric-card .label{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:.3rem;}
.metric-card .value{font-family:'IBM Plex Mono',monospace;font-size:1.4rem;font-weight:500;color:var(--accent);}
.section-header{border-left:3px solid var(--accent);padding-left:.8rem;margin:2rem 0 1rem;}
.section-header h2{font-family:'DM Serif Display',serif;font-size:1.4rem;color:var(--text);margin:0;}
.scenario-bear{border-color:var(--danger)!important;} .scenario-base{border-color:var(--accent2)!important;} .scenario-bull{border-color:var(--accent)!important;}
.red-flag{background:rgba(247,80,80,.08);border:1px solid rgba(247,80,80,.3);border-radius:8px;padding:.6rem 1rem;margin:.4rem 0;font-size:.85rem;color:#f75050;}
.info-tag{display:inline-block;background:rgba(79,142,247,.1);border:1px solid rgba(79,142,247,.3);border-radius:20px;padding:.15rem .7rem;font-size:.75rem;color:var(--accent2);margin-right:.4rem;margin-bottom:.3rem;}
[data-testid="stSidebar"]{background:var(--surface)!important;border-right:1px solid var(--border)!important;}
.stTextInput input,.stNumberInput input{background:#0f1117!important;border:1px solid var(--border)!important;color:var(--text)!important;border-radius:6px!important;}
.stButton>button{background:var(--accent)!important;color:#0f1117!important;font-weight:600!important;border:none!important;border-radius:6px!important;padding:.5rem 1.5rem!important;}
hr{border-color:var(--border)!important;margin:1.5rem 0!important;}
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

    # FMP API Key
    st.markdown("**📈 Financial Data API Key**")
    st.caption("Free key at [financialmodelingprep.com](https://financialmodelingprep.com)")
    fmp_key = st.text_input(
        "FMP API Key", type="password",
        placeholder="Enter your FMP key…",
        label_visibility="collapsed",
    )
    if fmp_key:
        st.success("✅ FMP key configured")
    else:
        st.warning("⚠️ Required for financial data")

    st.markdown("---")

    # Claude API Key
    st.markdown("**🤖 Claude AI API Key**")
    st.caption("Free key at [console.anthropic.com](https://console.anthropic.com)")
    claude_key = st.text_input(
        "Claude API Key", type="password",
        placeholder="sk-ant-…",
        label_visibility="collapsed",
    )
    if claude_key:
        st.success("✅ Claude key configured")
    else:
        st.info("Optional — enables AI analysis")

    st.markdown("---")
    st.markdown("**📐 DCF Parameters**")
    discount_rate    = st.slider("Discount Rate (WACC)", 0.06, 0.20, 0.10, 0.01, format="%.0f%%")
    terminal_growth  = st.slider("Terminal Growth Rate", 0.01, 0.05, 0.025, 0.005, format="%.1f%%")
    projection_years = st.slider("Projection Horizon (years)", 3, 10, 5)

    st.markdown("---")
    st.caption("Not financial advice. Apply human judgment to all outputs.")

# ─── Main Input ───────────────────────────────────────────────────────────────

col_input, col_btn = st.columns([4, 1])
with col_input:
    ticker = st.text_input(
        "Ticker", placeholder="e.g.  AAPL  ·  MSFT  ·  GOOGL  ·  AMZN  ·  TSLA",
        label_visibility="collapsed",
    )
with col_btn:
    analyze = st.button("🔍 Analyze", use_container_width=True)

# ─── Analysis Pipeline ────────────────────────────────────────────────────────

if ticker and analyze:
    ticker = ticker.strip().upper()

    if not fmp_key:
        st.error("❌ Please enter your FMP API key in the sidebar to fetch financial data.")
        st.stop()

    with st.spinner(f"Fetching financial data for **{ticker}** from Financial Modeling Prep…"):
        data = load_financials(ticker, fmp_key)

    if data["error"]:
        st.error(f"❌ {data['error']}")
        st.stop()

    metrics = get_key_metrics(data["profile"], data["metrics"])
    company_name = metrics.get("company_name", ticker)

    # ── Company Header ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="margin:1.5rem 0 .5rem">
        <span class="info-tag">{metrics.get('exchange','')}</span>
        <span class="info-tag">{metrics.get('sector','N/A')}</span>
        <span class="info-tag">{metrics.get('industry','N/A')}</span>
        <span class="info-tag">{metrics.get('country','N/A')}</span>
    </div>
    <h2 style="font-family:'DM Serif Display',serif;font-size:2rem;margin:0 0 1.5rem">
        {company_name}
        <span style="color:#7a7f9a;font-size:1rem;">({ticker})</span>
    </h2>
    """, unsafe_allow_html=True)

    # ── Key Market Metrics ────────────────────────────────────────────────────
    def fmt(val, mode="plain", prefix=""):
        if val is None: return "N/A"
        try:
            if mode == "pct":   return f"{float(val):.1%}"
            if mode == "large": return format_value(float(val))
            if mode == "2f":    return f"{prefix}{float(val):.2f}"
            return str(val)
        except: return "N/A"

    cols = st.columns(6)
    cards = [
        ("Market Cap",    fmt(metrics.get("market_cap"), "large"),          ""),
        ("Current Price", fmt(metrics.get("current_price"), "2f", "$"),     ""),
        ("P/E Ratio",     fmt(metrics.get("pe_ratio"), "2f"),                ""),
        ("EV/EBITDA",     fmt(metrics.get("ev_ebitda"), "2f"),               ""),
        ("Profit Margin", fmt(metrics.get("profit_margin"), "pct"),          ""),
        ("Beta",          fmt(metrics.get("beta"), "2f"),                    ""),
    ]
    for col, (label, value, sub) in zip(cols, cards):
        col.markdown(f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
            <div style="font-size:.7rem;color:#7a7f9a;">{sub}</div>
        </div>""", unsafe_allow_html=True)

    # ── Cash Flow Analysis ────────────────────────────────────────────────────
    st.markdown('<div class="section-header"><h2>💧 Cash Flow Analysis</h2></div>', unsafe_allow_html=True)

    if not data["cashflow"]:
        st.error("Cash flow statement unavailable for this ticker.")
        st.stop()

    fcf_series, debug = compute_free_cash_flow(data["cashflow"])

    with st.expander("🔧 Debug Info", expanded=False):
        st.write(f"**OCF field:** `{debug['ocf_key_used']}`")
        st.write(f"**CapEx field:** `{debug['capex_key_used']}`")
        if debug["warnings"]:
            for w in debug["warnings"]: st.warning(w)

    if debug["red_flags"]:
        st.markdown("**⚠️ Red Flags:**")
        for flag in debug["red_flags"]:
            st.markdown(f'<div class="red-flag">{flag}</div>', unsafe_allow_html=True)

    if fcf_series is None:
        st.error("Could not compute Free Cash Flow.")
        st.stop()

    # FCF Table
    fcf_df = pd.DataFrame({
        "Fiscal Year": fcf_series.index,
        "FCF":         [format_value(v) for v in fcf_series.values],
        "Raw ($)":     [f"${v:,.0f}" for v in fcf_series.values],
    }).set_index("Fiscal Year")
    st.dataframe(fcf_df, use_container_width=True)

    # FCF Bar Chart
    fig, ax = plt.subplots(figsize=(9, 3.5))
    fig.patch.set_facecolor("#1a1d26"); ax.set_facecolor("#1a1d26")
    colors = ["#00d4aa" if v >= 0 else "#f75050" for v in fcf_series.values]
    bars = ax.bar(fcf_series.index, fcf_series.values / 1e9, color=colors, width=0.6, alpha=0.85, edgecolor="none")
    ax.axhline(0, color="#2a2e3e", linewidth=1)
    ax.set_ylabel("FCF ($ Billions)", color="#7a7f9a", fontsize=9)
    ax.tick_params(colors="#7a7f9a", labelsize=8)
    [s.set_color("#2a2e3e") for s in ax.spines.values()]
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.1f}B"))
    for bar, val in zip(bars, fcf_series.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + abs(max(fcf_series.values)/1e9)*0.02,
                format_value(val), ha="center", va="bottom", color="#e8eaf0", fontsize=8)
    plt.tight_layout(); st.pyplot(fig); plt.close()

    # ── DCF Valuation ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-header"><h2>🏦 DCF Valuation — Scenario Analysis</h2></div>', unsafe_allow_html=True)

    latest_fcf = next((float(v) for v in fcf_series.values if v and v != 0), None)
    if latest_fcf is None:
        st.error("All FCF values are zero or NaN — cannot run DCF.")
        st.stop()

    shares = metrics.get("shares_outstanding")
    price  = metrics.get("current_price")

    try:
        scenarios = run_scenarios(
            fcf=latest_fcf, discount_rate=discount_rate,
            years=projection_years, terminal_growth=terminal_growth,
            shares_outstanding=shares, current_price=price,
        )
    except ValueError as e:
        st.error(f"DCF Error: {e}"); st.stop()

    # Scenario Cards
    s_cols = st.columns(3)
    for col, (name, emoji, cls) in zip(s_cols, [
        ("Bear","🐻","scenario-bear"), ("Base","⚖️","scenario-base"), ("Bull","🚀","scenario-bull")
    ]):
        r = scenarios[name]
        upside_color = "#00d4aa" if r.upside_pct and r.upside_pct > 0 else "#f75050"
        col.markdown(f"""
        <div class="metric-card {cls}" style="padding:1.2rem;">
            <div class="label" style="font-size:.8rem;font-weight:600;">{emoji} {name} CASE</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:1.3rem;color:var(--text);margin:.5rem 0;">
                {format_value(r.firm_value)}
            </div>
            <div style="font-size:.75rem;color:#7a7f9a;">Firm Value</div>
            <hr style="margin:.7rem 0;border-color:#2a2e3e;">
            <div style="font-size:.8rem;">
                <span style="color:#7a7f9a;">Intrinsic/Share: </span>
                <strong>{"$"+f"{r.intrinsic_value_per_share:.2f}" if r.intrinsic_value_per_share else "N/A"}</strong>
            </div>
            <div style="font-size:.8rem;margin-top:.3rem;">
                <span style="color:#7a7f9a;">Upside: </span>
                <strong style="color:{upside_color};">{f"{r.upside_pct:+.1f}%" if r.upside_pct else "N/A"}</strong>
            </div>
            <div style="font-size:.8rem;margin-top:.3rem;">
                <span style="color:#7a7f9a;">Margin of Safety: </span>
                <strong>{f"{r.margin_of_safety:.1%}" if r.margin_of_safety else "N/A"}</strong>
            </div>
        </div>""", unsafe_allow_html=True)

    # ── Claude AI Insight ─────────────────────────────────────────────────────
    st.markdown('<div class="section-header"><h2>🤖 Claude AI Analysis</h2></div>', unsafe_allow_html=True)

    if not claude_key:
        st.info("💡 Add your **Anthropic API key** in the sidebar to enable AI-powered investment analysis.")
    else:
        with st.spinner("Claude is analysing the valuation…"):
            insight = generate_insight(
                ticker=ticker, firm_value=scenarios["Base"].firm_value,
                fcf=latest_fcf, scenarios=scenarios,
                metrics=metrics, red_flags=debug["red_flags"],
                api_key=claude_key,
            )
        st.markdown(f"""
        <div style="background:#1a1d26;border:1px solid #2a2e3e;border-radius:12px;
                    padding:1.5rem 2rem;line-height:1.8;font-size:.92rem;">
            {insight.replace(chr(10),'<br>')}
        </div>""", unsafe_allow_html=True)

    # ── Raw Statements ────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📂 Raw Financial Statements", expanded=False):
        tab1, tab2, tab3 = st.tabs(["Cash Flow", "Income Statement", "Balance Sheet"])
        with tab1:
            if data["cashflow"]:
                st.dataframe(pd.DataFrame(data["cashflow"]), use_container_width=True)
        with tab2:
            if data["income"]:
                st.dataframe(pd.DataFrame(data["income"]), use_container_width=True)
        with tab3:
            if data["balance"]:
                st.dataframe(pd.DataFrame(data["balance"]), use_container_width=True)

    with st.expander("⚙️ Model Assumptions", expanded=False):
        st.markdown(f"""
        | Parameter | Value |
        |---|---|
        | Discount Rate (WACC) | `{discount_rate:.1%}` |
        | Terminal Growth Rate | `{terminal_growth:.1%}` |
        | Projection Horizon   | `{projection_years} years` |
        | Base FCF Used        | `{format_value(latest_fcf)}` |
        | Shares Outstanding   | `{format_value(shares) if shares else "N/A"}` |
        | Market Price         | `{"$"+str(price) if price else "N/A"}` |
        """)

# ─── Welcome State ────────────────────────────────────────────────────────────
elif not analyze:
    st.markdown("""
    <br>
    <div style="text-align:center;padding:3rem 1rem;color:#7a7f9a;">
        <div style="font-size:3rem;margin-bottom:1rem;">📊</div>
        <div style="font-family:'DM Serif Display',serif;font-size:1.4rem;color:#e8eaf0;margin-bottom:.8rem;">
            Enter a stock ticker to begin
        </div>
        <div style="font-size:.88rem;max-width:480px;margin:0 auto;line-height:1.7;">
            Powered by <strong style="color:#00d4aa">Financial Modeling Prep</strong> data,
            a <strong style="color:#4f8ef7">DCF valuation engine</strong>,
            and <strong style="color:#f0c040">Claude AI</strong>.
        </div>
        <br>
        <div style="font-size:.8rem;color:#4a4f6a;">
            ① Enter your FMP key in the sidebar &nbsp;·&nbsp;
            ② Enter a ticker &nbsp;·&nbsp;
            ③ Click Analyze
        </div>
        <br>
        <div style="font-size:.8rem;color:#4a4f6a;">Try: AAPL · MSFT · GOOGL · AMZN · TSLA · META · NVDA</div>
    </div>
    """, unsafe_allow_html=True)
