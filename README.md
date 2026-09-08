# NG Finance Pro 📈

## Overview

NG Finance Pro is a Streamlit-based financial intelligence and treasury decision-support platform for accountants, treasury professionals, finance managers and analysts.

The project combines Nigerian market monitoring, treasury analytics, budget variance analysis, bank reconciliation, financial statement ratios and an optional AI analyst into one application.

## Version 2.1 Upgrade

The repository has been upgraded from a monolithic MVP into a modular architecture with separate configuration, services, analytics and UI layers.

### What is now implemented

- Live market snapshot for USD/NGN, BTC, ETH, gold and crude oil through yFinance
- Cached market-data service with graceful failure handling
- Financial news terminal with optional NewsAPI integration
- Optional OpenAI financial analyst with a rule-based fallback when no API key is configured
- Interactive treasury dashboard with adjusted available cash and estimated cash runway
- Real one-to-one bank reconciliation using amount matching and configurable date tolerance
- Budget vs actual upload and variance analysis
- Financial statement analyzer for standardized CSV/XLSX extracts
- Core liquidity, profitability, solvency and cash-flow ratios
- Financial health score from 0–100 across five dimensions
- Market-derived volatility risk indicators
- Automated unit tests and GitHub Actions CI

## Financial Statement Input Format

Upload CSV or XLSX files with two columns such as:

```text
Account,Amount
Cash & Cash Equivalents,100000000
Current Assets,250000000
Current Liabilities,150000000
Total Assets,600000000
Total Liabilities,250000000
Total Equity,350000000
Total Debt,120000000
```

The analyzer supports Balance Sheet, Income Statement and Cash Flow extracts. The line-item names should match the items shown in the application for the most complete ratio coverage.

## Bank Reconciliation Input Format

Each file should contain identifiable Date and Amount columns. Optional description/narration/reference columns are also supported. The engine matches each bank transaction to at most one cashbook transaction using amount equality to two decimal places and a configurable date tolerance.

## Budget Input Format

CSV/XLSX files should contain:

```text
Department,Budget,Actual
Finance,5000000,4500000
HR,3000000,3500000
Operations,8000000,7600000
```

## Configuration

For Streamlit Cloud, add secrets for:

```toml
NEWS_API_KEY = "your-newsapi-key"
OPENAI_API_KEY = "your-openai-api-key"
```

`OPENAI_API_KEY` is optional. Without it, the application uses a deterministic rule-based analyst rather than pretending that static text is AI-generated.

## Architecture

```text
NG Finance Pro
├── app.py
├── config/
│   └── settings.py
├── services/
│   ├── market_data.py
│   ├── news_service.py
│   └── ai_service.py
├── analytics/
│   ├── ratios.py
│   ├── financial_health.py
│   └── reconciliation.py
├── pages/
│   ├── dashboard.py
│   ├── markets.py
│   ├── risk.py
│   ├── treasury.py
│   ├── reconciliation.py
│   ├── budget.py
│   └── financial_statements.py
└── tests/
    └── test_analytics.py
```

## Technology Stack

- Python 3.11
- Streamlit
- Pandas
- Plotly
- yFinance
- OpenAI API (optional)
- NewsAPI (optional)
- OpenPyXL
- Pytest
- GitHub Actions

## Roadmap

### V2.2 — Data & Persistence
- SQLite/PostgreSQL database layer
- Company and user records
- Persistent treasury transactions
- Audit trail

### V2.3 — Treasury Intelligence
- Cash-flow forecasting
- Liquidity stress testing
- Cash concentration analysis
- Bank/account-level treasury reporting

### V2.4 — Advanced Financial Analytics
- PDF annual-report extraction
- Multi-period ratio trends
- Peer/company comparison
- Valuation models
- Credit-risk indicators

### V2.5 — Investment & AI Research
- Structured investment research assistant
- Nigerian listed-company screening
- Portfolio analytics
- Explainable AI research summaries

## Author

Gbenga Olufisayo

Accountant | Treasury Professional | Financial Engineering Enthusiast

## Live Application

https://nigeria-finance-dashboard-5brcqb4w4rsryneyh4tyeq.streamlit.app/
