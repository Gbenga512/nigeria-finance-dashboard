import streamlit as st

WORKSPACES = [
    "📊  Dashboard", "🏢  SME Finance Department", "🏦  SME Bank Statements",
    "📚  SME Accounting & Statements", "📘  SME Management Accounts",
    "🧠  Intelligence Centre", "🎯  Integrated Risk Command Centre",
    "📁  Finance Data Workspace", "🧾  Financial Data Controls", "🧪  Quant Lab",
    "🔬  Research & Backtesting", "🌍  Emerging Markets Research", "📉  GARCH Volatility Lab",
    "💱  Liquidity & FX Risk", "🛡️  Risk Robustness Lab", "📈  Markets", "🤖  AI Insights",
    "🛡️  Risk Monitor", "📐  Portfolio Risk", "📰  News Terminal", "💧  Treasury Dashboard",
    "↔️  Bank Reconciliation", "📑  Budget Analysis", "📋  Financial Statement Analyzer",
    "📄  Executive Reports",
]


def inject_styles() -> None:
    st.markdown('''<style>
    .stApp{background:#07111f}.ng-card{border:1px solid rgba(148,163,184,.14);border-radius:15px;padding:17px;background:rgba(13,25,41,.96)}
    .ng-card-title,.ng-muted{color:#91a4bb}.ng-card-title{font-size:.77rem;font-weight:750}.ng-card-value{color:#f7fafc;font-size:1.55rem;font-weight:850;margin:4px 0}
    .ng-positive{color:#2dd4a7;font-weight:750}.ng-negative{color:#ff647c;font-weight:750}.ng-neutral{color:#f4c95d;font-weight:750}.ng-muted{font-size:.78rem}
    .ng-section-label{color:#6f849c;font-size:.68rem;font-weight:850;letter-spacing:.13em;text-transform:uppercase;margin:22px 0 8px}.ng-footer{color:#53667d;font-size:.72rem;text-align:center;padding-top:20px}
    .ng-status{display:inline-flex;padding:6px 10px;border-radius:999px;background:rgba(45,212,167,.08);color:#2dd4a7;border:1px solid rgba(45,212,167,.16);font-size:.72rem;font-weight:800}
    .ng-upgrade{margin-top:22px;padding:15px;border-radius:13px;border:1px solid rgba(59,156,255,.2);background:rgba(59,156,255,.08)}.ng-upgrade-title{color:#f7fafc;font-weight:800;font-size:.85rem}.ng-upgrade-copy{color:#71869e;font-size:.7rem;margin-top:4px}
    .ng-brand{display:flex;align-items:center;gap:11px;padding:8px 4px 18px}.ng-brand-mark{width:38px;height:38px;border-radius:11px;display:grid;place-items:center;background:linear-gradient(135deg,#3b9cff,#2dd4a7);color:#06111e;font-weight:950;font-size:18px}.ng-brand-name{color:#f7fafc;font-weight:900;font-size:1.05rem}.ng-brand-tag{color:#61758d;font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;margin-top:3px}
    .ng-hero{padding:26px 28px;border:1px solid rgba(148,163,184,.14);border-radius:19px;background:linear-gradient(135deg,rgba(15,31,52,.98),rgba(9,20,34,.98));margin-bottom:20px}.ng-eyebrow{color:#3b9cff;font-size:.7rem;font-weight:850;letter-spacing:.14em;text-transform:uppercase;margin-bottom:6px}.ng-subtitle{color:#91a4bb;font-size:.96rem;margin:0;max-width:780px}
    @media (max-width: 640px){
      .block-container{padding:1rem .75rem 2rem!important;max-width:100%!important}
      .ng-hero{padding:20px 17px;border-radius:15px;margin-bottom:14px}.ng-hero h1{font-size:2.05rem!important;line-height:1.08!important;margin:0 0 10px!important}.ng-subtitle{font-size:.88rem;line-height:1.55}
      .ng-card{padding:13px;border-radius:12px}.ng-card-value{font-size:1.25rem}.ng-section-label{margin-top:16px}
      div[data-testid="stHorizontalBlock"]{gap:.55rem!important}
      div[data-testid="stHorizontalBlock"]>div[data-testid="column"]{min-width:0!important}
      .stButton>button,.stDownloadButton>button{min-height:46px!important;font-size:.92rem!important}
      .stSelectbox label,.stTextInput label,.stNumberInput label,.stDateInput label{font-size:.86rem!important}
      [data-testid="stDataFrame"]{max-width:100%;overflow-x:auto}
    }
    </style>''', unsafe_allow_html=True)


def brand() -> None:
    st.sidebar.markdown('''<div class="ng-brand"><div class="ng-brand-mark">NG</div><div><div class="ng-brand-name">NG FINANCE PRO</div><div class="ng-brand-tag">Intelligence • Treasury • Risk</div></div></div>''', unsafe_allow_html=True)


def workspace_navigator(current: str) -> None:
    """Mobile-friendly workspace navigator that works without opening the sidebar."""
    st.markdown("### Workspace navigation")
    choices = [x for x in WORKSPACES if x != current]
    target = st.selectbox("Open module", choices, key="ng_mobile_nav")
    if st.button("Open selected module", key="ng_open_module", use_container_width=True):
        st.session_state["ng_nav_target"] = target
        st.rerun()


def hero(title: str, subtitle: str, status: str = "Live market feed") -> None:
    st.markdown(f'''<div class="ng-hero"><div class="ng-eyebrow">NG Finance Pro / Executive workspace</div><h1>{title}</h1><p class="ng-subtitle">{subtitle}</p><div style="margin-top:14px"><span class="ng-status">● {status}</span></div></div>''', unsafe_allow_html=True)


def footer() -> None:
    st.markdown('<div class="ng-footer">NG Finance Pro • Financial Intelligence Platform • MVP v3.0 • Zero-API-cost core</div>', unsafe_allow_html=True)
