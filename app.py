"""KPI Partner Channel Dashboard — Streamlit app (v2.1 polished)."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from config import (
    FUNNEL_ORDER,
    STATUS_COLORS,
    MANAGER_COLORS,
    TARGETS_Q1,
    TARGETS_Q2,
    QUARTERLY_PLANS,
    BDM_KPI_TARGETS,
    BDM_TOTAL_BONUS,
    BDM_MANAGERS,
)
import html as _html
from datetime import datetime as _datetime

# Current quarter (used in header and progress section)
_current_q = (_datetime.now().month - 1) // 3 + 1
from data_loader import (
    load_pipeline,
    load_longlist,
    load_all_longlists,
    load_deals,
    build_touches_timeline,
    compute_bdm_kpi,
)

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="KPI Партнёрский канал",
    page_icon="📊",
    layout="wide",
)

# ──────────────────────────────────────────────
# Global CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
/* ── Streamlit chrome ── */
#MainMenu, footer {display: none !important;}
header[data-testid="stHeader"] {background: transparent !important; backdrop-filter: none !important;}

/* ── Tighter vertical rhythm ── */
[data-testid="stVerticalBlock"] > div {gap: 0.25rem !important;}
.block-container {padding-top: 1rem !important; padding-bottom: 0.5rem !important; max-width: 100% !important; padding-left: 2rem !important; padding-right: 2rem !important;}

/* ── Allow tooltips to overflow containers and stack on top ── */
[data-testid="stHorizontalBlock"],
[data-testid="stColumn"],
[data-testid="stMarkdownContainer"],
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stVerticalBlock"],
[data-testid="column"],
.stMarkdown, .element-container {
    overflow: visible !important;
}
/* Hovered card/th rises above all siblings */
.kpi-card:hover, .styled-table thead th:hover {
    z-index: 99999 !important;
    position: relative;
}

/* ── KPI Card ── */
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E2E6EC;
    border-top: 3px solid #4A90D9;
    border-radius: 10px;
    padding: 16px 12px 14px 12px;
    text-align: center;
    min-height: 100px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    transition: box-shadow 0.15s, z-index 0s;
    overflow: visible;
    position: relative;
    z-index: 1;
}
.kpi-card:hover {box-shadow: 0 3px 12px rgba(74,144,217,0.12); z-index: 99999;}
.kpi-card.alert {border-top-color: #E57373;}
.kpi-card.money {border-top-color: #66BB6A;}
.kpi-label {
    font-size: 12.5px;
    font-weight: 700;
    color: #8C939D;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 6px;
    line-height: 1.35;
    white-space: nowrap;
}
.kpi-value {
    font-size: 36px;
    font-weight: 800;
    color: #1A1A2E;
    line-height: 1.05;
    letter-spacing: -0.5px;
}
.kpi-value .unit {
    font-size: 18px;
    font-weight: 600;
    color: #8C939D;
    margin-left: 2px;
}
.kpi-sub {
    font-size: 12.5px;
    color: #A0A7B3;
    margin-top: 4px;
}

/* ── Section Header ── */
.section-hdr {
    border-left: 4px solid #4A90D9;
    padding-left: 12px;
    font-size: 19px;
    font-weight: 700;
    color: #1A1A2E;
    margin: 14px 0 8px 0;
    line-height: 1.3;
    position: relative;
    z-index: 10;
}

/* ── Conversion blocks ── */
.conv-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border-radius: 6px;
    margin-bottom: 4px;
    background: #FAFBFC;
    border: 1px solid #F0F1F3;
}
.conv-pct {font-size: 22px; font-weight: 700; min-width: 60px;}
.conv-pct.red {color: #D32F2F;}
.conv-pct.yellow {color: #F57C00;}
.conv-pct.green {color: #388E3C;}
.conv-detail {font-size: 14px; color: #6B7280; line-height: 1.3;}
.conv-total {
    background: #EBF0FA;
    border: 1px solid #D0DBEF;
    border-radius: 6px;
    padding: 10px 14px;
    margin-top: 4px;
    text-align: center;
}
.conv-total .pct {font-size: 24px; font-weight: 700; color: #1A1A2E;}
.conv-total .lbl {font-size: 13px; color: #6B7280; margin-top: 2px;}

/* ── Styled table ── */
.styled-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 15px;
    border-radius: 8px;
    overflow: visible;
    border: 1px solid #E2E6EC;
    box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}
.styled-table thead tr:first-child th:first-child {border-top-left-radius: 7px;}
.styled-table thead tr:first-child th:last-child {border-top-right-radius: 7px;}
.styled-table tbody tr:last-child td:first-child {border-bottom-left-radius: 7px;}
.styled-table tbody tr:last-child td:last-child {border-bottom-right-radius: 7px;}
.styled-table thead th {
    background: #F0F2F6;
    color: #5A6270;
    font-weight: 700;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 10px 12px;
    text-align: left;
    border-bottom: 2px solid #E0E3E8;
    white-space: nowrap;
    overflow: visible;
    position: relative;
}
.styled-table thead th.num {text-align: right;}
.styled-table tbody td {
    padding: 9px 12px;
    border-bottom: 1px solid #F0F1F3;
    color: #2D3748;
    font-size: 15px;
}
.styled-table tbody td.num {text-align: right; font-variant-numeric: tabular-nums; font-weight: 500;}
.styled-table tbody tr:last-child td {border-bottom: none;}
.styled-table tbody tr:hover {background: #F7F9FC;}
.styled-table .row-total td {
    background: #E8EDF5;
    font-weight: 800;
    color: #1A1A2E;
    border-top: 2px solid #C5D0E3;
    font-size: 15px;
}
.styled-table .zero {color: #D32F2F; font-weight: 700;}
.styled-table .low {color: #F57C00; font-weight: 600;}
.styled-table .ok {color: #2E7D32; font-weight: 700;}

/* ── Data bar cell ── */
.data-bar {
    display: flex; align-items: center; gap: 6px; justify-content: flex-end;
}
.data-bar .bar {
    height: 6px; border-radius: 3px; background: #4A90D9; min-width: 2px;
}
.data-bar .bar.red {background: #E57373;}
.data-bar .bar.green {background: #66BB6A;}
.data-bar .bar.amber {background: #FFB74D;}

/* ── Badge ── */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 700;
    line-height: 1.5;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {background: #F4F6F9 !important;}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {gap: 0.3rem !important;}
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stSelectbox label {
    font-size: 11px !important;
    font-weight: 600 !important;
    color: #6B7280 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
    font-size: 11px !important;
    padding: 1px 6px !important;
    border-radius: 4px !important;
}
[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background: linear-gradient(135deg, #4A90D9 0%, #3A7BC8 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 16px !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    letter-spacing: 0.3px !important;
    box-shadow: 0 2px 6px rgba(74,144,217,0.25) !important;
    transition: all 0.15s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: linear-gradient(135deg, #3A7BC8 0%, #2D6CB5 100%) !important;
    box-shadow: 0 3px 10px rgba(74,144,217,0.35) !important;
}

/* ── Plotly chart tighter ── */
[data-testid="stPlotlyChart"] {margin-top: -4px; margin-bottom: -8px;}

/* ── Panel container ── */
.panel {
    background: #FFFFFF;
    border: 1px solid #E2E6EC;
    border-radius: 10px;
    padding: 14px 16px 10px 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}
.panel-hdr {
    font-size: 11px;
    font-weight: 700;
    color: #8C939D;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}

/* ── Info tooltip ── */
.info-tip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px; height: 18px;
    border-radius: 50%;
    background: #E2E6EC;
    color: #6B7280;
    font-size: 10px;
    font-weight: 700;
    font-style: normal;
    cursor: help;
    position: relative;
    vertical-align: middle;
    margin-left: 4px;
    flex-shrink: 0;
    line-height: 1;
    transition: background 0.15s;
}
.info-tip:hover {background: #4A90D9; color: white;}
/* Default: opens BELOW, centered */
.info-tip .tip-body {
    visibility: hidden;
    opacity: 0;
    position: absolute;
    top: calc(100% + 14px);
    left: 50%;
    transform: translateX(-50%);
    background: #1A1A2E;
    color: #E8ECF0;
    font-size: 12px;
    font-weight: 400;
    line-height: 1.45;
    padding: 10px 12px;
    border-radius: 8px;
    width: 260px;
    white-space: normal;
    text-transform: none;
    letter-spacing: 0;
    text-align: left;
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    z-index: 999999;
    pointer-events: none;
    transition: opacity 0.15s, visibility 0.15s;
}
/* Arrow pointing UP (tooltip below icon) */
.info-tip .tip-body::after {
    content: '';
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 6px solid transparent;
    border-bottom-color: #1A1A2E;
}
.info-tip:hover .tip-body {visibility: visible; opacity: 1;}
.info-tip .tip-body b {color: #81C784; font-weight: 600;}
.info-tip .tip-body .tip-formula {
    display: block;
    margin-top: 4px;
    padding: 4px 6px;
    background: rgba(255,255,255,0.08);
    border-radius: 4px;
    font-family: monospace;
    font-size: 11px;
    color: #B0BEC5;
}
.info-tip .tip-body .tip-src {
    display: block;
    margin-top: 4px;
    font-size: 10.5px;
    color: #8C939D;
}
/* Right-aligned: tooltip opens to the left */
.info-tip.tip-left .tip-body {left: auto; right: -8px; transform: none;}
.info-tip.tip-left .tip-body::after {left: auto; right: 12px; transform: none;}

/* ── Footer ── */
.footer-text {
    text-align: center;
    color: #B0B7C3;
    font-size: 13px;
    padding: 8px 0 2px 0;
}
/* ── Train loading animation ── */
@keyframes trainSlideIn {
    0%   { transform: translateX(120%); }
    70%  { transform: translateX(0%); }
    85%  { transform: translateX(-3%); }
    92%  { transform: translateX(1%); }
    100% { transform: translateX(0%); }
}
@keyframes wheelSpin {
    0%   { transform: rotate(0deg); }
    70%  { transform: rotate(-720deg); }
    100% { transform: rotate(-720deg); }
}
@keyframes smokeRise {
    0%   { opacity: 0.6; transform: translate(0,0) scale(1); }
    50%  { opacity: 0.3; transform: translate(8px,-12px) scale(1.5); }
    100% { opacity: 0; transform: translate(16px,-24px) scale(2); }
}
@keyframes smokeFade {
    0%   { opacity: 1; }
    70%  { opacity: 1; }
    100% { opacity: 0; }
}
.train-animated { animation: trainSlideIn 3.5s cubic-bezier(.25,.46,.45,.94) forwards; }
.train-animated .train-wheel { animation: wheelSpin 3.5s cubic-bezier(.25,.46,.45,.94) forwards; }
.train-smoke-group { animation: smokeFade 4.5s ease-out forwards; }
.train-smoke-group circle { animation: smokeRise 1.8s ease-out infinite; }
.train-smoke-group circle:nth-child(2) { animation-delay: 0.6s; }
.train-smoke-group circle:nth-child(3) { animation-delay: 1.2s; }
</style>
""", unsafe_allow_html=True)

# Inject JS for local time via st.components
import streamlit.components.v1 as _components
_components.html("""
<script>
    function _setTime(){
        var els = window.parent.document.querySelectorAll('#local-time');
        els.forEach(function(el){
            var d = new Date();
            el.textContent = d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
        });
    }
    setInterval(function(){
        _setTime();
    }, 1000);
</script>
""", height=0, width=0)

# ──────────────────────────────────────────────
# Pre-load helpers (needed for header before data loads)
# ──────────────────────────────────────────────
def _short_money(val, suffix="м"):
    """Format money as short string: 1500000 -> '1.5м', 500000 -> '500т'."""
    if abs(val) >= 1_000_000:
        r = val / 1_000_000
        return f'{r:.1f}{suffix}'.replace('.0' + suffix, suffix)
    return f'{val / 1_000:.0f}т'



def _build_train_html(animated=False):
    """Build the locomotive + wagons HTML. animated=True adds slide-in + smoke."""
    anim_cls = ' class="train-animated"' if animated else ''
    wheel_cls = ' class="train-wheel"' if animated else ''
    # Smoke: animated group or static circles
    if animated:
        smoke_html = (
            '<g class="train-smoke-group">'
            '<circle cx="21" cy="4" r="4" stroke="#9E9E9E" stroke-width="1" fill="#D0D0D0" fill-opacity="0.3" opacity="0.5"/>'
            '<circle cx="14" cy="-2" r="3" stroke="#9E9E9E" stroke-width="0.8" fill="#D0D0D0" fill-opacity="0.2" opacity="0.35"/>'
            '<circle cx="8" cy="-6" r="2.5" stroke="#9E9E9E" stroke-width="0.6" fill="#D0D0D0" fill-opacity="0.15" opacity="0.2"/>'
            '</g>'
        )
    else:
        smoke_html = (
            '<circle cx="21" cy="4" r="4" stroke="#9E9E9E" stroke-width="1" fill="none" opacity="0.4"/>'
            '<circle cx="13" cy="2" r="2.5" stroke="#9E9E9E" stroke-width="0.8" fill="none" opacity="0.25"/>'
        )

    wagons = ''.join([
        (lambda p, qi: (
            '<div style="width:3px;height:2px;background:#8C939D;flex-shrink:0;z-index:2;align-self:flex-end;margin-bottom:8px;"></div>'
            '<div style="position:relative;flex-shrink:0;width:124px;z-index:2;">'
            '<div style="border-radius:10px;padding:8px 12px;text-align:center;height:60px;display:flex;flex-direction:column;'
            'justify-content:center;box-sizing:border-box;background:{bg};border:{brd_style};{shadow}">'
            '<div style="font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:{lbl};">{q}</div>'
            '<div style="font-size:14px;font-weight:700;color:#1A1A2E;margin-top:2px;">Rev {rev}</div>'
            '<div style="font-size:12px;color:#6B7280;">MRR {mrr}</div>'
            '</div>'
            '<div{wc} style="position:absolute;bottom:-4px;left:18px;width:14px;height:14px;border-radius:50%;border:1.5px solid #1A1A2E;'
            'background:radial-gradient(circle,#4A90D9 22%,transparent 22%);z-index:3;"></div>'
            '<div{wc} style="position:absolute;bottom:-4px;right:18px;width:14px;height:14px;border-radius:50%;border:1.5px solid #1A1A2E;'
            'background:radial-gradient(circle,#4A90D9 22%,transparent 22%);z-index:3;"></div>'
            '<div style="position:absolute;bottom:8px;right:-5px;width:7px;height:2px;background:#8C939D;z-index:2;"></div>'
            '</div>'
        ).format(
            bg="#EFF6FF" if qi == _current_q else ("#FAFAFA" if p.get("forecast") else "#F7F8FA"),
            brd_style="2px solid #4A90D9" if qi == _current_q else ("1.5px dashed #E0E0E0" if p.get("forecast") else "1.5px solid #E2E6EC"),
            shadow="box-shadow:0 0 0 2px rgba(74,144,217,0.15);" if qi == _current_q else ("opacity:0.85;" if p.get("forecast") else ""),
            lbl="#4A90D9" if qi == _current_q else ("#B0B0B0" if p.get("forecast") else "#8C939D"),
            q=p["q"] + (" прогноз" if p.get("forecast") else " план"),
            rev=_short_money(p["revenue"], "М"),
            mrr=_short_money(p["mrr"], "М") if p["mrr"] >= 1_000_000 else _short_money(p["mrr"], "К").replace("т", "К"),
            wc=wheel_cls,
        ))(p, i + 1)
        for i, p in enumerate(QUARTERLY_PLANS)
    ])

    return (
        f'<div{anim_cls} style="margin-left:auto;flex-shrink:0;margin-right:120px;position:relative;display:flex;align-items:flex-end;gap:0;padding-bottom:22px;overflow:hidden;">'
        '<div style="position:absolute;bottom:16px;left:0;right:0;height:2px;background:#8C939D;z-index:1;border-radius:1px;"></div>'
        '<div style="position:absolute;bottom:12px;left:0;right:0;height:1.5px;background:#8C939D;opacity:0.4;z-index:1;border-radius:1px;"></div>'
        '<div style="position:absolute;bottom:10px;left:0;right:0;height:10px;z-index:0;'
        'background:repeating-linear-gradient(90deg,transparent,transparent 16px,rgba(176,176,176,0.25) 16px,rgba(176,176,176,0.25) 19px);"></div>'
        '<div style="position:relative;flex-shrink:0;width:90px;z-index:2;">'
        '<svg width="90" height="60" viewBox="0 0 90 60" fill="none" stroke="#4A90D9" style="display:block;">'
        + smoke_html +
        '<rect x="16" y="7" width="10" height="13" rx="2" stroke-width="1.8"/>'
        '<rect x="14" y="5" width="14" height="3.5" rx="1" stroke-width="1.5"/>'
        '<ellipse cx="38" cy="20" rx="5" ry="3" stroke-width="1.2" fill="none"/>'
        '<rect x="8" y="20" width="48" height="22" rx="5" stroke-width="2" fill="none"/>'
        '<line x1="24" y1="20" x2="24" y2="42" stroke-width="0.8" opacity="0.3"/>'
        '<line x1="40" y1="20" x2="40" y2="42" stroke-width="0.8" opacity="0.3"/>'
        '<circle cx="8" cy="31" r="7" stroke-width="2" fill="none"/>'
        '<circle cx="8" cy="31" r="2.5" stroke-width="1" fill="none"/>'
        '<rect x="54" y="12" width="22" height="30" rx="3" stroke-width="2" fill="none"/>'
        '<path d="M52 12 L78 12 L78 8 Q65 3 52 8 Z" stroke-width="1.5" fill="none"/>'
        '<rect x="58" y="17" width="6" height="8" rx="1" stroke-width="1.2" fill="none"/>'
        '<rect x="66" y="17" width="6" height="8" rx="1" stroke-width="1.2" fill="none"/>'
        '<path d="M0 50 L8 42 L8 50 Z" stroke-width="1.2" fill="none"/>'
        '<line x1="0" y1="46" x2="78" y2="46" stroke="#1A1A2E" stroke-width="2"/>'
        '</svg>'
        f'<div{wheel_cls} style="position:absolute;bottom:-4px;left:12px;width:18px;height:18px;border-radius:50%;border:2px solid #1A1A2E;'
        'background:radial-gradient(circle,#4A90D9 25%,transparent 25%);z-index:3;"></div>'
        f'<div{wheel_cls} style="position:absolute;bottom:-4px;left:36px;width:18px;height:18px;border-radius:50%;border:2px solid #1A1A2E;'
        'background:radial-gradient(circle,#4A90D9 25%,transparent 25%);z-index:3;"></div>'
        f'<div{wheel_cls} style="position:absolute;bottom:-2px;left:64px;width:14px;height:14px;border-radius:50%;border:1.5px solid #1A1A2E;'
        'background:radial-gradient(circle,#4A90D9 22%,transparent 22%);z-index:3;"></div>'
        '<div style="position:absolute;bottom:8px;right:-5px;width:7px;height:2px;background:#8C939D;z-index:2;"></div>'
        '</div>'
        + wagons
        + '</div>'
    )


def _build_full_header(period_label, snapshot_date, animated=False, data_stale_days=0):
    """Build complete header: title + subtitle + train."""
    stale_badge = ""
    if data_stale_days > 1:
        stale_badge = (
            f' <span style="font-size:11px;color:#E67E22;background:#FFF3E0;padding:1px 8px;'
            f'border-radius:4px;font-weight:600;">⚠ данные отстают на {data_stale_days} дн.</span>'
        )
    return (
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:0;">'
        '<div style="width:4px;height:42px;background:linear-gradient(180deg,#4A90D9,#66BB6A);border-radius:2px;"></div>'
        '<div style="flex:1;">'
        '<div style="display:flex;align-items:baseline;gap:16px;flex-wrap:wrap;">'
        '<div style="font-size:28px;font-weight:800;color:#1A1A2E;line-height:1.2;letter-spacing:-0.3px;">'
        'KPI Партнёрского канала Kaiten</div>'
        f'<div style="font-size:13px;font-weight:600;color:#4A90D9;background:#EBF0FA;'
        f'padding:3px 12px;border-radius:6px;white-space:nowrap;">{period_label}</div>'
        '</div>'
        f'<div style="font-size:14px;color:#8C939D;margin-top:2px;">Партнёрский отдел &middot; '
        f'Снимок данных: {snapshot_date}{stale_badge} &middot; '
        'Обновлено: <span id="local-time">--:--</span></div>'
        '</div>'
        + _build_train_html(animated=animated)
        + '</div>'
    )


# ──────────────────────────────────────────────
# Animated header placeholder (renders BEFORE data load)
# ──────────────────────────────────────────────
_header_placeholder = st.empty()
_is_first_load = "data_loaded" not in st.session_state
_header_placeholder.markdown(
    _build_full_header(
        period_label="Загрузка данных…",
        snapshot_date="—",
        animated=_is_first_load,
    ),
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# Load data
# ──────────────────────────────────────────────
df_pipe = load_pipeline()
df_long = load_longlist()
longlists_by_mgr = load_all_longlists()  # {manager: count}
df_deals = load_deals()
df_timeline = build_touches_timeline(df_pipe)
st.session_state.data_loaded = True

# ──────────────────────────────────────────────
# Compute data period from touch dates
# ──────────────────────────────────────────────
from datetime import date, timedelta

_touch_date_cols_all = [c for c in df_pipe.columns if isinstance(c, str) and c.startswith("touch_") and c.endswith("_date")]
_touch_dates = []
for _col in _touch_date_cols_all:
    _valid = df_pipe[_col].dropna()
    if len(_valid):
        _touch_dates.extend(_valid.tolist())

if _touch_dates:
    _data_min = min(_touch_dates).date() if hasattr(min(_touch_dates), 'date') else min(_touch_dates)
    _data_max = max(_touch_dates).date() if hasattr(max(_touch_dates), 'date') else max(_touch_dates)
    _sorted_dates = sorted(set(d.date() if hasattr(d, 'date') else d for d in _touch_dates))
    if len(_sorted_dates) >= 2 and (_data_max - _sorted_dates[-2]).days > 30:
        _data_max = _sorted_dates[-2]
    # Cap at today — don't show future dates as snapshot
    _data_max = min(_data_max, date.today())
else:
    _data_min = date.today().replace(day=1)
    _data_max = date.today()

# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="font-size:11px;font-weight:700;color:#6B7280;text-transform:uppercase;'
        'letter-spacing:1.2px;margin:4px 0 8px 0;padding-bottom:6px;border-bottom:2px solid #E2E6EC;">Фильтры</div>',
        unsafe_allow_html=True,
    )

    # ── Period selector ──
    st.markdown(
        '<div style="font-size:11px;font-weight:600;color:#6B7280;text-transform:uppercase;'
        'letter-spacing:0.5px;margin-bottom:4px;">Период</div>',
        unsafe_allow_html=True,
    )

    # Quick period buttons
    today = _data_max  # use latest data date as "today"
    quick_periods = {
        "Всё время":     (_data_min, _data_max),
        "Текущий месяц": (today.replace(day=1), _data_max),
        "Прошлый месяц": ((today.replace(day=1) - timedelta(days=1)).replace(day=1),
                          today.replace(day=1) - timedelta(days=1)),
        "Последние 7 дн": (_data_max - timedelta(days=6), _data_max),
        "Последние 14 дн": (_data_max - timedelta(days=13), _data_max),
        "Последние 30 дн": (_data_max - timedelta(days=29), _data_max),
    }

    period_choice = st.radio(
        "Быстрый выбор",
        options=list(quick_periods.keys()) + ["Свой период"],
        index=0,
        horizontal=False,
        label_visibility="collapsed",
    )

    if period_choice == "Свой период":
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            sel_start = st.date_input("От", value=_data_min, min_value=_data_min, max_value=_data_max,
                                       format="DD.MM.YYYY", label_visibility="collapsed")
        with d_col2:
            sel_end = st.date_input("До", value=_data_max, min_value=_data_min, max_value=_data_max,
                                     format="DD.MM.YYYY", label_visibility="collapsed")
        filter_date_start = sel_start
        filter_date_end = sel_end
    else:
        filter_date_start, filter_date_end = quick_periods[period_choice]

    # Clamp to data range
    filter_date_start = max(filter_date_start, _data_min)
    filter_date_end = min(filter_date_end, _data_max)

    period_label = f"{filter_date_start.strftime('%d.%m.%Y')} — {filter_date_end.strftime('%d.%m.%Y')}"

    st.markdown(
        f'<div style="margin:6px 0 12px 0;padding:8px 10px;border-radius:6px;background:#EBF0FA;'
        f'border:1px solid #D0DBEF;text-align:center;">'
        f'<div style="font-size:14px;font-weight:700;color:#1A1A2E;">{period_label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="margin-bottom:4px;border-bottom:1px solid #E2E6EC;padding-bottom:8px;"></div>',
        unsafe_allow_html=True,
    )

    all_managers = sorted(df_pipe["manager"].unique())
    selected_managers = st.multiselect("Менеджер", options=all_managers, default=all_managers)

    all_statuses = sorted(df_pipe["status"].unique())
    selected_statuses = st.multiselect("Статус", options=all_statuses, default=all_statuses)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    if st.button("Обновить данные"):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        '<div style="margin-top:12px;padding-top:8px;border-top:1px solid #E2E6EC;'
        'font-size:11px;color:#A0A7B3;line-height:1.5;">'
        f'Данные: {_data_min.strftime("%d.%m")} — {_data_max.strftime("%d.%m.%Y")}<br>Dashboard v2.1</div>',
        unsafe_allow_html=True,
    )

# ──────────────────────────────────────────────
# Apply filters (manager + status + date period)
# ──────────────────────────────────────────────
# _latest_touch — informational "most recent touch per company" (used elsewhere
# in the UI). The period filter itself checks whether ANY touch falls inside
# the range, so a company touched in both March and April is still included
# when "Прошлый месяц" is selected.
import pandas as pd

_all_touch_cols = [c for c in df_pipe.columns if isinstance(c, str) and c.startswith("touch_") and c.endswith("_date")]
df_pipe["_latest_touch"] = df_pipe[_all_touch_cols].max(axis=1)

_fds = pd.Timestamp(filter_date_start)
_fde = pd.Timestamp(filter_date_end)

_is_full_range = (filter_date_start == _data_min and filter_date_end == _data_max)
if _is_full_range:
    _date_mask = pd.Series(True, index=df_pipe.index)
else:
    _date_mask = pd.Series(False, index=df_pipe.index)
    for _tc in _all_touch_cols:
        _col = df_pipe[_tc]
        _date_mask = _date_mask | ((_col >= _fds) & (_col <= _fde))

mask = (
    df_pipe["manager"].isin(selected_managers)
    & df_pipe["status"].isin(selected_statuses)
    & _date_mask
)
df_filtered = df_pipe[mask]

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def fmt_money(val):
    if val >= 1_000_000:
        return f'{val/1_000_000:.1f}<span class="unit">млн ₽</span>'
    if val >= 1_000:
        return f'{val:,.0f}<span class="unit"> ₽</span>'.replace(",", " ")
    return f'{val:.0f}<span class="unit"> ₽</span>'


def info_tip(desc, formula="", source="", tip_cls=""):
    """Return HTML for (i) tooltip icon."""
    body = desc
    if formula:
        body += f'<span class="tip-formula">{formula}</span>'
    if source:
        body += f'<span class="tip-src">Источник: {source}</span>'
    return (
        f'<span class="info-tip {tip_cls}">'
        f'i<span class="tip-body">{body}</span>'
        f'</span>'
    )


def section_header(text, tooltip=""):
    tip = info_tip(tooltip) if tooltip else ""
    st.markdown(f'<div class="section-hdr">{text} {tip}</div>', unsafe_allow_html=True)


def conv_color_class(pct):
    if pct >= 30: return "green"
    if pct >= 10: return "yellow"
    return "red"


def data_bar_html(val, max_val, bar_cls=""):
    """Inline data bar for table cells."""
    pct = min(val / max_val * 100, 100) if max_val > 0 else 0
    return (
        f'<div class="data-bar">'
        f'<span>{val}</span>'
        f'<div class="bar {bar_cls}" style="width:{max(pct, 3):.0f}%;"></div>'
        f'</div>'
    )


PLOTLY_LAYOUT = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, sans-serif", size=15, color="#2D3748"),
    margin=dict(l=12, r=12, t=6, b=12),
    hoverlabel=dict(bgcolor="white", font_size=14, bordercolor="#E0E3E8"),
)

# ──────────────────────────────────────────────
# HEADER — replace placeholder with real data (static train)
# ──────────────────────────────────────────────
_data_stale_days = (date.today() - _data_max).days if _data_max < date.today() else 0
_header_placeholder.markdown(
    _build_full_header(
        period_label=period_label,
        snapshot_date=filter_date_end.strftime("%d.%m.%Y"),
        animated=False,
        data_stale_days=_data_stale_days,
    ),
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# KPI CARDS
# ──────────────────────────────────────────────
total_in_work = len(df_filtered)
longlist_count = sum(v for m, v in longlists_by_mgr.items() if m in selected_managers)
longlist_breakdown = " | ".join(f"{m.split()[0]}: {c}" for m, c in longlists_by_mgr.items() if m in selected_managers)
deals_count = len(df_deals)
_csm_count = len(df_deals[df_deals["team"].astype(str).str.upper() == "CSM"]) if "team" in df_deals.columns else deals_count
_bdm_count = len(df_deals[df_deals["team"].astype(str).str.upper() == "BDM"]) if "team" in df_deals.columns else 0
total_kp = df_deals["planned_amount"].sum() if not df_deals.empty and "planned_amount" in df_deals.columns else 0
weighted_pipe = df_deals["weighted_amount"].sum() if not df_deals.empty and "weighted_amount" in df_deals.columns else 0

cards = [
    ("В работе", f"{total_in_work}", "", "компаний в пайпе",
     "Количество компаний-партнёров с назначенным менеджером в выбранном периоде.",
     "COUNT(компании WHERE менеджер ≠ пусто AND дата в периоде)",
     "Общий пайп"),
    ("Лонглист", f"{longlist_count}", "alert", "не обработан",
     f"Компании в листах ожидания, ещё не взятые в работу.<br><b>Разбивка:</b> {longlist_breakdown}",
     "SUM(строк) по всем вкладкам «Лонглист *»",
     "Лонглист Белкин + Лонглист Баксанова"),
    ("Сделок", f"{deals_count}", "", f"CSM: {_csm_count} · BDM: {_bdm_count}",
     f"Активные сделки с партнёрами. <b>CSM</b> — старые партнёры (Ангелина). <b>BDM</b> — новые (Ирина, Никита, Павел).",
     "COUNT(строк) GROUP BY Команда",
     "Сделки партнёров CSM/KAM/BDM"),
    ("Сумма КП", fmt_money(total_kp), "money", "плановая",
     "Суммарная плановая стоимость всех активных сделок (коммерческих предложений).",
     "SUM(Плановая сумма) по всем сделкам",
     "Сделки партнёров → кол. «Плановая сумма»"),
    ("Взвеш. пайплайн", fmt_money(weighted_pipe), "money", "с учётом вероятности",
     "Суммарная стоимость сделок, скорректированная на вероятность закрытия. Показывает реалистичный прогноз выручки.",
     "SUM(Плановая сумма × Вероятность / 100)",
     "Сделки партнёров → кол. «Плановая сумма» × «Вероятность»"),
]

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
kpi_cols = st.columns(5, gap="small")
for i, (label, value, cls, sub, tip_desc, tip_formula, tip_src) in enumerate(cards):
    tip_class = "tip-left" if i >= 3 else ""
    with kpi_cols[i]:
        st.markdown(
            f'<div class="kpi-card {cls}">'
            f'<div class="kpi-label">{label} {info_tip(tip_desc, tip_formula, tip_src, tip_class)}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'<div class="kpi-sub">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ──────────────────────────────────────────────
# PROGRESS TO PLAN
# ──────────────────────────────────────────────
section_header("Прогресс к плану",
    "Факт vs цель по ключевым KPI. Q1 = янв–мар, Q2 = апр–июн. "
    '<b>Источник целей:</b> Каскад KPI B-сегмента Kaiten v2.2'
)

# Compute actuals
_active_partners = len(df_filtered[df_filtered["status"].isin(["Договор", "Подписан"])])
_leads_csm = _csm_count
_leads_bdm = _bdm_count
_pipeline_kp = total_kp
_paid_mask = df_deals["deal_stage"].astype(str).str.lower().str.contains("оплачено", na=False) if not df_deals.empty else pd.Series(dtype=bool)
_revenue_fact = df_deals.loc[_paid_mask, "planned_amount"].sum() if not df_deals.empty else 0
_mrr_fact = df_deals.loc[_paid_mask, "mrr"].sum() if not df_deals.empty and "mrr" in df_deals.columns else 0

_actuals = [
    ("active_partners", _active_partners),
    ("leads_csm", _leads_csm),
    ("leads_bdm", _leads_bdm),
    ("pipeline_kp", _pipeline_kp),
    ("revenue", _revenue_fact),
    ("mrr", _mrr_fact),
]


def _build_progress_html(targets, actuals, disabled=False):
    html_out = ""
    opacity = "0.45" if disabled else "1"
    for key, actual in actuals:
        t = targets.get(key, {})
        target = t.get("target", 1)
        label = t.get("label", key)
        is_money = t.get("fmt") == "money"
        if disabled:
            pct = 0
            bar_color = "#B0BEC5"
        else:
            pct = min(actual / target * 100, 100) if target > 0 else 0
            bar_color = "#66BB6A" if pct >= 70 else ("#FFB74D" if pct >= 40 else "#E57373")
        if is_money:
            actual_str = _short_money(actual, "м")
            target_str = _short_money(target, "м")
        else:
            actual_str = str(actual)
            target_str = str(target)
        right_text = (
            f'<span style="font-size:12px;color:#B0BEC5;">цель: {target_str}</span>'
            if disabled else
            f'<span style="font-size:12px;color:#6B7280;">{actual_str}/{target_str} '
            f'<span style="font-weight:700;color:{bar_color};">{pct:.0f}%</span></span>'
        )
        html_out += (
            f'<div style="margin-bottom:7px;opacity:{opacity};">'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2px;">'
            f'<span style="font-size:12px;font-weight:600;color:#2D3748;">{label}</span>'
            f'{right_text}'
            f'</div>'
            f'<div style="background:#E8ECF0;border-radius:4px;height:7px;overflow:hidden;">'
            f'<div style="width:{pct:.0f}%;height:100%;background:{bar_color};border-radius:4px;"></div>'
            f'</div></div>'
        )
    return html_out


# Determine current quarter
from datetime import datetime as _dt_cls
_now = _dt_cls.now()
_current_q = (_now.month - 1) // 3 + 1  # 1=Q1, 2=Q2, ...
_q1_disabled = _current_q < 1  # never true, kept for symmetry
_q2_disabled = _current_q < 2  # Q2 not started yet

def _quarter_header(label, state):
    """state ∈ {'current','past','future'}"""
    if state == "current":
        title_color = "#4A90D9"
        badge = (' <span style="font-size:10px;font-weight:600;color:#fff;background:#4A90D9;'
                 'border-radius:4px;padding:1px 6px;margin-left:6px;">текущий</span>')
    elif state == "past":
        title_color = "#8A95A5"
        badge = (' <span style="font-size:10px;font-weight:500;color:#6B7280;background:#E8ECF0;'
                 'border-radius:4px;padding:1px 6px;margin-left:6px;">завершён</span>')
    else:  # future
        title_color = "#8A95A5"
        badge = (' <span style="font-size:10px;font-weight:500;color:#fff;background:#B0BEC5;'
                 'border-radius:4px;padding:1px 6px;margin-left:6px;">период не начался</span>')
    return f'<div style="font-size:13px;font-weight:700;color:{title_color};margin-bottom:6px;">{label}{badge}</div>'

_q1_state = "current" if _current_q == 1 else ("past" if _current_q > 1 else "future")
_q2_state = "current" if _current_q == 2 else ("past" if _current_q > 2 else "future")

col_q1, col_q2 = st.columns(2, gap="medium")
with col_q1:
    st.markdown(
        _quarter_header("Q1 2026 (янв–мар)", _q1_state)
        + _build_progress_html(TARGETS_Q1, _actuals, disabled=(_q1_state == "future")),
        unsafe_allow_html=True,
    )
with col_q2:
    st.markdown(
        _quarter_header("Q2 2026 (апр–июн)", _q2_state)
        + _build_progress_html(TARGETS_Q2, _actuals, disabled=(_q2_state == "future")),
        unsafe_allow_html=True,
    )

# ──────────────────────────────────────────────
# FUNNEL
# ──────────────────────────────────────────────
section_header("Воронка привлечения партнёров",
    "Распределение компаний по этапам воронки привлечения. "
    "Показывает сколько партнёров на каждом этапе и конверсию между ними. "
    '<b>Формула конверсии:</b> кол-во на следующем этапе / кол-во на текущем × 100%. '
    '<b>Источник:</b> Общий пайп → кол. «Текущий статус»'
)

status_counts = df_filtered["status"].value_counts()

MAIN_FUNNEL = ["Нет ОС", "На рассмотрении", "Договор", "Подписан"]
funnel_data = [{"status": s, "count": status_counts.get(s, 0)} for s in MAIN_FUNNEL]

SIDE_STATUSES = ["Не интересно", "Не обрабатываем", "Прочее"]
side_data = [{"status": s, "count": status_counts.get(s, 0)} for s in SIDE_STATUSES if status_counts.get(s, 0) > 0]
side_colors_map = {"Не интересно": "#E57373", "Не обрабатываем": "#CE93D8", "Прочее": "#B0BEC5"}

col_funnel, col_conv = st.columns([3, 2], gap="medium")

with col_funnel:
    funnel_colors_map = {"Нет ОС": "#90A4AE", "На рассмотрении": "#FFB74D", "Договор": "#4FC3F7", "Подписан": "#66BB6A"}
    all_bars = funnel_data + side_data
    max_count = max((r["count"] for r in all_bars), default=1) or 1

    fig_funnel = go.Figure()
    for row in funnel_data:
        pct_of_first = (row["count"] / funnel_data[0]["count"] * 100) if funnel_data[0]["count"] > 0 else 0
        bar_color = funnel_colors_map.get(row["status"], "#90A4AE")
        is_small = row["count"] < max_count * 0.12
        fig_funnel.add_trace(go.Bar(
            y=[row["status"]], x=[row["count"]], orientation="h",
            marker_color=bar_color,
            text=f'<b>{row["count"]}</b>  ({pct_of_first:.0f}%)',
            textposition="outside" if is_small else "inside",
            textfont=dict(size=13, color="#2D3748" if is_small else "white"),
            showlegend=False,
            hovertemplate=f'{row["status"]}: {row["count"]} ({pct_of_first:.1f}%)<extra></extra>',
        ))
    for row in side_data:
        bar_color = side_colors_map.get(row["status"], "#B0BEC5")
        is_small = row["count"] < max_count * 0.12
        fig_funnel.add_trace(go.Bar(
            y=[row["status"]], x=[row["count"]], orientation="h",
            marker_color=bar_color, marker_pattern_shape="/",
            text=f'<b>{row["count"]}</b>',
            textposition="outside" if is_small else "inside",
            textfont=dict(size=12, color="#2D3748" if is_small else "white"),
            showlegend=False,
            hovertemplate=f'{row["status"]}: {row["count"]}<extra></extra>',
        ))

    total_bars = len(funnel_data) + len(side_data)
    fig_funnel.update_layout(
        **{**PLOTLY_LAYOUT, "margin": dict(l=0, r=55, t=4, b=4)},
        height=max(200, total_bars * 46),
        barmode="overlay",
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, autorange="reversed", tickfont=dict(size=12)),
        bargap=0.22,
    )
    st.plotly_chart(fig_funnel, use_container_width=True)

with col_conv:
    st.markdown(
        '<p style="font-size:10.5px;font-weight:700;color:#8C939D;text-transform:uppercase;'
        'letter-spacing:0.5px;margin:0 0 6px 0;">Конверсия между этапами</p>',
        unsafe_allow_html=True,
    )
    for i in range(len(funnel_data) - 1):
        cur, nxt = funnel_data[i]["count"], funnel_data[i + 1]["count"]
        rate = (nxt / cur * 100) if cur > 0 else 0
        st.markdown(
            f'<div class="conv-row">'
            f'<div class="conv-pct {conv_color_class(rate)}">{rate:.1f}%</div>'
            f'<div class="conv-detail">{funnel_data[i]["status"]} &rarr; {funnel_data[i+1]["status"]}'
            f'<br><span style="color:#A0A7B3;font-size:11px;">{cur} &rarr; {nxt}</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    first, last = funnel_data[0]["count"], funnel_data[-1]["count"]
    overall = (last / first * 100) if first > 0 else 0
    st.markdown(
        f'<div class="conv-total">'
        f'<div class="pct">{overall:.1f}%</div>'
        f'<div class="lbl">Общая конверсия &middot; {first} &rarr; {last}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if side_data:
        st.markdown(
            '<p style="font-size:10.5px;font-weight:700;color:#8C939D;text-transform:uppercase;'
            'letter-spacing:0.5px;margin:8px 0 4px 0;">Отсев</p>',
            unsafe_allow_html=True,
        )
        for row in side_data:
            clr = side_colors_map.get(row["status"], "#B0BEC5")
            st.markdown(
                f'<div class="conv-row" style="border-left:3px solid {clr};">'
                f'<div style="font-size:16px;font-weight:700;color:{clr};min-width:35px;">{row["count"]}</div>'
                f'<div class="conv-detail">{row["status"]}</div></div>',
                unsafe_allow_html=True,
            )

# ──────────────────────────────────────────────
# BDM METRICS
# ──────────────────────────────────────────────
section_header("Метрики по менеджерам",
    "Разбивка пайплайна по BDM-менеджерам. "
    '<b>Конверсия</b> = (Договор + Подписан) / Всего × 100%. '
    '<b>Источник:</b> Общий пайп → кол. «Ответственный» × «Текущий статус»'
)

col_chart, col_table = st.columns([2, 3], gap="medium")

with col_chart:
    manager_status = df_filtered.groupby(["manager", "status"]).size().reset_index(name="count")
    fig_mgr = px.bar(
        manager_status, y="manager", x="count", color="status",
        color_discrete_map=STATUS_COLORS, barmode="stack", orientation="h",
        labels={"manager": "", "count": "Компаний", "status": "Статус"},
    )
    fig_mgr.update_layout(
        **PLOTLY_LAYOUT, height=260,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font_size=10),
        xaxis=dict(showgrid=True, gridcolor="#F0F1F3", zeroline=False),
        yaxis=dict(showgrid=False, autorange="reversed"),
        bargap=0.28,
    )
    # Show labels: outside for small segments, inside for large
    for trace in fig_mgr.data:
        trace.texttemplate = "%{x}"
        trace.textfont = dict(size=11)
        # Use 'auto' so Plotly picks inside/outside based on bar size
        trace.textposition = "auto"
        trace.insidetextanchor = "middle"
    st.plotly_chart(fig_mgr, use_container_width=True)

with col_table:
    summary_rows = []
    for mgr in selected_managers:
        d = df_filtered[df_filtered["manager"] == mgr]
        total = len(d)
        reviewing = len(d[d["status"] == "На рассмотрении"])
        contract = len(d[d["status"].isin(["Договор", "Подписан"])])
        no_resp = len(d[d["status"] == "Нет ОС"])
        conv = (contract / total * 100) if total > 0 else 0
        ll = longlists_by_mgr.get(mgr, 0)
        summary_rows.append((mgr, total, reviewing, contract, no_resp, conv, ll))

    t_total = sum(r[1] for r in summary_rows)
    t_rev = sum(r[2] for r in summary_rows)
    t_con = sum(r[3] for r in summary_rows)
    t_no = sum(r[4] for r in summary_rows)
    t_conv = (t_con / t_total * 100) if t_total > 0 else 0
    t_ll = sum(r[6] for r in summary_rows)
    max_total = max((r[1] for r in summary_rows), default=1) or 1

    html_rows = ""
    for mgr, total, reviewing, contract, no_resp, conv, ll in summary_rows:
        contract_cls = "zero" if contract == 0 else "ok"
        conv_cls = "zero" if conv == 0 else ("ok" if conv >= 5 else "low")
        ll_cls = "low" if ll > 0 else ""
        html_rows += (
            f'<tr>'
            f'<td style="white-space:nowrap;"><strong>{mgr.split()[0]}</strong>'
            f' <span style="color:#A0A7B3;">{" ".join(mgr.split()[1:])}</span></td>'
            f'<td class="num">{data_bar_html(total, max_total)}</td>'
            f'<td class="num">{reviewing}</td>'
            f'<td class="num {contract_cls}">{contract}</td>'
            f'<td class="num">{no_resp}</td>'
            f'<td class="num {conv_cls}">{conv:.1f}%</td>'
            f'<td class="num {ll_cls}">{ll if ll > 0 else "—"}</td>'
            f'</tr>'
        )

    _tip_total = info_tip("Общее кол-во компаний в работе у менеджера.", "", "Общий пайп")
    _tip_review = info_tip("Статус «На рассмотрении».", "", "Общий пайп → статус")
    _tip_deal = info_tip("Статус «Договор» или «Подписан».", "", "Общий пайп → статус")
    _tip_noos = info_tip("Нет ответа на касания.", "", "Общий пайп → статус", "tip-left")
    _tip_conv = info_tip("(Договор + Подписан) / Всего × 100%", "", "расчётная", "tip-left")
    _tip_ll = info_tip("Компании в лонглисте менеджера, ещё не взятые в работу.", "COUNT(строк)", "Лонглист *", "tip-left")

    st.markdown(f"""
    <table class="styled-table">
        <thead><tr>
            <th>Менеджер</th><th class="num">Всего {_tip_total}</th><th class="num">Рассмотр. {_tip_review}</th>
            <th class="num">Договор {_tip_deal}</th><th class="num">Нет ОС {_tip_noos}</th><th class="num">Конв. {_tip_conv}</th>
            <th class="num">Лонглист {_tip_ll}</th>
        </tr></thead>
        <tbody>
            {html_rows}
            <tr class="row-total">
                <td>Итого</td><td class="num">{t_total}</td><td class="num">{t_rev}</td>
                <td class="num">{t_con}</td><td class="num">{t_no}</td><td class="num">{t_conv:.1f}%</td>
                <td class="num">{t_ll}</td>
            </tr>
        </tbody>
    </table>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# DISCIPLINE & DATA QUALITY
# ──────────────────────────────────────────────
section_header("Дисциплина и качество данных",
    "Управленческие метрики по дисциплине ведения CRM. "
    "Помогают выявить пробелы в заполнении данных, "
    "оценить интенсивность работы и скорость конверсии по каждому менеджеру."
)

_dq_touch_date_cols = sorted(
    [c for c in df_filtered.columns if isinstance(c, str) and c.startswith("touch_") and c.endswith("_date")],
    key=lambda c: int(c.split("_")[1]),
    reverse=True,
)
_dq_touch_result_cols = [c.replace("_date", "_result") for c in _dq_touch_date_cols]

_dq_rows = []
for mgr in selected_managers:
    d = df_filtered[df_filtered["manager"] == mgr]
    total = len(d)
    if total == 0:
        _dq_rows.append((mgr, 0, pd.NaT, 0, 0, 0, 0.0, 0.0, None, 0, 0.0, None, None))
        continue

    # 1. Last update date per manager (most recent touch across all their companies)
    mgr_last_touch = pd.NaT
    for _, r in d.iterrows():
        for dc in _dq_touch_date_cols:
            dv = r.get(dc)
            if pd.notna(dv):
                if pd.isna(mgr_last_touch) or dv > mgr_last_touch:
                    mgr_last_touch = dv
                break

    # 2. Empty results: touches that have a date but no result text
    empty_results = 0
    total_touches = 0
    for _, r in d.iterrows():
        for dc, rc in zip(_dq_touch_date_cols, _dq_touch_result_cols):
            dv = r.get(dc)
            if pd.notna(dv):
                total_touches += 1
                rv = r.get(rc, "")
                rv_str = str(rv).strip() if pd.notna(rv) else ""
                if rv_str.lower() in ("", "nan", "nat"):
                    empty_results += 1

    # 3. Companies in "Прочее" status
    prochee_count = len(d[d["status"] == "Прочее"])

    # 4. Average touches per company
    avg_touches = total_touches / total if total > 0 else 0

    # 5. Cadence buckets per company based on most recent touch:
    #    - stalled: 8–30 days since last touch (cadence slip, not abandoned)
    #    - abandoned: >30 days since last touch OR no touches at all (really dropped)
    stalled_count = 0
    abandoned_count = 0
    for _, r in d.iterrows():
        last_dt = pd.NaT
        for dc in _dq_touch_date_cols:
            dv = r.get(dc)
            if pd.notna(dv):
                last_dt = dv
                break
        if pd.isna(last_dt):
            abandoned_count += 1
            continue
        days = (pd.Timestamp.now() - last_dt).days
        if days > 30:
            abandoned_count += 1
        elif days > 7:
            stalled_count += 1
    stalled_pct = stalled_count / total * 100 if total > 0 else 0
    abandoned_pct = abandoned_count / total * 100 if total > 0 else 0

    # 6. Cadence regularity — how evenly the manager returns to active companies:
    #    - cadence_interval: avg gap (days) between consecutive touches per active
    #      company (≥2 touches, last touch ≤30 days ago), averaged across companies
    #    - cadence_cv: coefficient of variation of manager's weekly touch count
    #      (low = steady workload, high = bursty)
    import statistics

    gaps_per_company = []
    _now_ts = pd.Timestamp.now()
    for _, r in d.iterrows():
        _dates = sorted([r[dc] for dc in _dq_touch_date_cols if pd.notna(r.get(dc))])
        if len(_dates) < 2:
            continue
        if (_now_ts - _dates[-1]).days > 30:
            continue
        _gaps = [(_dates[i] - _dates[i - 1]).days for i in range(1, len(_dates))]
        if _gaps:
            gaps_per_company.append(sum(_gaps) / len(_gaps))

    cadence_interval = (sum(gaps_per_company) / len(gaps_per_company)) if gaps_per_company else None

    _weekly_counts = {}
    for _, r in d.iterrows():
        for dc in _dq_touch_date_cols:
            dv = r.get(dc)
            if pd.notna(dv):
                _wk = dv.to_period("W").start_time
                _weekly_counts[_wk] = _weekly_counts.get(_wk, 0) + 1
    _weekly_vals = list(_weekly_counts.values())
    if len(_weekly_vals) >= 2 and sum(_weekly_vals) > 0:
        _w_mean = sum(_weekly_vals) / len(_weekly_vals)
        _w_std = statistics.pstdev(_weekly_vals)
        cadence_cv = _w_std / _w_mean if _w_mean > 0 else None
    else:
        cadence_cv = None

    # 7. Funnel velocity: avg days from first touch to Договор/Подписан
    converted = d[d["status"].isin(["Договор", "Подписан"])]
    velocity_days = None
    if len(converted) > 0:
        durations = []
        for _, r in converted.iterrows():
            # First touch = earliest date
            first_touch = pd.NaT
            for dc in reversed(_dq_touch_date_cols):
                dv = r.get(dc)
                if pd.notna(dv):
                    first_touch = dv
            # Last touch = most recent date
            last_touch = pd.NaT
            for dc in _dq_touch_date_cols:
                dv = r.get(dc)
                if pd.notna(dv):
                    last_touch = dv
                    break
            if pd.notna(first_touch) and pd.notna(last_touch):
                durations.append((last_touch - first_touch).days)
        if durations:
            velocity_days = sum(durations) / len(durations)

    _dq_rows.append((mgr, total, mgr_last_touch, empty_results, prochee_count, stalled_count, stalled_pct, avg_touches, velocity_days, abandoned_count, abandoned_pct, cadence_interval, cadence_cv))

# Render table
_dq_html_rows = ""
for row in _dq_rows:
    mgr, total, last_touch, empty_results, prochee, stalled, stalled_pct, avg_t, vel, abandoned, abandoned_pct, cadence_interval, cadence_cv = row

    clr = MANAGER_COLORS.get(mgr, "#90A4AE")

    # Last update formatting
    if pd.notna(last_touch):
        lt_days = (pd.Timestamp.now() - last_touch).days
        lt_str = last_touch.strftime("%d.%m")
        lt_cls = "zero" if lt_days > 7 else ("low" if lt_days > 3 else "ok")
        lt_html = f'<span class="{lt_cls}">{lt_str}</span> <span style="font-size:11px;color:#A0A7B3;">({lt_days}д)</span>'
    else:
        lt_html = '<span class="zero">нет данных</span>'

    # Empty results
    er_cls = "zero" if empty_results > 3 else ("low" if empty_results > 0 else "ok")
    er_html = f'<span class="{er_cls}">{empty_results}</span>'

    # Прочее
    pr_cls = "low" if prochee > 0 else ""
    pr_html = f'<span class="{pr_cls}">{prochee}</span>' if prochee > 0 else "—"

    # Avg touches
    at_cls = "zero" if avg_t < 1.5 else ("low" if avg_t < 2.5 else "ok")
    at_html = f'<span class="{at_cls}">{avg_t:.1f}</span>'

    # Stalled % (8–30 days — cadence slip)
    sp_cls = "zero" if stalled_pct > 50 else ("low" if stalled_pct > 25 else "ok")
    sp_html = f'<span class="{sp_cls}">{stalled_pct:.0f}%</span> <span style="font-size:11px;color:#A0A7B3;">({stalled})</span>'

    # Abandoned % (>30 days or no touches — real drop-off)
    ab_cls = "zero" if abandoned_pct > 20 else ("low" if abandoned_pct > 5 else "ok")
    if abandoned > 0:
        ab_html = f'<span class="{ab_cls}">{abandoned_pct:.0f}%</span> <span style="font-size:11px;color:#A0A7B3;">({abandoned})</span>'
    else:
        ab_html = '<span class="ok">—</span>'

    # Cadence regularity: avg interval between touches (active companies) + weekly CV
    if cadence_interval is None:
        cad_html = '<span style="color:#A0A7B3;">—</span>'
    else:
        cad_cls = "ok" if cadence_interval <= 14 else ("low" if cadence_interval <= 30 else "zero")
        if cadence_cv is not None:
            cv_part = f' <span style="font-size:11px;color:#A0A7B3;">(CV {cadence_cv:.1f})</span>'
        else:
            cv_part = ""
        cad_html = f'<span class="{cad_cls}">{cadence_interval:.0f}д</span>{cv_part}'

    # Velocity
    if vel is not None:
        v_cls = "ok" if vel < 14 else ("low" if vel < 30 else "zero")
        vel_html = f'<span class="{v_cls}">{vel:.0f}д</span>'
    else:
        vel_html = '<span style="color:#A0A7B3;">—</span>'

    _dq_html_rows += (
        f'<tr>'
        f'<td style="white-space:nowrap;">'
        f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{clr};margin-right:6px;vertical-align:middle;"></span>'
        f'<strong>{mgr.split()[0]}</strong>'
        f' <span style="color:#A0A7B3;">{" ".join(mgr.split()[1:])}</span></td>'
        f'<td class="num">{lt_html}</td>'
        f'<td class="num">{er_html}</td>'
        f'<td class="num">{pr_html}</td>'
        f'<td class="num">{at_html}</td>'
        f'<td class="num">{sp_html}</td>'
        f'<td class="num">{ab_html}</td>'
        f'<td class="num">{cad_html}</td>'
        f'<td class="num">{vel_html}</td>'
        f'</tr>'
    )

# Totals
_dq_total_empty = sum(r[3] for r in _dq_rows)
_dq_total_prochee = sum(r[4] for r in _dq_rows)
_dq_total_stalled = sum(r[5] for r in _dq_rows)
_dq_total_abandoned = sum(r[9] for r in _dq_rows)
_dq_total_companies = sum(r[1] for r in _dq_rows)
_dq_total_stalled_pct = (_dq_total_stalled / _dq_total_companies * 100) if _dq_total_companies > 0 else 0
_dq_total_abandoned_pct = (_dq_total_abandoned / _dq_total_companies * 100) if _dq_total_companies > 0 else 0

_tip_last_upd = info_tip("Дата последнего касания менеджера (по всем компаниям). Красный — обновление > 7 дней назад.", "", "Общий пайп → touch dates")
_tip_empty_res = info_tip("Количество касаний, у которых есть дата, но не заполнен результат. Признак некачественного ведения CRM.", "", "Общий пайп → result")
_tip_prochee = info_tip("Компании, чей статус не распознан (попал в «Прочее»). Нужно проставить корректный статус.", "", "Общий пайп → статус")
_tip_avg_touch = info_tip("Среднее количество касаний на одну компанию. Ниже 1.5 — слабая проработка.", "SUM(касаний) / COUNT(компаний)", "Общий пайп", "tip-left")
_tip_stalled_pct = info_tip("Доля компаний, где последнее касание было 8–30 дней назад. Просадка каденции — нужно вернуться ко второму кругу.", "COUNT(8–30дн) / Всего × 100%", "Общий пайп", "tip-left")
_tip_abandoned = info_tip("Доля компаний без касаний более 30 дней (или совсем без касаний). Реальная заброшенность — требует разбора: работать или закрывать.", "COUNT(>30дн ∪ нет касаний) / Всего × 100%", "Общий пайп", "tip-left")
_tip_cadence = info_tip("Насколько ровно менеджер возвращается к активным компаниям. Основное число — средний интервал (дн) между последовательными касаниями, усреднённый по компаниям с ≥2 касаниями и свежим (<30д) последним касанием. CV в скобках — коэффициент вариации числа касаний по неделям (низкий = ровно, высокий = вспышками).", "AVG(gap_per_company); CV = stdev(touches/week) / mean", "Общий пайп → touch dates", "tip-left")
_tip_velocity = info_tip("Среднее число дней от первого касания до статуса «Договор / Подписан». Чем меньше — тем быстрее конвертация.", "AVG(last_touch − first_touch) для Договор/Подписан", "Общий пайп", "tip-left")

st.markdown(f"""
<table class="styled-table">
    <thead><tr>
        <th>Менеджер</th>
        <th class="num">Посл. обновл. {_tip_last_upd}</th>
        <th class="num">Пустые рез-ты {_tip_empty_res}</th>
        <th class="num">Без статуса {_tip_prochee}</th>
        <th class="num">Касан./комп. {_tip_avg_touch}</th>
        <th class="num">Зависшие 8–30д {_tip_stalled_pct}</th>
        <th class="num">Заброшено >30д {_tip_abandoned}</th>
        <th class="num">Каденция {_tip_cadence}</th>
        <th class="num">Скор. воронки {_tip_velocity}</th>
    </tr></thead>
    <tbody>
        {_dq_html_rows}
        <tr class="row-total">
            <td>Итого</td>
            <td class="num"></td>
            <td class="num">{_dq_total_empty}</td>
            <td class="num">{_dq_total_prochee}</td>
            <td class="num"></td>
            <td class="num">{_dq_total_stalled_pct:.0f}% ({_dq_total_stalled})</td>
            <td class="num">{_dq_total_abandoned_pct:.0f}% ({_dq_total_abandoned})</td>
            <td class="num"></td>
            <td class="num"></td>
        </tr>
    </tbody>
</table>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# STALLED COMPANIES expander
# ──────────────────────────────────────────────
# Pre-compute stalled data before expander (for header)
_touch_date_cols = sorted(
    [c for c in df_filtered.columns if isinstance(c, str) and c.startswith("touch_") and c.endswith("_date")],
    key=lambda c: int(c.split("_")[1]),
    reverse=True,
)
_touch_result_cols = [c.replace("_date", "_result") for c in _touch_date_cols]


def _safe_val(series, key, default=""):
    """Safely get scalar from a Series, handling duplicates."""
    try:
        v = series[key]
        if isinstance(v, pd.Series):
            v = v.iloc[0]
        return v
    except (KeyError, IndexError):
        return default


stalled_rows = []
for _, r in df_filtered.iterrows():
    last_date = None
    last_result = ""
    for dc, rc in zip(_touch_date_cols, _touch_result_cols):
        dv = _safe_val(r, dc)
        if pd.notna(dv):
            last_date = dv
            rv = _safe_val(r, rc, "")
            rv_str = str(rv).strip() if pd.notna(rv) else ""
            last_result = rv_str if rv_str.lower() not in ("", "nan", "nat") else ""
            break
    days_since = (pd.Timestamp.now() - last_date).days if pd.notna(last_date) else 999
    stalled_rows.append({
        "company": _safe_val(r, "company", ""),
        "manager": _safe_val(r, "manager", ""),
        "last_touch": last_date,
        "last_result": str(last_result)[:50],
        "days_since": days_since,
        "status": _safe_val(r, "status", ""),
    })

df_stalled = pd.DataFrame(stalled_rows).sort_values("days_since", ascending=False)
df_stalled_show = df_stalled[df_stalled["days_since"] > 7].head(30)

# Build summary for expander label
_stalled_total = len(df_stalled_show)
if _stalled_total > 0:
    _by_mgr = df_stalled_show.groupby("manager").size()
    _mgr_parts = " · ".join(f"{m.split()[0]}: {c}" for m, c in _by_mgr.items())
    _stalled_label = f"Компании без касаний — требуют внимания ({_stalled_total} шт: {_mgr_parts})"
else:
    _stalled_label = "Компании без касаний — все активны"

with st.expander(_stalled_label, expanded=False):

    if df_stalled_show.empty:
        st.markdown('<div style="color:#6B7280;padding:8px;">Все компании активны (касания < 7 дней назад)</div>', unsafe_allow_html=True)
    else:
        s_rows = ""
        for _, sr in df_stalled_show.iterrows():
            d = sr["days_since"]
            d_cls = "zero" if d > 30 else ("low" if d > 14 else "")
            dt_str = sr["last_touch"].strftime("%d.%m") if pd.notna(sr["last_touch"]) else "нет"
            clr = MANAGER_COLORS.get(sr["manager"], "#90A4AE")
            s_rows += (
                f'<tr>'
                f'<td>{sr["company"][:35]}</td>'
                f'<td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
                f'background:{clr};margin-right:4px;vertical-align:middle;"></span>{sr["manager"].split()[0]}</td>'
                f'<td>{dt_str}</td>'
                f'<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{_html.escape(sr["last_result"])}</td>'
                f'<td class="num {d_cls}"><b>{d}д</b></td>'
                f'</tr>'
            )
        st.markdown(f"""
        <table class="styled-table">
            <thead><tr>
                <th>Компания</th><th>Менеджер</th><th>Посл. касание</th>
                <th>Результат</th><th class="num">Дней без касания</th>
            </tr></thead>
            <tbody>{s_rows}</tbody>
        </table>
        """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# DEALS PIPELINE — full width, table + chart side by side
# ──────────────────────────────────────────────
section_header("Пайплайн сделок партнёров",
    "Активные сделки с партнёрами. "
    '<b>Сумма</b> — плановая стоимость сделки (КП). '
    '<b>Вероятность</b> — оценка шанса закрытия. '
    '<b>Взвешенная сумма</b> = Сумма × Вероятность / 100. '
    '⚠ — наличие риска или блокера. '
    '<b>Источник:</b> вкладка «Сделки партнёров»'
)

# Deals have different managers (KAM/sales), not BDM — no manager filtering
df_deals_filtered = df_deals

if df_deals_filtered.empty:
    st.markdown(
        '<div class="panel" style="text-align:center;color:#8C939D;padding:20px;">Нет данных по сделкам</div>',
        unsafe_allow_html=True,
    )
else:
    stage_colors = {
        "Новый лид": ("#E3F2FD", "#1565C0"), "Discovery": ("#FFF3E0", "#E65100"),
        "КП отправлено": ("#E8F5E9", "#2E7D32"), "Переговоры": ("#F3E5F5", "#6A1B9A"),
        "Закрыто": ("#E8F5E9", "#1B5E20"), "Проведено демо": ("#E0F7FA", "#00838F"),
        "Направлено КП": ("#F1F8E9", "#558B2F"),
    }
    LOST_KEYWORDS = ["проиграно"]
    PAID_KEYWORDS = ["оплачено"]

    def deal_badge(stage):
        stage_str = str(stage) if pd.notna(stage) else ""
        is_lost = any(kw in stage_str.lower() for kw in LOST_KEYWORDS)
        is_paid = any(kw in stage_str.lower() for kw in PAID_KEYWORDS)
        if is_lost:
            bg, fg = "#FFEBEE", "#C62828"
        elif is_paid:
            bg, fg = "#E8F5E9", "#1B5E20"
        else:
            bg, fg = stage_colors.get(stage_str, ("#F0F2F6", "#5A6270"))
        return f'<span class="badge" style="background:{bg};color:{fg};">{stage}</span>'

    def prob_cell(val):
        cls = "ok" if val >= 50 else ("low" if val >= 20 else "zero")
        return f'<span class="{cls}">{val:.0f}%</span>'

    deal_rows = ""
    total_planned = 0
    total_weighted = 0
    for _, row in df_deals_filtered.iterrows():
        partner = row.get("partner", "—")
        client = row.get("client", "—")
        stage = row.get("deal_stage", "—")
        planned = row.get("planned_amount", 0)
        prob = row.get("probability", 0)
        risk = row.get("risk", "")
        team = str(row.get("team", "")).strip().upper() if pd.notna(row.get("team")) else ""
        team_badge = ""
        if team == "BDM":
            team_badge = '<span class="badge" style="background:#FFF3E0;color:#E65100;font-size:10px;padding:1px 6px;margin-left:4px;">BDM</span>'
        elif team == "CSM":
            team_badge = '<span class="badge" style="background:#E3F2FD;color:#1565C0;font-size:10px;padding:1px 6px;margin-left:4px;">CSM</span>'
        total_planned += planned
        total_weighted += planned * prob / 100
        planned_fmt = f'{planned:,.0f} ₽'.replace(",", " ")

        risk_icon = ""
        if pd.notna(risk) and str(risk).strip() and str(risk).strip().lower() != "nan":
            import html as _html
            risk_text = _html.escape(str(risk).strip())
            risk_icon = (
                f' <span class="info-tip" style="background:#FFF3E0;color:#E65100;width:18px;height:18px;font-size:11px;">'
                f'⚠<span class="tip-body" style="width:220px;">'
                f'<b>Риск / блокер:</b><br>{risk_text}'
                f'<span class="tip-src">Источник: Сделки партнёров → «Риск / блокер»</span>'
                f'</span></span>'
            )

        stage_str = str(stage) if pd.notna(stage) else ""
        is_lost = any(kw in stage_str.lower() for kw in LOST_KEYWORDS)
        is_paid = any(kw in stage_str.lower() for kw in PAID_KEYWORDS)
        if is_lost:
            row_style = ' style="opacity:0.5;"'
        elif is_paid:
            row_style = ' style="background:#F1F8E9;"'
        else:
            row_style = ""
        paid_icon = ' <span style="font-size:14px;" title="Оплачено">💰</span>' if is_paid else ""

        # Velocity: days in pipeline
        days = row.get("days_in_pipeline", None)
        if pd.notna(days):
            days_int = int(days)
            days_cls = "ok" if days_int < 14 else ("low" if days_int <= 30 else "zero")
            days_html = f'<span class="{days_cls}">{days_int}д</span>'
        else:
            days_html = "—"

        # Next step
        nstep = row.get("next_step", "")
        nstep_date = row.get("next_step_date", None)
        overdue = row.get("next_step_overdue", False)
        nstep_str = str(nstep).strip() if pd.notna(nstep) and str(nstep).strip().lower() != "nan" else ""
        if nstep_str:
            ndate_str = nstep_date.strftime("%d.%m") if pd.notna(nstep_date) else ""
            overdue_cls = ' style="color:#D32F2F;font-weight:600;"' if overdue and pd.notna(nstep_date) else ""
            nstep_html = f'<span{overdue_cls}>{nstep_str[:25]}'
            if ndate_str:
                nstep_html += f' <span style="color:#A0A7B3;font-size:11px;">{ndate_str}</span>'
            nstep_html += '</span>'
        else:
            nstep_html = '<span style="color:#A0A7B3;">—</span>'

        # Ответственные: BDM (partner_manager) + Sales (sales_manager)
        def _clean_name(v):
            s = str(v).strip() if pd.notna(v) else ""
            return s if s and s.lower() != "nan" else ""
        bdm_name = _clean_name(row.get("partner_manager"))
        sales_name = _clean_name(row.get("sales_manager"))
        owners_parts = []
        if bdm_name:
            owners_parts.append(
                f'<span style="font-size:11px;color:#A0A7B3;">BDM:</span> '
                f'<span style="color:#2D3748;">{bdm_name}</span>'
            )
        if sales_name:
            _sales_label = team if team in ("KAM", "CSM") else "Прод"
            owners_parts.append(
                f'<span style="font-size:11px;color:#A0A7B3;">{_sales_label}:</span> '
                f'<span style="color:#2D3748;">{sales_name}</span>'
            )
        if owners_parts:
            owners_html = '<br>'.join(owners_parts)
        else:
            owners_html = '<span style="color:#A0A7B3;">—</span>'

        # Client details (industry + segment)
        industry = row.get("industry", "")
        segment = row.get("segment", "")
        client_extra = ""
        ind_str = str(industry).strip() if pd.notna(industry) and str(industry).strip().lower() != "nan" else ""
        seg_str = str(segment).strip() if pd.notna(segment) and str(segment).strip().lower() != "nan" else ""
        if ind_str or seg_str:
            parts = [s for s in [seg_str, ind_str] if s]
            client_extra = f'<br><span style="font-size:11px;color:#A0A7B3;">{" · ".join(parts)}</span>'

        deal_rows += (
            f'<tr{row_style}>'
            f'<td><strong>{partner}</strong>{team_badge}{paid_icon}{risk_icon}</td>'
            f'<td>{client}{client_extra}</td>'
            f'<td>{owners_html}</td>'
            f'<td>{deal_badge(stage)}</td>'
            f'<td class="num">{planned_fmt}</td>'
            f'<td class="num">{prob_cell(prob)}</td>'
            f'<td class="num">{days_html}</td>'
            f'<td>{nstep_html}</td>'
            f'</tr>'
        )

    total_planned_fmt = f'{total_planned:,.0f} ₽'.replace(",", " ")
    total_weighted_fmt = f'{total_weighted:,.0f} ₽'.replace(",", " ")

    col_deal_tbl, col_deal_chart = st.columns([3, 2], gap="medium")

    _dtip_sum = info_tip("Плановая сумма КП.", "Сделки → «Сумма клиента (КП)»", "xlsx")
    _dtip_prob = info_tip("Оценка вероятности закрытия.", "Сделки → «Вероятность»", "xlsx")
    _dtip_stage = info_tip("Текущий этап сделки.", "Сделки → «Этап сделки»", "xlsx")
    _dtip_days = info_tip("Дней с момента поступления лида.", "Сегодня − Дата поступления", "расчётная", "tip-left")
    _dtip_nstep = info_tip("Следующий шаг и дата. Красный = просрочен.", "Сделки → «Следующий шаг» + «Дата»", "xlsx", "tip-left")
    _dtip_owners = info_tip("Ответственные за сделку: BDM со стороны партнёрки и менеджер продаж (KAM/CSM) со стороны продаж.", "Сделки → «Отв. партнёрки» + «Отв. продаж»", "xlsx")

    # Avg metrics
    _active = df_deals_filtered[~df_deals_filtered["deal_stage"].astype(str).str.lower().str.contains("проиграно|оплачено", na=False)]
    _avg_deal = _active["planned_amount"].mean() if len(_active) > 0 else 0
    _avg_days = _active["days_in_pipeline"].mean() if len(_active) > 0 and "days_in_pipeline" in _active.columns else 0

    with col_deal_tbl:
        st.markdown(f"""
        <table class="styled-table">
            <thead><tr>
                <th>Партнёр</th><th>Клиент</th><th>Ответственные {_dtip_owners}</th><th>Этап {_dtip_stage}</th>
                <th class="num">Сумма {_dtip_sum}</th><th class="num">Вер. {_dtip_prob}</th>
                <th class="num">Дни {_dtip_days}</th><th>След. шаг {_dtip_nstep}</th>
            </tr></thead>
            <tbody>
                {deal_rows}
                <tr class="row-total">
                    <td colspan="4">Итого &middot; Взвеш: {total_weighted_fmt} {info_tip("SUM(Сумма × Вероятность / 100)", "", "расчётная")}</td>
                    <td class="num">{total_planned_fmt}</td>
                    <td colspan="3"></td>
                </tr>
            </tbody>
        </table>
        """, unsafe_allow_html=True)

        # Avg metrics below table
        avg_deal_fmt = f'{_avg_deal/1_000:.0f} тыс ₽' if _avg_deal >= 1_000 else f'{_avg_deal:.0f} ₽'
        avg_days_fmt = f'{_avg_days:.0f} дн' if pd.notna(_avg_days) and _avg_days > 0 else "—"
        st.markdown(
            f'<div style="display:flex;gap:24px;margin-top:6px;font-size:13px;color:#6B7280;">'
            f'<span>Ср. чек (актив.): <b style="color:#2D3748;">{avg_deal_fmt}</b></span>'
            f'<span>Ср. возраст сделки: <b style="color:#2D3748;">{avg_days_fmt}</b></span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_deal_chart:
        if "deal_stage" in df_deals_filtered.columns and "planned_amount" in df_deals_filtered.columns and len(df_deals_filtered) > 0:
            # Exclude lost deals from chart (already highlighted in table)
            df_active_deals = df_deals_filtered[~df_deals_filtered["deal_stage"].astype(str).str.lower().str.contains("проиграно", na=False)]
            if not df_active_deals.empty:
                stage_sum = df_active_deals.groupby("deal_stage").agg(
                    total=("planned_amount", "sum"), weighted=("weighted_amount", "sum"),
                ).reset_index()
                stage_sum.columns = ["Этап", "Сумма КП", "Взвешенная"]
                stage_sum = stage_sum.sort_values("Сумма КП", ascending=True)  # ascending for horizontal

                def fmt_m(v):
                    if v >= 1_000_000:
                        return f'{v/1_000_000:.1f} млн'
                    if v >= 1_000:
                        return f'{v/1_000:.0f} тыс'
                    return f'{v:.0f}'

                fig_deals = go.Figure()
                # KP amount — main bar
                fig_deals.add_trace(go.Bar(
                    y=stage_sum["Этап"], x=stage_sum["Сумма КП"], name="Сумма КП",
                    orientation="h", marker_color="#4A90D9",
                    text=[fmt_m(v) for v in stage_sum["Сумма КП"]],
                    textposition="outside", textfont=dict(size=12, color="#2D3748"),
                ))
                # Weighted — overlay bar (transparent)
                fig_deals.add_trace(go.Bar(
                    y=stage_sum["Этап"], x=stage_sum["Взвешенная"], name="Взвешенная",
                    orientation="h", marker_color="rgba(102,187,106,0.5)",
                    text=[fmt_m(v) for v in stage_sum["Взвешенная"]],
                    textposition="inside", textfont=dict(size=11, color="#1B5E20"),
                ))
                n_stages = len(stage_sum)
                fig_deals.update_layout(
                    **PLOTLY_LAYOUT, height=max(180, n_stages * 50 + 40), barmode="overlay",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font_size=11),
                    yaxis=dict(showgrid=False, tickfont=dict(size=12)),
                    xaxis=dict(showgrid=True, gridcolor="#F0F1F3", zeroline=False, showticklabels=False),
                    bargap=0.25,
                )
                st.plotly_chart(fig_deals, use_container_width=True)

# ──────────────────────────────────────────────
# ACTIVITY DYNAMICS — full width, chart + mini-table side by side
# ──────────────────────────────────────────────
section_header("Динамика активности",
    "Количество касаний (звонки, письма, встречи) по дням на графике и по неделям в таблице под ним. "
    "Показывает интенсивность обработки пайплайна и ритм работы. "
    '<b>Формула:</b> график — COUNT(касаний) GROUP BY день, менеджер; таблица — по неделям. '
    '<b>Источник:</b> Общий пайп → кол. «Касание N (Дата)»'
)

if df_timeline.empty:
    st.markdown(
        '<div class="panel" style="text-align:center;color:#8C939D;padding:20px;">Нет данных по касаниям</div>',
        unsafe_allow_html=True,
    )
else:
    _tl_fds = pd.Timestamp(filter_date_start)
    _tl_fde = pd.Timestamp(filter_date_end) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    df_tl = df_timeline[
        df_timeline["manager"].isin(selected_managers)
        & (df_timeline["date"] >= _tl_fds)
        & (df_timeline["date"] <= _tl_fde)
    ]

    if df_tl.empty:
        st.markdown(
            '<div class="panel" style="text-align:center;color:#8C939D;padding:20px;">'
            'Нет касаний для выбранных менеджеров</div>',
            unsafe_allow_html=True,
        )
    else:
        # Daily data for the chart — normalize timestamps to midnight so
        # repeat touches on the same day collapse onto one x position.
        df_tl_daily = df_tl.copy()
        df_tl_daily["day"] = df_tl_daily["date"].dt.normalize()
        daily = df_tl_daily.groupby(["day", "manager"]).size().reset_index(name="touches")

        # Fill zero days across the full range so lines don't jump over gaps
        if not daily.empty:
            _day_min, _day_max = daily["day"].min(), daily["day"].max()
            _all_days = pd.date_range(_day_min, _day_max, freq="D")
            _full_idx = pd.MultiIndex.from_product(
                [_all_days, selected_managers], names=["day", "manager"]
            )
            daily = daily.set_index(["day", "manager"]).reindex(_full_idx, fill_value=0).reset_index()

        weekly = df_tl.groupby(["week", "manager"]).size().reset_index(name="touches")

        # Chart — daily granularity
        fig_activity = go.Figure()
        for mgr in selected_managers:
            mgr_daily = daily[daily["manager"] == mgr].sort_values("day")
            color = MANAGER_COLORS.get(mgr, "#90A4AE")
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            fig_activity.add_trace(go.Scatter(
                x=mgr_daily["day"], y=mgr_daily["touches"], name=mgr.split()[0],
                mode="lines+markers",
                line=dict(color=color, width=2), marker=dict(size=5, color=color),
                fill="tozeroy", fillcolor=f"rgba({r},{g},{b},0.07)",
                hovertemplate="<b>%{x|%d.%m.%Y}</b><br>Касаний: %{y}<extra>%{fullData.name}</extra>",
            ))

        fig_activity.update_layout(
            **PLOTLY_LAYOUT, height=300,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font_size=11),
            xaxis=dict(showgrid=False, tickformat="%d %b", title="", dtick=86400000.0 * 7),
            yaxis=dict(showgrid=True, gridcolor="#F0F1F3", zeroline=False, title="Касаний/день", title_font_size=11),
            hovermode="x unified",
        )
        st.plotly_chart(fig_activity, use_container_width=True)

        # Weekly breakdown table — full width, below chart
        all_weeks = sorted(weekly["week"].unique())
        week_labels = [w.strftime("%d.%m") for w in all_weeks]

        # Build header
        _tip_touches = info_tip("Число касаний за неделю (начало недели).", "COUNT(касаний) GROUP BY неделя", "Общий пайп", "tip-left")
        th_weeks = "".join(f'<th class="num">{wl}</th>' for wl in week_labels)
        header = f'<tr><th>Менеджер</th>{th_weeks}<th class="num">Итого {_tip_touches}</th></tr>'

        # Build rows
        tbl_rows = ""
        col_totals = {w: 0 for w in all_weeks}
        grand_total = 0
        for mgr in selected_managers:
            clr = MANAGER_COLORS.get(mgr, "#90A4AE")
            dot = f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{clr};margin-right:6px;vertical-align:middle;"></span>'
            mgr_data = weekly[weekly["manager"] == mgr]
            mgr_by_week = dict(zip(mgr_data["week"], mgr_data["touches"]))
            row_total = 0
            cells = ""
            for w in all_weeks:
                v = mgr_by_week.get(w, 0)
                row_total += v
                col_totals[w] += v
                cls = ' class="num zero"' if v == 0 else ' class="num"'
                cells += f"<td{cls}>{v}</td>"
            grand_total += row_total
            tbl_rows += f'<tr><td style="white-space:nowrap;">{dot}{mgr.split()[0]}</td>{cells}<td class="num"><strong>{row_total}</strong></td></tr>'

        # Totals row
        total_cells = "".join(f'<td class="num">{col_totals[w]}</td>' for w in all_weeks)
        tbl_rows += f'<tr class="row-total"><td>Итого</td>{total_cells}<td class="num">{grand_total}</td></tr>'

        st.markdown(f"""
        <table class="styled-table">
            <thead>{header}</thead>
            <tbody>{tbl_rows}</tbody>
        </table>
        """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# BDM PERSONAL KPI
# ──────────────────────────────────────────────
section_header("Персональные KPI BDM",
    "Помесячная динамика выполнения KPI каждым BDM-менеджером. "
    "<b>Активированные</b> = статус «Договор» или «Подписан» (дата = последнее касание). "
    "<b>Первая продажа</b> = уникальные партнёры с оплаченной сделкой (team=BDM). "
    "<b>Выручка</b> = сумма оплаченных сделок BDM. "
    ""
)

# Months by quarter
_bdm_quarters = [
    ("Q1", [(2026, 1), (2026, 2), (2026, 3)]),
    ("Q2", [(2026, 4), (2026, 5), (2026, 6)]),
]
_month_labels = {
    (2026, 1): "Янв", (2026, 2): "Фев", (2026, 3): "Мар",
    (2026, 4): "Апр", (2026, 5): "Май", (2026, 6): "Июн",
}

_bdm_cols = st.columns(3, gap="medium")
for idx, mgr in enumerate(BDM_MANAGERS):
    with _bdm_cols[idx]:
        _mgr_short = mgr.split()[0]
        _mgr_color = MANAGER_COLORS.get(mgr, "#6B7280")

        # Current totals (all time / current period)
        _kpi_total = compute_bdm_kpi(df_filtered, df_deals, mgr)

        # Build progress bars for current totals
        _bdm_bars = ""
        for kpi_key, kpi_cfg in BDM_KPI_TARGETS.items():
            fact = _kpi_total[kpi_key]
            target = kpi_cfg["target"]
            pct = min(fact / target * 100, 100) if target > 0 else 0
            bar_color = "#66BB6A" if pct >= 70 else ("#FFB74D" if pct >= 40 else "#E57373")
            is_money = kpi_cfg.get("fmt") == "money"
            if is_money:
                fact_str = _short_money(fact, "м")
                target_str = _short_money(target, "м")
            else:
                fact_str = str(int(fact))
                target_str = str(target)
            _bdm_bars += (
                f'<div style="margin-bottom:6px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2px;">'
                f'<span style="font-size:11px;font-weight:600;color:#2D3748;">{kpi_cfg["label"]}</span>'
                f'<span style="font-size:11px;color:#6B7280;">{fact_str}/{target_str} '
                f'<span style="font-weight:700;color:{bar_color};">{pct:.0f}%</span></span>'
                f'</div>'
                f'<div style="background:#E8ECF0;border-radius:3px;height:6px;overflow:hidden;">'
                f'<div style="width:{pct:.0f}%;height:100%;background:{bar_color};border-radius:3px;"></div>'
                f'</div></div>'
            )

        # Header card with progress bars
        st.markdown(
            f'<div style="background:#fff;border:1px solid #E2E6EC;border-radius:10px;padding:14px 16px;'
            f'border-top:3px solid {_mgr_color};">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
            f'<span style="font-size:14px;font-weight:700;color:#1A1A2E;">{_mgr_short}</span>'
            f'</div>'
            f'{_bdm_bars}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Monthly dynamics table with quarterly subtotals
        _tbl_header = '<th style="text-align:left;padding:4px 8px;font-size:11px;">Месяц</th>'
        for kpi_key, kpi_cfg in BDM_KPI_TARGETS.items():
            _short_label = kpi_cfg["label"].split()[0]
            _tbl_header += f'<th style="text-align:center;padding:4px 6px;font-size:11px;">{_short_label}</th>'

        _tbl_rows = ""
        _h1_totals = {"activated": 0, "first_sale": 0, "revenue": 0}

        for q_label, q_months in _bdm_quarters:
            _q_totals = {"activated": 0, "first_sale": 0, "revenue": 0}
            _is_future_q = q_months[0][1] > _now.month if q_months[0][0] == _now.year else q_months[0][0] > _now.year

            for ym in q_months:
                _is_future = (ym[0] > _now.year) or (ym[0] == _now.year and ym[1] > _now.month)
                kpi_m = compute_bdm_kpi(df_filtered, df_deals, mgr, year_month=ym)
                _row_opacity = 'opacity:0.4;' if _is_future else ''
                _row_cells = f'<td style="padding:4px 8px;font-size:11px;font-weight:600;{_row_opacity}">{_month_labels[ym]}</td>'
                for kpi_key, kpi_cfg in BDM_KPI_TARGETS.items():
                    fact = kpi_m[kpi_key]
                    target = kpi_cfg["target"]
                    is_money = kpi_cfg.get("fmt") == "money"
                    if is_money:
                        fact_str = _short_money(fact, "м")
                    else:
                        fact_str = str(int(fact))
                    if _is_future:
                        color = "#B0BEC5"
                    else:
                        color = "#66BB6A" if fact >= target else ("#E57373" if fact == 0 else "#FFB74D")
                    _row_cells += (
                        f'<td style="text-align:center;padding:4px 6px;font-size:11px;{_row_opacity}">'
                        f'<span style="color:{color};font-weight:600;">{fact_str}</span>'
                        f'<span style="color:#B0BEC5;font-size:10px;">/{target if not is_money else _short_money(target, "м")}</span>'
                        f'</td>'
                    )
                    _q_totals[kpi_key] += fact
                    _h1_totals[kpi_key] += fact
                _tbl_rows += f'<tr>{_row_cells}</tr>'

            # Quarter subtotal row
            _q_style = 'border-top:2px solid #E2E6EC;background:#F7F8FA;'
            if _is_future_q:
                _q_style += 'opacity:0.4;'
            _total_cells = f'<td style="padding:4px 8px;font-size:11px;font-weight:700;">{q_label}</td>'
            for kpi_key, kpi_cfg in BDM_KPI_TARGETS.items():
                val = _q_totals[kpi_key]
                target_q = kpi_cfg["target"] * 3
                is_money = kpi_cfg.get("fmt") == "money"
                if is_money:
                    val_str = _short_money(val, "м")
                    tgt_str = _short_money(target_q, "м")
                else:
                    val_str = str(int(val))
                    tgt_str = str(target_q)
                _total_cells += (
                    f'<td style="text-align:center;padding:4px 6px;font-size:11px;font-weight:700;">'
                    f'{val_str}<span style="color:#B0BEC5;font-size:10px;">/{tgt_str}</span></td>'
                )
            _tbl_rows += f'<tr style="{_q_style}">{_total_cells}</tr>'

        # H1 total row
        _h1_cells = '<td style="padding:4px 8px;font-size:11px;font-weight:800;">H1</td>'
        for kpi_key, kpi_cfg in BDM_KPI_TARGETS.items():
            val = _h1_totals[kpi_key]
            target_h = kpi_cfg["target"] * 6
            is_money = kpi_cfg.get("fmt") == "money"
            if is_money:
                val_str = _short_money(val, "м")
                tgt_str = _short_money(target_h, "м")
            else:
                val_str = str(int(val))
                tgt_str = str(target_h)
            _h1_cells += (
                f'<td style="text-align:center;padding:4px 6px;font-size:11px;font-weight:800;">'
                f'{val_str}<span style="color:#B0BEC5;font-size:10px;">/{tgt_str}</span></td>'
            )
        _tbl_rows += f'<tr style="border-top:3px solid #2D3748;background:#EDF0F4;">{_h1_cells}</tr>'

        st.markdown(
            f'<table class="styled-table" style="margin-top:8px;font-size:11px;width:100%;">'
            f'<thead><tr>{_tbl_header}</tr></thead>'
            f'<tbody>{_tbl_rows}</tbody>'
            f'</table>',
            unsafe_allow_html=True,
        )

# ──────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────
st.markdown(
    '<div class="footer-text">Пайп партнёров Кайтен 24.03.2026 &middot; Dashboard v2.2</div>',
    unsafe_allow_html=True,
)
