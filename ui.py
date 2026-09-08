import streamlit as st


def inject_styles() -> None:
    """Apply the NG Finance Pro visual system."""
    st.markdown(
        """
        <style>
        :root {
            --ng-navy: #0b1220;
            --ng-panel: #111a2b;
            --ng-panel-2: #162238;
            --ng-border: rgba(148, 163, 184, 0.16);
            --ng-text: #f8fafc;
            --ng-muted: #94a3b8;
            --ng-accent: #38bdf8;
            --ng-positive: #34d399;
            --ng-negative: #fb7185;
        }

        .stApp {
            background:
                radial-gradient(circle at 90% 0%, rgba(56, 189, 248, 0.07), transparent 30%),
                var(--ng-navy);
        }

        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stToolbar"] { visibility: hidden; height: 0; }
        .block-container { max-width: 1440px; padding-top: 2rem; padding-bottom: 3rem; }

        [data-testid="stSidebar"] {
            background: #0a1020;
            border-right: 1px solid var(--ng-border);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--ng-muted); }
        [data-testid="stSidebar"] .stRadio label { font-weight: 600; }

        h1, h2, h3 { letter-spacing: -0.02em; }
        h1 { font-size: clamp(2rem, 4vw, 3.1rem) !important; }
        h2 { margin-top: 1.6rem; }

        [data-testid="stMetric"] {
            background: linear-gradient(145deg, var(--ng-panel), var(--ng-panel-2));
            border: 1px solid var(--ng-border);
            border-radius: 16px;
            padding: 18px 20px;
            min-height: 128px;
            box-shadow: 0 12px 32px rgba(0,0,0,.14);
        }
        [data-testid="stMetricLabel"] { color: var(--ng-muted) !important; font-weight: 600; }
        [data-testid="stMetricValue"] { font-size: clamp(1.45rem, 2.6vw, 2rem); }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--ng-border);
            border-radius: 14px;
            overflow: hidden;
        }

        .ng-hero {
            padding: 26px 28px;
            border: 1px solid var(--ng-border);
            border-radius: 20px;
            background: linear-gradient(135deg, rgba(22,34,56,.96), rgba(13,25,44,.96));
            margin-bottom: 24px;
        }
        .ng-eyebrow {
            color: var(--ng-accent);
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .12em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .ng-subtitle { color: var(--ng-muted); font-size: 1rem; margin: 0; }
        .ng-status {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 6px 10px;
            border-radius: 999px;
            background: rgba(52,211,153,.10);
            color: var(--ng-positive);
            border: 1px solid rgba(52,211,153,.18);
            font-size: .78rem;
            font-weight: 700;
        }
        .ng-card {
            border: 1px solid var(--ng-border);
            border-radius: 16px;
            padding: 18px;
            background: rgba(17,26,43,.82);
        }
        .ng-card-title { color: var(--ng-muted); font-size: .82rem; font-weight: 700; }
        .ng-card-value { color: var(--ng-text); font-size: 1.65rem; font-weight: 800; margin: 4px 0; }
        .ng-positive { color: var(--ng-positive); font-weight: 700; }
        .ng-negative { color: var(--ng-negative); font-weight: 700; }
        .ng-muted { color: var(--ng-muted); font-size: .82rem; }
        .ng-footer { color: #64748b; font-size: .78rem; text-align: center; padding-top: 18px; }

        @media (max-width: 800px) {
            .block-container { padding: 1rem 1rem 2.5rem; }
            [data-testid="stMetric"] { min-height: 108px; padding: 14px; }
            .ng-hero { padding: 20px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, status: str = "Live market feed") -> None:
    st.markdown(
        f"""
        <div class="ng-hero">
            <div class="ng-eyebrow">NG Finance Pro</div>
            <h1>{title}</h1>
            <p class="ng-subtitle">{subtitle}</p>
            <div style="margin-top:14px"><span class="ng-status">● {status}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer() -> None:
    st.markdown(
        '<div class="ng-footer">NG Finance Pro • Financial Intelligence Platform • MVP v2.2 • Zero-API-cost core</div>',
        unsafe_allow_html=True,
    )
