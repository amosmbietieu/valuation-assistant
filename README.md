# 📊 AI-Powered Valuation Assistant

> **Assignment 4 — AI for Finance | Tier B Submission**
> A production-grade financial valuation tool combining real market data, a DCF model, and Claude AI.

---

## 🎯 What This Tool Does

This application implements a complete **end-to-end equity valuation workflow**:

1. **Fetches real financial data** from Yahoo Finance (Cash Flow, Income Statement, Balance Sheet, market metadata)
2. **Computes Free Cash Flow** using a robust, multi-key fallback parser (handles Yahoo Finance naming inconsistencies)
3. **Runs a 3-scenario DCF model** (Bear / Base / Bull) with terminal value and per-share intrinsic value
4. **Detects cash flow red flags** automatically (negative FCF, deteriorating trends, CapEx pressure)
5. **Sends structured financial context to Claude AI** for professional investment analysis

---

## 🏗️ Architecture

```
valuation_assistant/
│
├── app.py                  ← Streamlit UI (main entry point)
├── requirements.txt        ← Python dependencies
├── README.md               ← This file
│
└── src/
    ├── __init__.py
    ├── data_loader.py      ← Yahoo Finance fetcher + key metrics extraction
    ├── cashflow.py         ← OCF / CapEx / FCF computation with red flag detection
    ├── dcf.py              ← DCF model: projections, terminal value, scenarios
    └── claude_ai.py        ← Anthropic API integration with structured prompt
```

---

## ⚙️ Installation & Setup

### 1. Clone / download the project
```bash
git clone <your-repo> valuation_assistant
cd valuation_assistant
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Get your Claude API Key
- Create an account at [console.anthropic.com](https://console.anthropic.com)
- Generate an API key
- Enter it in the app's sidebar (no `.env` file needed)

### 5. Run the app
```bash
streamlit run app.py
```
Open your browser at **http://localhost:8501**

---

## 🧮 Financial Model — Technical Details

### Free Cash Flow Formula
```
FCF = Operating Cash Flow (OCF) − Capital Expenditures (CapEx)
```
> Note: Yahoo Finance reports CapEx as a **negative** number, so the implementation
> uses `FCF = OCF + CapEx (signed)` which is mathematically equivalent.

### DCF Formula
```
         FCF₁        FCF₂                FCFₙ        Terminal Value
Value = ——————— + ——————————— + ... + —————————— + ——————————————————
        (1+r)¹    (1+r)²              (1+r)ⁿ          (1+r)ⁿ

Terminal Value = FCFₙ × (1+g) / (r − g)      [Gordon Growth Model]
```

### Scenario Parameters
| Scenario | FCF Growth | WACC Adjustment |
|---|---|---|
| 🐻 Bear | 2% | WACC + 2% |
| ⚖️ Base | 5% | WACC (as set) |
| 🚀 Bull | 10% | WACC − 1% |

---

## ⚠️ Limitations & Critical Notes

| Limitation | Impact |
|---|---|
| Yahoo Finance data quality | Occasional missing / renamed fields (handled by fallback logic) |
| DCF sensitivity | Small changes in WACC or terminal growth → large valuation swings |
| AI output is probabilistic | Claude's analysis must be validated by human judgment |
| No macro scenarios | Model cannot anticipate recessions, rate shocks, or black swans |
| Historical FCF ≠ future FCF | Past cash generation is not a guarantee of future performance |
| No debt adjustment | Firm value ≠ equity value; ideally subtract net debt for equity value |

> **This tool is for educational purposes only. It does not constitute financial advice.**

---

## 🔑 Key Financial Concepts Implemented

- **Cash Flow vs Net Income** — why FCF is more reliable for valuation
- **Operating / Investing / Financing Cash Flows** — full statement parsing
- **Free Cash Flow** — OCF minus CapEx
- **Discounted Cash Flow** — time value of money applied to future FCF
- **Terminal Value** — Gordon Growth Model for perpetuity
- **Margin of Safety** — difference between intrinsic and market value
- **Red Flag Detection** — automated warnings for deteriorating cash flows
- **AI Auditing** — Claude assesses earnings quality and identifies risks

---

## 👨‍💻 Tech Stack

- **Python 3.10+**
- **Streamlit** — interactive web UI
- **yfinance** — real-time Yahoo Finance data
- **pandas / numpy** — financial data processing
- **matplotlib** — charts and visualizations
- **Anthropic Claude API** — AI-powered analysis

---

## 📝 Submission Notes

This project demonstrates mastery of all Assignment 4 objectives:
- ✅ Cash flow interpretation (OCF, CapEx, FCF, red flags)
- ✅ DCF model with real inputs and assumptions
- ✅ AI tools for financial forecasting (Claude API integration)
- ✅ End-to-end valuation workflow
- ✅ Critical assessment of model limitations
