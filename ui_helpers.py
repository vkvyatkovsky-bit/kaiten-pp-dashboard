"""Reusable UI helpers shared across dashboard pages (overview + weekly)."""

import streamlit as st


def _short_money(val, suffix="м"):
    """Format money as short string: 1500000 -> '1.5м', 500000 -> '500т'."""
    if abs(val) >= 1_000_000:
        r = val / 1_000_000
        return f'{r:.1f}{suffix}'.replace('.0' + suffix, suffix)
    return f'{val / 1_000:.0f}т'


def fmt_money(val):
    """Format amount with HTML unit span: 1.5<span>млн ₽</span>."""
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
    """Render section title with blue left bar + optional tooltip."""
    tip = info_tip(tooltip) if tooltip else ""
    st.markdown(f'<div class="section-hdr">{text} {tip}</div>', unsafe_allow_html=True)
