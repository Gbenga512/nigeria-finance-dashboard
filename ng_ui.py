import streamlit as st

WORKSPACES = [
    "📊  Dashboard", "🏢  SME Finance Department", "👤  Personal Finance", "💳  Personal Accounts",
    "🔁  Recurring Finance", "🏦  SME Bank Statements", "📚  SME Accounting & Statements",
    "📘  SME Management Accounts", "👥  Customers & Suppliers", "🧠  Intelligence Centre",
    "🎯  Integrated Risk Command Centre", "📁  Finance Data Workspace", "🧾  Financial Data Controls",
    "🧪  Quant Lab", "🔬  Research & Backtesting", "🌍  Emerging Markets Research",
    "📉  GARCH Volatility Lab", "💱  Liquidity & FX Risk", "🛡️  Risk Robustness Lab",
    "📈  Markets", "🤖  AI Insights", "🛡️  Risk Monitor", "📐  Portfolio Risk",
    "📰  News Terminal", "💧  Treasury Dashboard", "↔️  Bank Reconciliation",
    "📑  Budget Analysis", "📋  Financial Statement Analyzer", "📄  Executive Reports",
]


def inject_styles() -> None:
    st.markdown(
        """<style>
        :root{--ng-bg:#060d18;--ng-panel:#0b1625;--ng-panel2:#0f1d2e;--ng-border:rgba(148,163,184,.13);--ng-text:#f5f7fb;--ng-muted:#8293a8;--ng-blue:#5aa9ff;--ng-teal:#35d6b0;--ng-amber:#f2c35b;--ng-red:#ff6b82}
        .stApp{background:radial-gradient(circle at 82% 0%,rgba(39,102,160,.13),transparent 28%),var(--ng-bg);color:var(--ng-text)}
        .block-container{max-width:1500px;padding-top:1.2rem;padding-bottom:3rem}
        [data-testid="stSidebar"]{background:#07111f;border-right:1px solid var(--ng-border)}
        [data-testid="stSidebar"]>div:first-child{padding-top:1.15rem}
        .ng-brand{display:flex;align-items:center;gap:11px;padding:5px 4px 20px}
        .ng-brand-mark{width:40px;height:40px;border-radius:12px;display:grid;place-items:center;background:linear-gradient(135deg,#4d9fff,#35d6b0);color:#06111e;font-weight:950;font-size:17px;box-shadow:0 8px 28px rgba(53,214,176,.14)}
        .ng-brand-name{color:var(--ng-text);font-weight:900;font-size:1.03rem;letter-spacing:.02em}.ng-brand-tag{color:#64778e;font-size:.61rem;letter-spacing:.12em;text-transform:uppercase;margin-top:3px}
        .ng-card{border:1px solid var(--ng-border);border-radius:16px;padding:17px;background:linear-gradient(145deg,rgba(15,29,46,.96),rgba(8,18,31,.96));box-shadow:0 12px 32px rgba(0,0,0,.12)}
        .ng-card-title,.ng-muted{color:var(--ng-muted)}.ng-card-title{font-size:.7rem;font-weight:800;letter-spacing:.07em;text-transform:uppercase}.ng-card-value{color:var(--ng-text);font-size:1.55rem;font-weight:850;margin:5px 0}
        .ng-positive{color:var(--ng-teal);font-weight:800}.ng-negative{color:var(--ng-red);font-weight:800}.ng-neutral{color:var(--ng-amber);font-weight:800}.ng-muted{font-size:.77rem}
        .ng-section-label{color:#63778f;font-size:.66rem;font-weight:850;letter-spacing:.15em;text-transform:uppercase;margin:25px 0 9px}
        .ng-footer{color:#50627a;font-size:.7rem;text-align:center;padding-top:24px}
        .ng-status{display:inline-flex;padding:5px 9px;border-radius:999px;background:rgba(53,214,176,.08);color:var(--ng-teal);border:1px solid rgba(53,214,176,.16);font-size:.68rem;font-weight:800}
        .ng-upgrade{margin-top:22px;padding:15px;border-radius:14px;border:1px solid rgba(90,169,255,.18);background:linear-gradient(145deg,rgba(37,89,137,.14),rgba(53,214,176,.04))}
        .ng-upgrade-title{color:var(--ng-text);font-weight:800;font-size:.84rem}.ng-upgrade-copy{color:#71859d;font-size:.69rem;margin-top:5px;line-height:1.5}
        .ng-hero{position:relative;overflow:hidden;padding:29px 31px;border:1px solid var(--ng-border);border-radius:21px;background:linear-gradient(135deg,rgba(15,34,55,.98),rgba(8,18,31,.98));margin-bottom:18px;box-shadow:0 20px 55px rgba(0,0,0,.16)}
        .ng-hero:after{content:"";position:absolute;width:260px;height:260px;border-radius:50%;right:-100px;top:-140px;background:rgba(90,169,255,.10);filter:blur(2px)}
        .ng-eyebrow{color:var(--ng-blue);font-size:.67rem;font-weight:850;letter-spacing:.16em;text-transform:uppercase;margin-bottom:7px}.ng-hero h1{font-size:2.35rem!important;letter-spacing:-.035em;margin-bottom:7px!important}.ng-subtitle{color:#95a7bb;font-size:.94rem;margin:0;max-width:800px;line-height:1.55}
        .ng-command{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:2px 0 15px;color:#8293a8;font-size:.75rem}
        .ng-command-kicker{color:#c8d3df;font-weight:700}.ng-live-dot{display:inline-flex;align-items:center;gap:6px}.ng-live-dot:before{content:"";width:7px;height:7px;border-radius:50%;background:var(--ng-teal);box-shadow:0 0 12px rgba(53,214,176,.65)}
        .ng-action{border:1px solid var(--ng-border);background:rgba(255,255,255,.025);border-radius:12px;padding:11px 13px;height:100%}.ng-action-title{color:#e7edf5;font-size:.82rem;font-weight:800}.ng-action-copy{color:#74879e;font-size:.69rem;line-height:1.4;margin-top:3px}
        .ng-alert{border-left:3px solid var(--ng-amber);padding:12px 14px;border-radius:10px;background:rgba(242,195,91,.055);margin-bottom:9px}.ng-alert-title{color:#eef2f7;font-weight:750;font-size:.82rem}.ng-alert-copy{color:#8293a8;font-size:.7rem;margin-top:3px}
        .ng-ticker{display:flex;gap:8px;overflow:hidden;margin:0 0 17px}.ng-ticker-item{min-width:145px;border:1px solid var(--ng-border);background:rgba(12,25,41,.78);border-radius:11px;padding:9px 11px}.ng-ticker-name{font-size:.67rem;color:#8497ad}.ng-ticker-price{font-size:.9rem;color:#f5f7fb;font-weight:800}.ng-ticker-change{font-size:.68rem;font-weight:800}
        .ng-kpi{min-height:105px}.ng-kpi .ng-card-value{font-size:1.42rem}.ng-kpi-meta{font-size:.69rem;color:#72869e}
        @media (max-width: 640px){
          .block-container{padding:1rem .7rem 2rem!important;max-width:100%!important}
          .ng-hero{padding:21px 17px;border-radius:16px}.ng-hero h1{font-size:1.9rem!important;line-height:1.08!important}.ng-subtitle{font-size:.86rem}
          .ng-card{padding:13px;border-radius:13px}.ng-card-value{font-size:1.25rem}.ng-section-label{margin-top:17px}
          div[data-testid="stHorizontalBlock"]{gap:.55rem!important}div[data-testid="stHorizontalBlock"]>div[data-testid="column"]{min-width:0!important}
          .stButton>button,.stDownloadButton>button{min-height:45px!important;font-size:.88rem!important}
          [data-testid="stDataFrame"]{max-width:100%;overflow-x:auto}.ng-command{align-items:flex-start;flex-direction:column}
        }
        </style>""",
        unsafe_allow_html=True,
    )


def brand() -> None:
    st.sidebar.markdown(
        '<div class="ng-brand"><div class="ng-brand-mark">NG</div><div><div class="ng-brand-name">NG FINANCE PRO</div><div class="ng-brand-tag">Financial intelligence system</div></div></div>',
        unsafe_allow_html=True,
    )


def workspace_navigator(current: str) -> None:
    st.markdown("### Workspace navigation")
    choices = [x for x in WORKSPACES if x != current]
    target = st.selectbox("Open module", choices, key="ng_mobile_nav")
    if st.button("Open selected module", key="ng_open_module", use_container_width=True):
        st.session_state["ng_nav_target"] = target
        st.rerun()


def hero(title: str, subtitle: str, status: str = "Live market feed") -> None:
    st.markdown(
        f'<div class="ng-hero"><div class="ng-eyebrow">NG Finance Pro / Executive workspace</div><h1>{title}</h1><p class="ng-subtitle">{subtitle}</p><div style="margin-top:14px"><span class="ng-status">● {status}</span></div></div>',
        unsafe_allow_html=True,
    )


def footer() -> None:
    st.markdown('<div class="ng-footer">NG Finance Pro • Financial Intelligence Platform • MVP v3.1 • Decision intelligence for finance teams</div>', unsafe_allow_html=True)
