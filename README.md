# NG Finance Pro 📊

**Quantitative financial intelligence and decision-support platform for finance teams, treasury professionals and quantitative-finance research.**

NG Finance Pro brings market data, accounting analytics, treasury monitoring, reconciliation, budgeting and quantitative risk modelling into one Streamlit workspace. The application is designed to operate in zero-cost mode without paid APIs; optional AI and news integrations can be enabled later.

## Current capabilities

### Finance operations
- CSV/XLSX finance-data ingestion with canonical schema normalization
- Explainable dataset classification for bank statements, general ledgers, budgets, transactions and financial statements
- Data-quality validation, duplicate detection and missing-date checks
- Bank reconciliation with configurable date tolerance
- Budget-versus-actual variance analysis
- Financial statement analysis and core liquidity, profitability and solvency ratios
- Management and executive reporting
- Treasury cash runway and liquidity monitoring

### Market and risk analytics
- Market monitoring for USD/NGN, BTC/USD, ETH/USD, gold and crude oil
- Historical, parametric-normal and Monte Carlo VaR/Expected Shortfall
- Maximum drawdown, downside volatility and stress scenarios
- Rolling historical VaR backtesting
- Kupiec proportion-of-failures testing
- Christoffersen independence and conditional-coverage testing
- GARCH(1,1) Gaussian QMLE volatility modelling and one-step forecasting
- EWMA volatility benchmark
- Portfolio correlation, component risk, minimum-variance optimization and walk-forward validation
- Liquidity runway, liquidity stress and USD/NGN FX exposure stress
- Research and backtesting workflows for out-of-sample evaluation and reproducibility
- ML-based volatility-regime experiments

### Intelligence layer
- Deterministic market-intelligence signals with transparent thresholds
- Optional OpenAI analyst integration
- Rule-based fallback when no OpenAI API key is configured
- Optional NewsAPI integration with graceful failure when no key is supplied

## Research orientation

NG Finance Pro is structured as more than a dashboard. Its quantitative layer supports reproducible empirical research through explicit assumptions, train/test or walk-forward evaluation, model comparison, stress testing and statistical validation.

A suitable MScFE research direction is:

> **Development and Evaluation of a Quantitative Financial Intelligence System for Market Risk, Liquidity Risk and Decision Support in Emerging Markets**

The research layer can compare historical, parametric, Monte Carlo, EWMA and GARCH volatility/risk approaches and evaluate forecasts out of sample. Nigeria/emerging-market instruments can be compared with global assets without fabricating local observations.

## Data principles

The platform does not fabricate Nigerian financial observations. Analytics consume data supplied by the caller or retrieved from configured market/news services. Scenario shocks and heuristic management thresholds are explicitly labelled as assumptions rather than historical facts.

## Input formats

### General finance data

CSV/XLSX files can contain common headers such as:

```text
Transaction Date,GL Account,Narration,Debit,Credit,Currency,Reference
2026-01-02,Cash,Customer receipt,0,150000,NGN,TX001
```

The Finance Data Workspace maps common headers into the canonical schema:

`date, account, description, debit, credit, amount, currency, category, reference, entity`

### Bank reconciliation

Bank and cashbook files should contain identifiable date and amount fields. Description, narration and reference fields are supported. Matching uses transaction amounts and configurable date tolerance.

### Budget analysis

```text
Department,Budget,Actual
Finance,5000000,4500000
HR,3000000,3500000
Operations,8000000,7600000
```

## Architecture

```text
NG Finance Pro
│
├── app.py                         Application shell and navigation
├── config/                        Configuration and market symbols
├── services/                      External data services
│   ├── market_data.py
│   ├── news_service.py
│   └── ai_service.py
│
├── analytics/                     Quantitative and accounting engines
│   ├── finance_data.py            Ingestion, classification, validation
│   ├── ratios.py
│   ├── financial_health.py
│   ├── reconciliation.py
│   ├── quant_risk.py              VaR, ES, drawdown, stress
│   ├── var_backtesting.py         Formal VaR validation
│   ├── garch.py                   GARCH/EWMA volatility
│   ├── portfolio_risk.py          Portfolio risk and optimization
│   ├── liquidity_fx.py            Liquidity and FX risk
│   ├── backtesting.py             OOS strategy validation
│   ├── ml_regime.py               ML regime experiments
│   └── ...
│
├── pages/                         Streamlit analytical workspaces
├── tests/                         Automated quantitative/unit tests
├── docs/                          Research and methodology documentation
└── .github/workflows/ci.yml       Continuous integration
```

## Technology stack

- Python 3.11
- Streamlit
- Pandas / NumPy
- SciPy / scikit-learn
- Plotly
- yFinance
- OpenPyXL
- Pytest
- GitHub Actions
- OpenAI API — optional
- NewsAPI — optional

## Cost model

The core application is designed to remain functional without paid APIs. OpenAI and NewsAPI credentials are optional enhancements, not runtime requirements for the core finance and quantitative workflows.

## Quality and reproducibility

The repository uses automated tests through GitHub Actions. Quantitative modules include deterministic tests where randomness is involved, explicit parameterization, and methodology documentation. Formal VaR validation uses one-step-ahead rolling forecasts to reduce look-ahead bias.

## Development roadmap

1. **Research-grade risk validation** — expand rolling forecast comparisons across Historical VaR, EWMA and GARCH.
2. **Emerging-market empirical layer** — compare Nigeria-focused and global instruments using consistent metrics.
3. **Forecast evaluation** — add forecast-error, coverage, calibration and stability diagnostics where statistically appropriate.
4. **Finance operating layer** — strengthen persistent finance-data workflows, audit trails and management reporting.
5. **Decision intelligence** — connect validated quantitative signals to transparent management actions rather than opaque recommendations.

## Author

**Gbenga Olufisayo**  
Accountant | Treasury Professional | Financial Engineering Enthusiast

## Live application

urlNG Finance Pro Streamlit applicationhttps://nigeria-finance-dashboard-5brcqb4w4rsryneyh4tyeq.streamlit.app/
