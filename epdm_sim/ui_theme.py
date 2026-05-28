"""High-end industrial digital-twin UI theme helpers for Streamlit."""

from __future__ import annotations

from html import escape
from typing import Iterable

import plotly.io as pio
import streamlit as st


ACCENTS = {
    "cyan": "#22d3ee",
    "blue": "#60a5fa",
    "amber": "#f59e0b",
    "orange": "#fb923c",
    "red": "#ef4444",
    "magenta": "#d946ef",
    "purple": "#a78bfa",
    "dark_red": "#7f1d1d",
    "graphite": "#0b1120",
}


def apply_theme(theme: str = "深色") -> None:
    """Apply the Android/Material-inspired industrial digital-twin theme."""
    dark = theme != "浅色"
    bg = "#050914" if dark else "#edf3fb"
    panel = "rgba(12, 21, 38, 0.70)" if dark else "rgba(255,255,255,0.76)"
    panel2 = "rgba(18, 31, 55, 0.58)" if dark else "rgba(241,247,255,0.86)"
    text = "#e5eefb" if dark else "#122033"
    muted = "#91a4bd" if dark else "#506078"
    border = "rgba(125, 211, 252, 0.22)" if dark else "rgba(59, 130, 246, 0.22)"
    shadow = "0 20px 70px rgba(0,0,0,.35)" if dark else "0 18px 50px rgba(59,130,246,.14)"
    pio.templates.default = "plotly_dark" if dark else "plotly_white"
    st.markdown(
        f"""
        <style>
        :root {{
            --epdm-bg: {bg};
            --epdm-panel: {panel};
            --epdm-panel-2: {panel2};
            --epdm-text: {text};
            --epdm-muted: {muted};
            --epdm-border: {border};
            --epdm-cyan: {ACCENTS['cyan']};
            --epdm-blue: {ACCENTS['blue']};
            --epdm-amber: {ACCENTS['amber']};
            --epdm-red: {ACCENTS['red']};
            --epdm-purple: {ACCENTS['purple']};
            --epdm-shadow: {shadow};
        }}
        .stApp {{
            color: var(--epdm-text);
            background:
                radial-gradient(circle at 18% 8%, rgba(34,211,238,.14), transparent 32%),
                radial-gradient(circle at 85% 15%, rgba(167,139,250,.14), transparent 30%),
                linear-gradient(140deg, {bg} 0%, {"#07111f" if dark else "#f6fbff"} 48%, {"#090d18" if dark else "#eaf2fb"} 100%);
        }}
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, rgba(9,15,28,.92), rgba(13,22,39,.78));
            border-right: 1px solid var(--epdm-border);
            box-shadow: 8px 0 30px rgba(0,0,0,.20);
            backdrop-filter: blur(18px);
        }}
        section[data-testid="stSidebar"] * {{ color: var(--epdm-text); }}
        .block-container {{
            padding-top: 1.15rem;
            max-width: 1800px;
        }}
        h1, h2, h3 {{
            letter-spacing: 0;
            color: var(--epdm-text);
        }}
        div[data-testid="stMetric"], .epdm-glass-card {{
            background: linear-gradient(145deg, var(--epdm-panel), var(--epdm-panel-2));
            border: 1px solid var(--epdm-border);
            border-radius: 22px;
            padding: 14px 16px;
            box-shadow: var(--epdm-shadow);
            backdrop-filter: blur(20px) saturate(135%);
            transition: transform .22s ease, border-color .22s ease, box-shadow .22s ease;
        }}
        div[data-testid="stMetric"]:hover, .epdm-glass-card:hover {{
            transform: translateY(-1px);
            border-color: rgba(34,211,238,.42);
            box-shadow: 0 24px 80px rgba(34,211,238,.10);
        }}
        div[data-testid="stMetricLabel"] p {{
            color: var(--epdm-muted);
            font-size: .82rem;
        }}
        div[data-testid="stMetricValue"] {{
            font-size: 1.72rem;
            font-weight: 760;
            color: var(--epdm-text);
        }}
        .stButton > button, .stDownloadButton > button {{
            border: 1px solid rgba(34,211,238,.35);
            border-radius: 999px;
            background: linear-gradient(135deg, rgba(34,211,238,.20), rgba(96,165,250,.12));
            color: var(--epdm-text);
            box-shadow: 0 10px 32px rgba(34,211,238,.13);
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            transform: translateY(-1px);
            border-color: rgba(34,211,238,.78);
            box-shadow: 0 16px 42px rgba(34,211,238,.20);
        }}
        div[data-testid="stSelectbox"], div[data-testid="stNumberInput"], div[data-testid="stSlider"] {{
            border-radius: 18px;
        }}
        div[data-testid="stExpander"] {{
            background: rgba(12,21,38,.36);
            border: 1px solid var(--epdm-border);
            border-radius: 20px;
            overflow: hidden;
            backdrop-filter: blur(14px);
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background: rgba(15,23,42,.35);
            border-radius: 999px;
            padding: 6px;
            border: 1px solid var(--epdm-border);
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 999px;
            padding: 10px 16px;
        }}
        .js-plotly-plot, .stPlotlyChart {{
            border-radius: 22px;
            overflow: hidden;
        }}
        .epdm-topbar {{
            display:flex; align-items:center; justify-content:space-between; gap:14px;
            padding: 16px 18px; margin-bottom: 16px;
            background: linear-gradient(135deg, rgba(15,23,42,.78), rgba(30,41,59,.42));
            border: 1px solid var(--epdm-border);
            border-radius: 26px;
            box-shadow: var(--epdm-shadow);
            backdrop-filter: blur(22px) saturate(150%);
        }}
        .epdm-title {{
            font-size: 1.25rem; font-weight: 780;
            background: linear-gradient(90deg, var(--epdm-cyan), var(--epdm-blue), var(--epdm-purple));
            -webkit-background-clip: text; color: transparent;
        }}
        .epdm-subtitle {{ color: var(--epdm-muted); font-size: .82rem; margin-top: 2px; }}
        .epdm-status-dot {{
            display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:8px;
            background: var(--dot-color); box-shadow: 0 0 16px var(--dot-color);
            animation: epdmPulse 1.8s ease-in-out infinite;
        }}
        @keyframes epdmPulse {{
            0%, 100% {{ opacity:.65; transform:scale(.95); }}
            50% {{ opacity:1; transform:scale(1.18); }}
        }}
        .epdm-chip {{
            display:inline-flex; align-items:center; gap:6px;
            padding:7px 11px; border-radius:999px; font-size:.82rem;
            border:1px solid rgba(255,255,255,.12);
            background: rgba(15,23,42,.38);
        }}
        .epdm-kpi-grid {{
            display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:12px;
            margin: 12px 0 18px;
        }}
        .epdm-kpi-card {{
            background: linear-gradient(145deg, var(--epdm-panel), rgba(15,23,42,.36));
            border: 1px solid var(--epdm-border);
            border-radius: 22px; padding: 15px 16px;
            box-shadow: var(--epdm-shadow);
            backdrop-filter: blur(20px);
        }}
        .epdm-kpi-label {{ color: var(--epdm-muted); font-size:.78rem; }}
        .epdm-kpi-value {{ font-size:1.62rem; font-weight:780; margin-top:4px; color:var(--epdm-text); }}
        .epdm-kpi-note {{ color: var(--accent); font-size:.76rem; margin-top:3px; }}
        .epdm-section-title {{
            display:flex; align-items:center; gap:10px; margin: 16px 0 8px;
            font-weight:720; color:var(--epdm-text);
        }}
        .epdm-section-title:before {{
            content:""; width:7px; height:24px; border-radius:999px;
            background: linear-gradient(180deg, var(--epdm-cyan), var(--epdm-purple));
            box-shadow: 0 0 20px rgba(34,211,238,.35);
        }}
        .epdm-alert {{
            margin: 0.72rem 0;
            padding: 0.86rem 1rem;
            border-radius: 18px;
            border: 1px solid var(--epdm-alert-border);
            background: linear-gradient(135deg, var(--epdm-alert-bg), rgba(15,23,42,.24));
            color: var(--epdm-text);
            box-shadow: 0 14px 44px rgba(0,0,0,.18);
            backdrop-filter: blur(16px) saturate(130%);
        }}
        .epdm-alert strong {{ color: var(--epdm-alert-color); margin-right: .45rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    install_safe_alerts()


def install_safe_alerts() -> None:
    """Install alert helpers that do not depend on Streamlit's optional emoji module.

    Some bundled Streamlit runtimes can render pages but fail inside
    ``st.info``/``st.warning``/``st.success`` because ``streamlit.emojis`` is
    absent.  The app only needs styled status text, so we replace those calls
    with the local glassmorphism alert markup after the theme has been applied.
    """
    if getattr(st, "_epdm_safe_alerts_installed", False):
        return

    def _render_alert(level: str, label: str, color: str, body: object, *_args: object, **_kwargs: object) -> None:
        text = escape(str(body))
        st.markdown(
            (
                "<div class='epdm-alert' "
                f"style='--epdm-alert-color:{color}; --epdm-alert-border:{color}66; --epdm-alert-bg:{color}1f;'>"
                f"<strong>{escape(label)}</strong>{text}</div>"
            ),
            unsafe_allow_html=True,
        )

    st.info = lambda body, *args, **kwargs: _render_alert("info", "提示", ACCENTS["blue"], body, *args, **kwargs)  # type: ignore[method-assign]
    st.success = lambda body, *args, **kwargs: _render_alert("success", "完成", ACCENTS["cyan"], body, *args, **kwargs)  # type: ignore[method-assign]
    st.warning = lambda body, *args, **kwargs: _render_alert("warning", "注意", ACCENTS["amber"], body, *args, **kwargs)  # type: ignore[method-assign]
    st.error = lambda body, *args, **kwargs: _render_alert("error", "错误", ACCENTS["red"], body, *args, **kwargs)  # type: ignore[method-assign]
    st._epdm_safe_alerts_installed = True


def top_bar(case_name: str, status: str, theme: str) -> None:
    """Render a glass top navigation bar."""
    color = status_color(status)
    st.markdown(
        f"""
        <div class="epdm-topbar">
          <div>
            <div class="epdm-title">Metallocene EPDM Digital Twin</div>
            <div class="epdm-subtitle">{escape(case_name)} · Android/Material industrial cockpit · {escape(theme)}</div>
          </div>
          <div class="epdm-chip"><span class="epdm-status-dot" style="--dot-color:{color}"></span>{escape(status)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_grid(items: Iterable[tuple[str, str, str | None, str | None]]) -> None:
    """Render a responsive KPI card grid."""
    cards = []
    for label, value, note, color in items:
        accent = color or ACCENTS["cyan"]
        cards.append(
            "<div class='epdm-kpi-card'>"
            f"<div class='epdm-kpi-label'>{escape(label)}</div>"
            f"<div class='epdm-kpi-value'>{escape(value)}</div>"
            f"<div class='epdm-kpi-note' style='--accent:{accent}; color:{accent};'>{escape(note or '')}</div>"
            "</div>"
        )
    st.markdown(f"<div class='epdm-kpi-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


def section_title(title: str) -> None:
    """Render a section title in the digital-twin style."""
    st.markdown(f"<div class='epdm-section-title'>{escape(title)}</div>", unsafe_allow_html=True)


def status_color(status: str | None) -> str:
    """Map a process/risk status to a digital-twin accent color."""
    value = (status or "").lower()
    if value in {"danger", "high", "危险"} or "不足" in value:
        return ACCENTS["red"]
    if value in {"medium", "warning", "注意"} or "偏高" in value:
        return ACCENTS["amber"]
    if "viscosity" in value or "黏" in value:
        return ACCENTS["purple"]
    return ACCENTS["cyan"]


def risk_chip(label: str, status: str | None) -> str:
    """Return an inline HTML status chip."""
    color = status_color(status)
    return (
        f"<span class='epdm-chip'><span class='epdm-status-dot' "
        f"style='--dot-color:{color}'></span>{escape(label)}：{escape(str(status))}</span>"
    )
