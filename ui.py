import streamlit as st


def inject_styles() -> None:
    """Apply the NG Finance Pro institutional visual system."""
    st.markdown(
        """
        <style>
        :root {
            --ng-bg: #07111f;
            --ng-sidebar: #08101c;
            --ng-panel: #0d1929;
            --ng-panel-2: #101f33;
            --ng-border: rgba(148, 163, 184, 0.14);
            --ng-text: #f7fafc;
            --ng-muted: #91a4bb;
            --ng-blue: #3b9cff;
            --ng-green: #2dd4a7;
            --ng-red: #ff647c;
            --ng-gold: #f4c95d;
        }

        .stApp {
            background:
                radial-gradient(circle at 78% -10%, rgba(59,156,255,.10), transparent 28%),
                radial-gradient(circle at 15% 10%, rgba(45,212,167,.035), transparent 24%),
                var(--ng-bg);
        }
        [data-testid="stHeader"] { background: rgba(7,17,31,.82); }
        [data-testid="stToolbar"] { visibility: hidden; height: 0; }
        .block-container { max-width: 1500px; padding: 1.35rem 2.2rem 3rem; }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #08111e 0%, #060d17 100%);
            border-right: 1px solid var(--ng-border);
        }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1.1rem; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--ng-muted); }
        [data-testid="stSidebar"] hr { border-color: var(--ng-border); }
        [data-testid="stSidebar"] .stRadio > label {
            color: #7389a3;
            font-size: .72rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .11em;
        }
        [data-testid="stSidebar"] .stRadio [role="radiogroup"] { gap: .18rem; }
        [data-testid="stSidebar"] .stRadio [role="radio"] {
            border-radius: 10px;
            padding: .55rem .65rem;
            transition: background .15s ease;
        }
        [data-testid="stSidebar"] .stRadio [role="radio"]:hover { background: rgba(59,156,255,.07); }
        [data-testid="stSidebar"] .stRadio [role="radio"][aria-checked="true"] {
            background: linear-gradient(90deg, rgba(59,156,255,.18), rgba(59,156,255,.05));
            border-left: 2px solid var(--ng-blue);
        }

        h1, h2, h3, h4 { letter-spacing: -.025em; }
        h1 { font-size: clamp(2rem, 4vw, 3rem) !important; }
        h2 { margin-top: 1.45rem; }
        h3 { margin-top: 1rem; }

        [data-testid="stMetric"] {
            background: linear-gradient(145deg, rgba(13,25,41,.98), rgba(16,31,51,.98));
            border: 1px solid var(--ng-border);
            border-radius: 15px;
            padding: 16px 18px;
            min-height: 118px;
            box-shadow: 0 14px 38px rgba(0,0,0,.12);
        }
        [data-testid="stMetricLabel"] { color: var(--ng-muted) !important; font-weight: 700; }
        [data-testid="stMetricValue"] { font-size: clamp(1.35rem, 2.5vw, 1.9rem); font-weight: 800; }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--ng-border);
            border-radius: 13px;
            overflow: hidden;
        }
        .stButton > button {
            border: 1px solid var(--ng-border);
            border-radius: 9px;
            background: rgba(13,25,41,.9);
            font-weight: 700;
        }
        .stButton > button:hover { border-color: rgba(59,156,255,.55); color: var(--ng-blue); }
        .stSelectbox > div > div, .stTextInput > div > div {
            border-radius: 9px;
            border-color: var(--ng-border);
            background: rgba(13,25,41,.8);
        }

        .ng-brand {
            display: flex; align-items: center; gap: 11px;
            padding: 8px 4px 18px;
        }
        .ng-brand-mark {
            width: 38px; height: 38px; border-radius: 11px;
            display: grid; place-items: center;
            background: linear-gradient(135deg, #3b9cff, #2dd4a7);
            color: #06111e; font-weight: 950; font-size: 18px;
            box-shadow: 0 8px 25px rgba(59,156,255,.22);
        }
        .ng-brand-name { color: var(--ng-text); font-weight: 900; font-size: 1.05rem; line-height: 1.05; }
        .ng-brand-tag { color: #61758d; font-size: .62rem; letter-spacing: .1em; text-transform: uppercase; margin-top: 3px; }

        .ng-hero {
            position: relative;
            overflow: hidden;
            padding: 26px 28px;
            border: 1px solid var(--ng-border);
            border-radius: 19px;
            background: linear-gradient(135deg, rgba(15,31,52,.98), rgba(9,20,34,.98));
            margin-bottom: 20px;
            box-shadow: 0 18px 50px rgba(0,0,0,.13);
        }
        .ng-hero:after {
            content: ""; position: absolute; width: 230px; height: 230px;
            right: -90px; top: -120px; border-radius: 50%;
            background: rgba(59,156,255,.09); filter: blur(2px);
        }
        .ng-eyebrow { color: var(--ng-blue); font-size: .7rem; font-weight: 850; letter-spacing: .14em; text-transform: uppercase; margin-bottom: 6px; }
        .ng-subtitle { color: var(--ng-muted); font-size: .96rem; margin: 0; max-width: 780px; }
        .ng-status {
            display: inline-flex; align-items: center; gap: 7px; padding: 6px 10px;
            border-radius: 999px; background: rgba(45,212,167,.08); color: var(--ng-green);
            border: 1px solid rgba(45,212,167,.16); font-size: .72rem; font-weight: 800;
        }
        .ng-card {
            border: 1px solid var(--ng-border); border-radius: 15px; padding: 17px;
            background: linear-gradient(145deg, rgba(13,25,41,.96), rgba(10,21,35,.96));
        }
        .ng-card-title { color: var(--ng-muted); font-size: .77rem; font-weight: 750; }
        .ng-card-value { color: var(--ng-text); font-size: 1.55rem; font-weight: 850; margin: 4px 0; }
        .ng-positive { color: var(--ng-green); font-weight: 750; }
        .ng-negative { color: var(--ng-red); font-weight: 750; }
        .ng-neutral { color: var(--ng-gold); font-weight: 750; }
        .ng-muted { color: var(--ng-muted); font-size: .78rem; }
        .ng-section-label { color: #6f849c; font-size: .68rem; font-weight: 850; letter-spacing: .13em; text-transform: uppercase; margin: 22px 0 8px; }
        .ng-footer { color: #53667d; font-size: .72rem; text-align: center; padding-top: 20px; }
        .ng-upgrade {
            margin-top: 22px; padding: 15px; border-radius: 13px;
            border: 1px solid rgba(59,156,255,.20);
            background: linear-gradient(145deg, rgba(59,156,255,.10), rgba(45,212,167,.05));
        }
        .ng-upgrade-title { color: var(--ng-text); font-weight: 800; font-size: .85rem; }
        .ng-upgrade-copy { color: #71869e; font-size: .7rem; margin-top: 4px; line-height: 1.45; }

        @media (max-width: 800px) {
            .block-container { padding: .9rem .8rem 2.5rem; }
            .ng-hero { padding: 20px; border-radius: 15px; }
            [data-testid="stMetric"] { min-height: 104px; padding: 13px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def brand() -> None:
    st.sidebar.markdown(
        """
        <div class="ng-brand">
            <div class="ng-brand-mark">NG</div>
            <div>
                <div class="ng-brand-name">NG FINANCE PRO</div>
                <div class="ng-brand-tag">Intelligence • Treasury • Risk</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, status: str = "Live market feed") -> None:
    st.markdown(
        f"""
        <div class="ng-hero">
            <div class="ng-eyebrow">NG Finance Pro / Executive workspace</div>
            <h1>{title}</h1>
            <p class="ng-subtitle">{subtitle}</p>
            <div style="margin-top:14px"><span class="ng-status">● {status}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer() -> None:
    st.markdown(
        '<div class="ng-footer">NG Finance Pro • Financial Intelligence Platform • MVP v3.0 • Zero-API-cost core</div>',
        unsafe_allow_html=True,
    )
