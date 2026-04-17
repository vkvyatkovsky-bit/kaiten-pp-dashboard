"""Weekly summary page: итоги за 7 дней + динамика 30 дней + фокус на след. неделю."""

from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import html as _html

from config import MANAGER_COLORS, BDM_KPI_TARGETS
from ui_helpers import section_header, info_tip, fmt_money, _short_money


# Статусы, исключаемые из «зависших компаний» (финальные)
_FINAL_STATUSES = {"Договор", "Подписан", "Отказ", "Неликвид", "Не интересно", "Не обрабатываем"}

# Статусы, которые считаются «активированными» (перешли в финальную продажу)
_CLOSED_WON = {"Договор", "Подписан"}

_MONTH_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}


# ──────────────────────────────────────────────
# Date window helpers
# ──────────────────────────────────────────────
def _weekly_window(today, n_days=7):
    """Вернуть (curr_start, curr_end, prev_start, prev_end) как pd.Timestamp."""
    today_ts = pd.Timestamp(today)
    curr_end = today_ts + pd.Timedelta(hours=23, minutes=59, seconds=59)
    curr_start = today_ts - pd.Timedelta(days=n_days - 1)
    prev_end = curr_start - pd.Timedelta(seconds=1)
    prev_start = curr_start - pd.Timedelta(days=n_days)
    return curr_start, curr_end, prev_start, prev_end


def _mtd_window(today):
    """Вернуть (curr_start, curr_end, prev_start, prev_end) для MTD vs прошлый MTD."""
    today_ts = pd.Timestamp(today)
    curr_start = today_ts.replace(day=1)
    curr_end = today_ts + pd.Timedelta(hours=23, minutes=59, seconds=59)
    # Прошлый месяц — с 1-го по тот же день
    first_prev_month = (curr_start - pd.Timedelta(days=1)).replace(day=1)
    day_in_month = today_ts.day
    try:
        prev_end = first_prev_month.replace(day=day_in_month) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    except ValueError:
        # Например 31 марта → в феврале только 28/29
        next_m = (first_prev_month + pd.Timedelta(days=32)).replace(day=1)
        prev_end = next_m - pd.Timedelta(seconds=1)
    prev_start = first_prev_month
    return curr_start, curr_end, prev_start, prev_end


# ──────────────────────────────────────────────
# Data counters
# ──────────────────────────────────────────────
def _touch_date_cols(df_pipe):
    return [c for c in df_pipe.columns if isinstance(c, str) and c.startswith("touch_") and c.endswith("_date")]


def _touch_result_cols(df_pipe):
    return [c for c in df_pipe.columns if isinstance(c, str) and c.startswith("touch_") and c.endswith("_result")]


def _count_touches_in_window(df_pipe, start, end, managers):
    """Суммарное число касаний у указанных менеджеров в окне [start, end]."""
    mask_mgr = df_pipe["manager"].isin(managers)
    sub = df_pipe[mask_mgr]
    total = 0
    for c in _touch_date_cols(sub):
        col = sub[c]
        total += int(((col >= start) & (col <= end)).sum())
    return total


def _count_new_companies_in_window(df_pipe, start, end, managers):
    """Компании, у которых ПЕРВОЕ (min) касание попадает в окно."""
    mask_mgr = df_pipe["manager"].isin(managers)
    sub = df_pipe[mask_mgr]
    tcols = _touch_date_cols(sub)
    if not tcols:
        return 0
    first_touch = sub[tcols].min(axis=1)
    return int(((first_touch >= start) & (first_touch <= end)).sum())


def _count_deals_in_window(df_deals, date_col, start, end, managers=None):
    """Количество сделок, у которых date_col ∈ [start, end]."""
    if df_deals is None or df_deals.empty or date_col not in df_deals.columns:
        return 0
    col = df_deals[date_col]
    mask = (col >= start) & (col <= end)
    if managers is not None and "partner_manager" in df_deals.columns:
        mask = mask & df_deals["partner_manager"].isin(managers)
    return int(mask.sum())


def _sum_kp_in_window(df_deals, start, end, managers=None):
    """Сумма kp_amount по сделкам с kp_date ∈ [start, end]."""
    if df_deals is None or df_deals.empty or "kp_date" not in df_deals.columns:
        return 0.0
    # kp_date может быть не распарсен (в load_deals парсятся только date_received/next_step_date)
    kp_dates = pd.to_datetime(df_deals["kp_date"], errors="coerce", dayfirst=True)
    mask = (kp_dates >= start) & (kp_dates <= end)
    if managers is not None and "partner_manager" in df_deals.columns:
        mask = mask & df_deals["partner_manager"].isin(managers)
    if "kp_amount" not in df_deals.columns:
        return 0.0
    return float(df_deals.loc[mask, "kp_amount"].sum())


def _count_closings_in_window(df_pipe, start, end, managers):
    """Компании, перешедшие в «Договор/Подписан» в окне (по дате последнего касания)."""
    mask_mgr = df_pipe["manager"].isin(managers)
    sub = df_pipe[mask_mgr]
    sub = sub[sub["status"].isin(_CLOSED_WON)]
    if sub.empty:
        return 0
    tcols = _touch_date_cols(sub)
    if not tcols:
        return 0
    last_touch = sub[tcols].max(axis=1)
    return int(((last_touch >= start) & (last_touch <= end)).sum())


# ──────────────────────────────────────────────
# Focus data (для блока «Фокус на следующую неделю»)
# ──────────────────────────────────────────────
def _overdue_next_steps(df_deals, today, managers):
    """Сделки с просроченным next_step_date."""
    if df_deals is None or df_deals.empty:
        return pd.DataFrame()
    if "next_step_date" not in df_deals.columns:
        return pd.DataFrame()
    today_ts = pd.Timestamp(today)
    mask = df_deals["next_step_date"].notna() & (df_deals["next_step_date"] < today_ts)
    if "partner_manager" in df_deals.columns:
        mask = mask & df_deals["partner_manager"].isin(managers)
    # Исключаем финальные стадии
    if "deal_stage" in df_deals.columns:
        stage = df_deals["deal_stage"].astype(str).str.lower()
        mask = mask & ~stage.str.contains("оплачено|отказ|закрыт", na=False, regex=True)
    sub = df_deals[mask].copy()
    if sub.empty:
        return sub
    sub["overdue_days"] = (today_ts - sub["next_step_date"]).dt.days
    sub = sub.sort_values("overdue_days", ascending=False)
    return sub


def _stalled_companies(df_pipe, today, managers, threshold_days=7):
    """Компании с последним касанием >threshold_days назад и не в финальном статусе."""
    mask_mgr = df_pipe["manager"].isin(managers)
    sub = df_pipe[mask_mgr].copy()
    tcols = _touch_date_cols(sub)
    if not tcols:
        return pd.DataFrame()
    sub["_last_touch"] = sub[tcols].max(axis=1)
    today_ts = pd.Timestamp(today)
    # Нужен факт касания (не «без касаний») — last_touch NOT NaT
    sub = sub[sub["_last_touch"].notna()]
    sub["days_since"] = (today_ts - sub["_last_touch"]).dt.days
    sub = sub[sub["days_since"] > threshold_days]
    sub = sub[~sub["status"].isin(_FINAL_STATUSES)]
    sub = sub.sort_values("days_since", ascending=False)
    return sub[["company", "manager", "_last_touch", "days_since", "status"]]


def _empty_result_touches(df_pipe, managers):
    """Строки вида (компания, менеджер, № касания, дата): касание сделано (есть date), результат пустой."""
    mask_mgr = df_pipe["manager"].isin(managers)
    sub = df_pipe[mask_mgr]
    records = []
    tdates = sorted(_touch_date_cols(sub), key=lambda c: int(c.split("_")[1]))
    for date_col in tdates:
        n = int(date_col.split("_")[1])
        result_col = f"touch_{n}_result"
        if result_col not in sub.columns:
            continue
        mask = sub[date_col].notna() & (sub[result_col].isna() | (sub[result_col].astype(str).str.strip() == ""))
        for _, row in sub.loc[mask, ["company", "manager", date_col, "status"]].iterrows():
            records.append({
                "company": row["company"],
                "manager": row["manager"],
                "touch_num": n,
                "touch_date": row[date_col],
                "status": row["status"],
            })
    if not records:
        return pd.DataFrame()
    out = pd.DataFrame(records).sort_values("touch_date", ascending=False)
    return out


# ──────────────────────────────────────────────
# Render helpers
# ──────────────────────────────────────────────
def _delta_chip_html(curr, prev, is_money=False):
    """Зелёный/красный/серый чип с ΔN + Δ% для сравнения с прошлым периодом."""
    if prev == 0 and curr == 0:
        return '<span style="color:#B0BEC5;font-size:12px;font-weight:600;">— без изм.</span>'
    if prev == 0:
        # Всплеск с 0
        sign = "+"
        color = "#66BB6A"
        bg = "#E8F5E9"
        arrow = "▲"
        val_str = f"+{_short_money(curr, 'м') if is_money else curr}"
        return (
            f'<span style="color:{color};background:{bg};font-size:12px;font-weight:700;'
            f'padding:2px 8px;border-radius:10px;">{arrow} {val_str} vs 0</span>'
        )
    delta = curr - prev
    pct = delta / prev * 100
    if abs(pct) < 1 and delta == 0:
        return '<span style="color:#B0BEC5;font-size:12px;font-weight:600;">— без изм.</span>'
    if delta > 0:
        color = "#2E7D32"
        bg = "#E8F5E9"
        arrow = "▲"
        sign = "+"
    else:
        color = "#C62828"
        bg = "#FFEBEE"
        arrow = "▼"
        sign = ""
    if is_money:
        val_str = f"{sign}{_short_money(delta, 'м')}"
    else:
        val_str = f"{sign}{int(delta)}"
    return (
        f'<span style="color:{color};background:{bg};font-size:12px;font-weight:700;'
        f'padding:2px 8px;border-radius:10px;white-space:nowrap;">{arrow} {val_str} ({sign}{pct:.0f}%)</span>'
    )


def _kpi_card_with_delta(label, value_html, delta_html, tooltip_html, card_cls=""):
    """HTML-карточка с большой цифрой недели + дельта под ней."""
    return (
        f'<div class="kpi-card {card_cls}">'
        f'<div class="kpi-label">{label} {tooltip_html}</div>'
        f'<div class="kpi-value">{value_html}</div>'
        f'<div style="margin-top:6px;">{delta_html}</div>'
        f'</div>'
    )


# ──────────────────────────────────────────────
# Top-level section renderers
# ──────────────────────────────────────────────
def _render_period_banner(today):
    curr_s, curr_e, prev_s, prev_e = _weekly_window(today)
    dyn_s = pd.Timestamp(today) - pd.Timedelta(days=29)
    dyn_e = pd.Timestamp(today)
    fmt = "%d.%m"
    st.markdown(
        f'<div style="margin:6px 0 14px 0;padding:10px 14px;border-radius:8px;background:#EBF0FA;'
        f'border:1px solid #D0DBEF;">'
        f'<div style="display:flex;gap:18px;flex-wrap:wrap;font-size:13.5px;color:#1A1A2E;">'
        f'<span><b style="color:#4A90D9;">Итоги недели:</b> '
        f'<b>{curr_s.strftime(fmt)} — {curr_e.strftime(fmt)}</b></span>'
        f'<span style="color:#6B7280;">•</span>'
        f'<span><b style="color:#8C939D;">Предыдущая:</b> '
        f'{prev_s.strftime(fmt)} — {prev_e.strftime(fmt)}</span>'
        f'<span style="color:#6B7280;">•</span>'
        f'<span><b style="color:#8C939D;">Динамика:</b> '
        f'{dyn_s.strftime(fmt)} — {dyn_e.strftime(fmt)} <i style="color:#8C939D;">(30 дней)</i></span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _render_weekly_kpi_cards(df_pipe, df_deals, today, managers):
    curr_s, curr_e, prev_s, prev_e = _weekly_window(today)

    # Метрики
    touches_c = _count_touches_in_window(df_pipe, curr_s, curr_e, managers)
    touches_p = _count_touches_in_window(df_pipe, prev_s, prev_e, managers)

    new_c = _count_new_companies_in_window(df_pipe, curr_s, curr_e, managers)
    new_p = _count_new_companies_in_window(df_pipe, prev_s, prev_e, managers)

    deals_c = _count_deals_in_window(df_deals, "date_received", curr_s, curr_e, managers)
    deals_p = _count_deals_in_window(df_deals, "date_received", prev_s, prev_e, managers)

    kp_c = _sum_kp_in_window(df_deals, curr_s, curr_e, managers)
    kp_p = _sum_kp_in_window(df_deals, prev_s, prev_e, managers)

    close_c = _count_closings_in_window(df_pipe, curr_s, curr_e, managers)
    close_p = _count_closings_in_window(df_pipe, prev_s, prev_e, managers)

    cards = [
        {
            "label": "Касаний за неделю",
            "value": f'<span class="kpi-value">{touches_c}</span>',
            "delta": _delta_chip_html(touches_c, touches_p),
            "tip": info_tip(
                "Звонки, письма, встречи за последние 7 дней.",
                "COUNT(touch_N_date ∈ [today-7, today])",
                "Общий пайп",
            ),
            "cls": "",
        },
        {
            "label": "Новых компаний",
            "value": f'<span class="kpi-value">{new_c}</span>',
            "delta": _delta_chip_html(new_c, new_p),
            "tip": info_tip(
                "Компании, у которых ПЕРВОЕ касание пришлось на эту неделю.",
                "COUNT(company, где min(touch_N_date) ∈ неделя)",
                "Общий пайп",
            ),
            "cls": "",
        },
        {
            "label": "Новых сделок",
            "value": f'<span class="kpi-value">{deals_c}</span>',
            "delta": _delta_chip_html(deals_c, deals_p),
            "tip": info_tip(
                "Сделки CSM/BDM, полученные за неделю.",
                "COUNT(deal, где date_received ∈ неделя)",
                "Сделки CSM/BDM",
            ),
            "cls": "",
        },
        {
            "label": "Выставлено КП",
            "value": f'<span class="kpi-value">{fmt_money(kp_c)}</span>' if kp_c else '<span class="kpi-value">0<span class="unit"> ₽</span></span>',
            "delta": _delta_chip_html(kp_c, kp_p, is_money=True),
            "tip": info_tip(
                "Сумма КП, выставленных за неделю (по kp_date).",
                "SUM(kp_amount, где kp_date ∈ неделя)",
                "Сделки CSM/BDM",
            ),
            "cls": "money",
        },
        {
            "label": "Переходы в Договор",
            "value": f'<span class="kpi-value">{close_c}</span>',
            "delta": _delta_chip_html(close_c, close_p),
            "tip": info_tip(
                "Компании, перешедшие в «Договор/Подписан» за неделю (дата = последнее касание).",
                "COUNT(company, status ∈ {Договор,Подписан} И last_touch ∈ неделя)",
                "Общий пайп",
            ),
            "cls": "",
        },
    ]

    cols = st.columns(5, gap="small")
    for col, card in zip(cols, cards):
        with col:
            st.markdown(
                _kpi_card_with_delta(card["label"], card["value"], card["delta"], card["tip"], card["cls"]),
                unsafe_allow_html=True,
            )


def _render_activity_30d_chart(df_timeline, today, managers):
    """Area по дням (30 дней) + пунктирная линия 7-дн скользящего среднего + заливка текущей недели."""
    today_ts = pd.Timestamp(today)
    dyn_start = today_ts - pd.Timedelta(days=29)
    dyn_end = today_ts + pd.Timedelta(hours=23, minutes=59, seconds=59)

    if df_timeline is None or df_timeline.empty:
        st.markdown(
            '<div class="panel" style="text-align:center;color:#8C939D;padding:20px;">Нет касаний за 30 дней</div>',
            unsafe_allow_html=True,
        )
        return

    df_tl = df_timeline[
        df_timeline["manager"].isin(managers)
        & (df_timeline["date"] >= dyn_start)
        & (df_timeline["date"] <= dyn_end)
    ].copy()

    if df_tl.empty:
        st.markdown(
            '<div class="panel" style="text-align:center;color:#8C939D;padding:20px;">Нет касаний за 30 дней</div>',
            unsafe_allow_html=True,
        )
        return

    df_tl["day"] = df_tl["date"].dt.normalize()
    daily = df_tl.groupby(["day", "manager"]).size().reset_index(name="touches")

    # Заполнение нулями
    all_days = pd.date_range(dyn_start.normalize(), today_ts.normalize(), freq="D")
    idx = pd.MultiIndex.from_product([all_days, managers], names=["day", "manager"])
    daily = daily.set_index(["day", "manager"]).reindex(idx, fill_value=0).reset_index()

    fig = go.Figure()

    # Полупрозрачная подсветка текущей недели
    curr_s, curr_e, _, _ = _weekly_window(today)
    fig.add_vrect(
        x0=curr_s, x1=curr_e,
        fillcolor="#4A90D9", opacity=0.06, line_width=0, layer="below",
    )

    # Области по менеджерам
    for mgr in managers:
        mgr_daily = daily[daily["manager"] == mgr].sort_values("day")
        color = MANAGER_COLORS.get(mgr, "#90A4AE")
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        fig.add_trace(go.Scatter(
            x=mgr_daily["day"], y=mgr_daily["touches"], name=mgr.split()[0],
            mode="lines", line=dict(color=color, width=1.8),
            fill="tozeroy", fillcolor=f"rgba({r},{g},{b},0.10)",
            hovertemplate="<b>%{x|%d.%m}</b><br>Касаний: %{y}<extra>%{fullData.name}</extra>",
        ))

    # Сумма + скользящая 7-дн
    total = daily.groupby("day")["touches"].sum().reset_index().sort_values("day")
    total["ma7"] = total["touches"].rolling(window=7, min_periods=1).mean()
    fig.add_trace(go.Scatter(
        x=total["day"], y=total["ma7"], name="Среднее 7дн",
        mode="lines", line=dict(color="#1A1A2E", width=2, dash="dot"),
        hovertemplate="<b>%{x|%d.%m}</b><br>Среднее 7дн: %{y:.1f}<extra></extra>",
    ))

    fig.update_layout(
        template="simple_white",
        margin=dict(l=10, r=10, t=30, b=10),
        height=280,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font_size=11),
        xaxis=dict(showgrid=False, tickformat="%d %b", title="", dtick=86400000.0 * 7),
        yaxis=dict(showgrid=True, gridcolor="#F0F1F3", zeroline=False, title="Касаний/день", title_font_size=11),
        hovermode="x unified",
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_manager_week_table(df_pipe, df_deals, today, managers):
    """HTML-таблица: менеджер × (касания, новые комп., сделки, КП, Δ касаний к прошлой нед.)."""
    curr_s, curr_e, prev_s, prev_e = _weekly_window(today)

    rows_data = []
    grand = {"touches": 0, "new": 0, "deals": 0, "kp": 0.0, "prev_touches": 0}

    for mgr in managers:
        t_c = _count_touches_in_window(df_pipe, curr_s, curr_e, [mgr])
        t_p = _count_touches_in_window(df_pipe, prev_s, prev_e, [mgr])
        n_c = _count_new_companies_in_window(df_pipe, curr_s, curr_e, [mgr])
        d_c = _count_deals_in_window(df_deals, "date_received", curr_s, curr_e, [mgr])
        kp_c = _sum_kp_in_window(df_deals, curr_s, curr_e, [mgr])
        rows_data.append({"mgr": mgr, "t": t_c, "tp": t_p, "n": n_c, "d": d_c, "kp": kp_c})
        grand["touches"] += t_c
        grand["prev_touches"] += t_p
        grand["new"] += n_c
        grand["deals"] += d_c
        grand["kp"] += kp_c

    # Header
    _tip_touches = info_tip("Касания за текущую неделю.", "COUNT(touch_date ∈ неделя)", "Общий пайп", "tip-left")
    _tip_new = info_tip("Компании с первым касанием на этой неделе.", "min(touch_date) ∈ неделя", "Общий пайп", "tip-left")
    _tip_deals = info_tip("Новые сделки CSM/BDM за неделю.", "date_received ∈ неделя", "Сделки", "tip-left")
    _tip_kp = info_tip("КП, выставленные на этой неделе.", "SUM(kp_amount, kp_date ∈ неделя)", "Сделки", "tip-left")
    _tip_delta = info_tip("Рост/падение касаний относительно предыдущей недели.", "ΔN = N(текущая) − N(прошлая)", "Общий пайп", "tip-left")

    header = (
        '<tr>'
        '<th>Менеджер</th>'
        f'<th class="num">Касания {_tip_touches}</th>'
        f'<th class="num">Новые комп. {_tip_new}</th>'
        f'<th class="num">Сделки {_tip_deals}</th>'
        f'<th class="num">КП, ₽ {_tip_kp}</th>'
        f'<th class="num">Δ касаний {_tip_delta}</th>'
        '</tr>'
    )

    rows_html = ""
    for r in rows_data:
        clr = MANAGER_COLORS.get(r["mgr"], "#90A4AE")
        dot = f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{clr};margin-right:6px;vertical-align:middle;"></span>'
        kp_str = fmt_money(r["kp"]) if r["kp"] else "—"
        rows_html += (
            f'<tr>'
            f'<td style="white-space:nowrap;">{dot}{_html.escape(r["mgr"])}</td>'
            f'<td class="num">{r["t"]}</td>'
            f'<td class="num">{r["n"]}</td>'
            f'<td class="num">{r["d"]}</td>'
            f'<td class="num">{kp_str}</td>'
            f'<td class="num">{_delta_chip_html(r["t"], r["tp"])}</td>'
            f'</tr>'
        )

    # Итого
    kp_total_str = fmt_money(grand["kp"]) if grand["kp"] else "—"
    rows_html += (
        f'<tr class="row-total">'
        f'<td>Итого</td>'
        f'<td class="num">{grand["touches"]}</td>'
        f'<td class="num">{grand["new"]}</td>'
        f'<td class="num">{grand["deals"]}</td>'
        f'<td class="num">{kp_total_str}</td>'
        f'<td class="num">{_delta_chip_html(grand["touches"], grand["prev_touches"])}</td>'
        f'</tr>'
    )

    st.markdown(
        f'<table class="styled-table"><thead>{header}</thead><tbody>{rows_html}</tbody></table>',
        unsafe_allow_html=True,
    )


def _render_mtd_comparison(df_pipe, df_deals, today, managers):
    """Сравнение MTD vs прошлый MTD (тот же день месяца)."""
    curr_s, curr_e, prev_s, prev_e = _mtd_window(today)
    today_ts = pd.Timestamp(today)

    # Метрики
    def _pack(start, end):
        return {
            "touches": _count_touches_in_window(df_pipe, start, end, managers),
            "new": _count_new_companies_in_window(df_pipe, start, end, managers),
            "deals": _count_deals_in_window(df_deals, "date_received", start, end, managers),
            "kp": _sum_kp_in_window(df_deals, start, end, managers),
            "closings": _count_closings_in_window(df_pipe, start, end, managers),
        }

    c = _pack(curr_s, curr_e)
    p = _pack(prev_s, prev_e)

    curr_m = _MONTH_RU[today_ts.month]
    prev_m = _MONTH_RU[curr_s.month - 1 if curr_s.month > 1 else 12]
    day = today_ts.day

    rows = [
        ("Касаний", c["touches"], p["touches"], False),
        ("Новых компаний", c["new"], p["new"], False),
        ("Новых сделок", c["deals"], p["deals"], False),
        ("КП, ₽", c["kp"], p["kp"], True),
        ("Переходы в Договор", c["closings"], p["closings"], False),
    ]

    header = (
        '<tr>'
        '<th>Метрика</th>'
        f'<th class="num">{curr_m} 1–{day}</th>'
        f'<th class="num">{prev_m} 1–{day}</th>'
        '<th class="num">Δ</th>'
        '</tr>'
    )
    body = ""
    for label, cv, pv, is_money in rows:
        cv_str = fmt_money(cv) if is_money else (f'{int(cv)}' if cv else "0")
        pv_str = fmt_money(pv) if is_money else (f'{int(pv)}' if pv else "0")
        if is_money and cv == 0:
            cv_str = "—"
        if is_money and pv == 0:
            pv_str = "—"
        body += (
            f'<tr>'
            f'<td>{label}</td>'
            f'<td class="num">{cv_str}</td>'
            f'<td class="num" style="color:#8C939D;">{pv_str}</td>'
            f'<td class="num">{_delta_chip_html(cv, pv, is_money=is_money)}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<table class="styled-table"><thead>{header}</thead><tbody>{body}</tbody></table>',
        unsafe_allow_html=True,
    )


def _render_successes(df_pipe, df_deals, today, managers):
    """Три карточки-хайлайта: лидер недели, крупнейшее КП, новые закрытия."""
    curr_s, curr_e, prev_s, prev_e = _weekly_window(today)

    # Лидер недели по касаниям
    leader_mgr, leader_touches, leader_delta = None, 0, 0
    for mgr in managers:
        t = _count_touches_in_window(df_pipe, curr_s, curr_e, [mgr])
        if t > leader_touches:
            leader_mgr, leader_touches = mgr, t
            tp = _count_touches_in_window(df_pipe, prev_s, prev_e, [mgr])
            leader_delta = t - tp

    # Крупнейшее КП
    biggest_client, biggest_sum, biggest_mgr = None, 0.0, None
    if df_deals is not None and not df_deals.empty and "kp_date" in df_deals.columns:
        kp_dates = pd.to_datetime(df_deals["kp_date"], errors="coerce", dayfirst=True)
        mask = (kp_dates >= curr_s) & (kp_dates <= curr_e)
        if "partner_manager" in df_deals.columns:
            mask = mask & df_deals["partner_manager"].isin(managers)
        sub = df_deals[mask]
        if not sub.empty and "kp_amount" in sub.columns and sub["kp_amount"].max() > 0:
            top = sub.loc[sub["kp_amount"].idxmax()]
            biggest_client = str(top.get("client", "—"))
            biggest_sum = float(top.get("kp_amount", 0))
            biggest_mgr = str(top.get("partner_manager", "—"))

    # Новые закрытия — перешедшие в «Договор/Подписан»
    closings_total = _count_closings_in_window(df_pipe, curr_s, curr_e, managers)
    # детализация по компаниям
    closings_list = []
    sub_closed = df_pipe[df_pipe["manager"].isin(managers) & df_pipe["status"].isin(_CLOSED_WON)]
    if not sub_closed.empty:
        tcols = _touch_date_cols(sub_closed)
        last = sub_closed[tcols].max(axis=1)
        hits = sub_closed[(last >= curr_s) & (last <= curr_e)]
        closings_list = hits[["company", "manager"]].head(3).to_dict("records")

    # Render 3 карточки
    c1, c2, c3 = st.columns(3, gap="medium")

    with c1:
        if leader_mgr and leader_touches > 0:
            clr = MANAGER_COLORS.get(leader_mgr, "#4A90D9")
            delta_str = f"+{leader_delta}" if leader_delta > 0 else str(leader_delta)
            delta_color = "#2E7D32" if leader_delta > 0 else ("#C62828" if leader_delta < 0 else "#8C939D")
            st.markdown(
                f'<div class="kpi-card" style="border-top-color:{clr};text-align:left;">'
                f'<div style="font-size:24px;margin-bottom:4px;">🏆</div>'
                f'<div style="font-size:12px;color:#8C939D;text-transform:uppercase;letter-spacing:0.5px;'
                f'font-weight:700;">Лидер недели</div>'
                f'<div style="font-size:17px;font-weight:800;color:#1A1A2E;margin-top:4px;">{_html.escape(leader_mgr)}</div>'
                f'<div style="font-size:13px;color:#6B7280;margin-top:4px;">{leader_touches} касаний '
                f'<span style="color:{delta_color};font-weight:700;">({delta_str} к прошлой неделе)</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="kpi-card" style="text-align:left;">'
                '<div style="font-size:24px;margin-bottom:4px;">🏆</div>'
                '<div style="font-size:12px;color:#8C939D;text-transform:uppercase;letter-spacing:0.5px;'
                'font-weight:700;">Лидер недели</div>'
                '<div style="font-size:14px;color:#8C939D;margin-top:8px;">Недостаточно активности</div>'
                '</div>',
                unsafe_allow_html=True,
            )

    with c2:
        if biggest_client and biggest_sum > 0:
            st.markdown(
                f'<div class="kpi-card money" style="text-align:left;">'
                f'<div style="font-size:24px;margin-bottom:4px;">💰</div>'
                f'<div style="font-size:12px;color:#8C939D;text-transform:uppercase;letter-spacing:0.5px;'
                f'font-weight:700;">Крупнейшее КП недели</div>'
                f'<div style="font-size:17px;font-weight:800;color:#1A1A2E;margin-top:4px;">'
                f'{fmt_money(biggest_sum)}</div>'
                f'<div style="font-size:13px;color:#6B7280;margin-top:4px;">'
                f'{_html.escape(biggest_client)} • <span style="color:#8C939D;">{_html.escape(biggest_mgr)}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="kpi-card money" style="text-align:left;">'
                '<div style="font-size:24px;margin-bottom:4px;">💰</div>'
                '<div style="font-size:12px;color:#8C939D;text-transform:uppercase;letter-spacing:0.5px;'
                'font-weight:700;">Крупнейшее КП недели</div>'
                '<div style="font-size:14px;color:#8C939D;margin-top:8px;">КП не выставлялись</div>'
                '</div>',
                unsafe_allow_html=True,
            )

    with c3:
        if closings_total > 0:
            names_html = "".join(
                f'<div style="font-size:13px;color:#2D3748;margin-top:2px;">'
                f'• {_html.escape(str(r["company"]))} '
                f'<span style="color:#8C939D;font-size:11.5px;">({_html.escape(str(r["manager"]).split()[0])})</span></div>'
                for r in closings_list
            )
            more = ""
            if closings_total > len(closings_list):
                more = f'<div style="font-size:12px;color:#8C939D;margin-top:4px;">…и ещё {closings_total - len(closings_list)}</div>'
            st.markdown(
                f'<div class="kpi-card" style="border-top-color:#66BB6A;text-align:left;">'
                f'<div style="font-size:24px;margin-bottom:4px;">✅</div>'
                f'<div style="font-size:12px;color:#8C939D;text-transform:uppercase;letter-spacing:0.5px;'
                f'font-weight:700;">Закрытия недели</div>'
                f'<div style="font-size:17px;font-weight:800;color:#1A1A2E;margin-top:4px;">'
                f'{closings_total} перехода в Договор</div>'
                f'<div style="margin-top:6px;">{names_html}{more}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="kpi-card" style="border-top-color:#66BB6A;text-align:left;">'
                '<div style="font-size:24px;margin-bottom:4px;">✅</div>'
                '<div style="font-size:12px;color:#8C939D;text-transform:uppercase;letter-spacing:0.5px;'
                'font-weight:700;">Закрытия недели</div>'
                '<div style="font-size:14px;color:#8C939D;margin-top:8px;">Пока нет переходов в Договор</div>'
                '</div>',
                unsafe_allow_html=True,
            )


def _render_focus_overdue(df_deals, today, managers):
    overdue = _overdue_next_steps(df_deals, today, managers)
    if overdue.empty:
        st.markdown(
            '<div class="panel" style="text-align:center;color:#66BB6A;padding:12px;font-weight:600;">'
            '✓ Просроченных next_step нет</div>',
            unsafe_allow_html=True,
        )
        return

    # Группировка по менеджерам для заголовка
    grp = overdue["partner_manager"].fillna("—").value_counts().to_dict() if "partner_manager" in overdue.columns else {}
    counts_str = ", ".join(f'{m.split()[0]}: {n}' for m, n in grp.items())
    total = len(overdue)
    st.markdown(
        f'<div style="font-size:13.5px;color:#6B7280;margin-bottom:6px;">Всего: <b style="color:#C62828;">{total}</b> '
        f'({_html.escape(counts_str)})</div>',
        unsafe_allow_html=True,
    )

    header = (
        '<tr>'
        '<th>Клиент</th>'
        '<th>Менеджер</th>'
        '<th class="num">next_step</th>'
        '<th class="num">Просрочка, дн</th>'
        '<th class="num">Сумма КП</th>'
        '<th>Стадия</th>'
        '</tr>'
    )
    rows = ""
    for _, r in overdue.iterrows():
        client = _html.escape(str(r.get("client", "—") or "—"))
        mgr = str(r.get("partner_manager", "—") or "—")
        clr = MANAGER_COLORS.get(mgr, "#90A4AE")
        dot = f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{clr};margin-right:5px;"></span>'
        ns_date = r["next_step_date"].strftime("%d.%m") if pd.notna(r["next_step_date"]) else "—"
        days = int(r["overdue_days"])
        days_cls = "ok"
        days_color = "#C62828" if days > 7 else ("#F57C00" if days > 2 else "#E67E22")
        kp = r.get("kp_amount", 0)
        kp_str = fmt_money(kp) if kp else "—"
        stage = _html.escape(str(r.get("deal_stage", "—") or "—"))
        rows += (
            f'<tr>'
            f'<td>{client}</td>'
            f'<td>{dot}<span style="font-size:13px;">{_html.escape(mgr.split()[0])}</span></td>'
            f'<td class="num">{ns_date}</td>'
            f'<td class="num" style="color:{days_color};font-weight:700;">{days}</td>'
            f'<td class="num">{kp_str}</td>'
            f'<td style="font-size:12px;color:#6B7280;">{stage}</td>'
            f'</tr>'
        )
    st.markdown(
        f'<table class="styled-table" style="font-size:13.5px;"><thead>{header}</thead><tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )


def _render_focus_stalled(df_pipe, today, managers):
    stalled = _stalled_companies(df_pipe, today, managers, threshold_days=7)
    if stalled.empty:
        st.markdown(
            '<div class="panel" style="text-align:center;color:#66BB6A;padding:12px;font-weight:600;">'
            '✓ Все активные компании в ритме</div>',
            unsafe_allow_html=True,
        )
        return

    grp = stalled["manager"].value_counts().to_dict()
    counts_str = ", ".join(f'{m.split()[0]}: {n}' for m, n in grp.items())
    total = len(stalled)
    st.markdown(
        f'<div style="font-size:13.5px;color:#6B7280;margin-bottom:6px;">Всего: <b style="color:#F57C00;">{total}</b> '
        f'({_html.escape(counts_str)}) · Ниже — топ-10 у каждого</div>',
        unsafe_allow_html=True,
    )

    header = (
        '<tr>'
        '<th>Компания</th>'
        '<th>Менеджер</th>'
        '<th class="num">Последнее касание</th>'
        '<th class="num">Дней без касания</th>'
        '<th>Статус</th>'
        '</tr>'
    )
    rows = ""
    # Топ-10 у каждого менеджера
    picks = []
    for mgr in managers:
        sub = stalled[stalled["manager"] == mgr].head(10)
        picks.append(sub)
    if picks:
        combined = pd.concat(picks, ignore_index=True)
    else:
        combined = stalled.head(0)

    for _, r in combined.iterrows():
        mgr = str(r["manager"])
        clr = MANAGER_COLORS.get(mgr, "#90A4AE")
        dot = f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{clr};margin-right:5px;"></span>'
        lt = r["_last_touch"].strftime("%d.%m") if pd.notna(r["_last_touch"]) else "—"
        days = int(r["days_since"])
        days_color = "#C62828" if days > 21 else ("#F57C00" if days > 14 else "#E67E22")
        rows += (
            f'<tr>'
            f'<td>{_html.escape(str(r["company"]))}</td>'
            f'<td>{dot}<span style="font-size:13px;">{_html.escape(mgr.split()[0])}</span></td>'
            f'<td class="num">{lt}</td>'
            f'<td class="num" style="color:{days_color};font-weight:700;">{days}</td>'
            f'<td style="font-size:12px;color:#6B7280;">{_html.escape(str(r["status"]))}</td>'
            f'</tr>'
        )
    st.markdown(
        f'<table class="styled-table" style="font-size:13.5px;"><thead>{header}</thead><tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )


def _render_focus_empty_results(df_pipe, managers):
    empty = _empty_result_touches(df_pipe, managers)
    if empty.empty:
        st.markdown(
            '<div class="panel" style="text-align:center;color:#66BB6A;padding:12px;font-weight:600;">'
            '✓ Все касания имеют результат</div>',
            unsafe_allow_html=True,
        )
        return

    grp = empty["manager"].value_counts().to_dict()
    counts_str = ", ".join(f'{m.split()[0]}: {n}' for m, n in grp.items())
    total = len(empty)
    shown = min(30, total)
    st.markdown(
        f'<div style="font-size:13.5px;color:#6B7280;margin-bottom:6px;">Всего: <b style="color:#E67E22;">{total}</b> '
        f'({_html.escape(counts_str)}) · Показано последних {shown}</div>',
        unsafe_allow_html=True,
    )

    header = (
        '<tr>'
        '<th>Компания</th>'
        '<th>Менеджер</th>'
        '<th class="num">Дата касания</th>'
        '<th class="num">№ касания</th>'
        '<th>Статус</th>'
        '</tr>'
    )
    rows = ""
    for _, r in empty.head(30).iterrows():
        mgr = str(r["manager"])
        clr = MANAGER_COLORS.get(mgr, "#90A4AE")
        dot = f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{clr};margin-right:5px;"></span>'
        td = r["touch_date"].strftime("%d.%m") if pd.notna(r["touch_date"]) else "—"
        rows += (
            f'<tr>'
            f'<td>{_html.escape(str(r["company"]))}</td>'
            f'<td>{dot}<span style="font-size:13px;">{_html.escape(mgr.split()[0])}</span></td>'
            f'<td class="num">{td}</td>'
            f'<td class="num">{r["touch_num"]}</td>'
            f'<td style="font-size:12px;color:#6B7280;">{_html.escape(str(r["status"]))}</td>'
            f'</tr>'
        )
    st.markdown(
        f'<table class="styled-table" style="font-size:13.5px;"><thead>{header}</thead><tbody>{rows}</tbody></table>',
        unsafe_allow_html=True,
    )


def _render_monday_checklist(df_pipe, df_deals, today, managers):
    """Авто-чеклист на понедельник на основе метрик выше."""
    overdue_cnt = len(_overdue_next_steps(df_deals, today, managers))
    stalled_cnt = len(_stalled_companies(df_pipe, today, managers))
    empty_cnt = len(_empty_result_touches(df_pipe, managers))

    curr_s, curr_e, prev_s, prev_e = _weekly_window(today)
    leader_mgr, leader_touches = None, 0
    for mgr in managers:
        t = _count_touches_in_window(df_pipe, curr_s, curr_e, [mgr])
        if t > leader_touches:
            leader_mgr, leader_touches = mgr, t

    items = []
    if overdue_cnt > 0:
        items.append(f'🔴 <b>Разобрать {overdue_cnt} просроченных next_step</b> — начать с самых давних, подтвердить новую дату или отметить отказ.')
    if stalled_cnt > 0:
        items.append(f'🟡 <b>Вернуться к {stalled_cnt} зависшим компаниям</b> (>7 дней без касания) — хотя бы один контакт каждому.')
    if empty_cnt > 0:
        items.append(f'🟠 <b>Заполнить результаты {empty_cnt} касаний</b> — иначе воронка теряет достоверность.')
    if leader_mgr and leader_touches > 0:
        items.append(f'🏆 <b>Повторить успех недели:</b> {_html.escape(leader_mgr)} держит темп ({leader_touches} касаний) — синк с командой о его подходе.')

    if not items:
        items = ['✓ Все базовые фокусы закрыты — можно сосредоточиться на качественном росте пайпа.']

    items_html = "".join(f'<li style="margin:6px 0;line-height:1.45;">{it}</li>' for it in items)
    st.markdown(
        f'<div class="panel" style="padding:14px 18px;background:#FFF8E1;border-color:#FFE082;">'
        f'<div style="font-size:13px;font-weight:700;color:#F57C00;text-transform:uppercase;letter-spacing:0.6px;'
        f'margin-bottom:8px;">📋 Чек-лист на понедельник</div>'
        f'<ul style="margin:0;padding-left:20px;font-size:14px;color:#2D3748;">{items_html}</ul>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────
def render_weekly_summary(df_pipe, df_deals, df_timeline, selected_managers, today):
    """Render full weekly summary page.

    Args:
        df_pipe: полный пайп (не отфильтрованный по периоду sidebar).
        df_deals: сделки CSM/BDM.
        df_timeline: таймлайн касаний (build_touches_timeline).
        selected_managers: список менеджеров из sidebar.
        today: date or Timestamp — «точка отсчёта» (обычно _data_max).
    """
    if df_pipe is None or df_pipe.empty:
        st.warning("Нет данных для формирования итогов недели.")
        return
    if not selected_managers:
        st.warning("Выберите хотя бы одного менеджера в сайдбаре.")
        return

    # 1. Подшапка с датами
    _render_period_banner(today)

    # 2. 5 KPI-карточек недели
    section_header(
        "Итоги недели — ключевые метрики",
        "Сравнение последних 7 дней с предыдущими 7 днями. Скользящее окно, не календарная неделя.",
    )
    _render_weekly_kpi_cards(df_pipe, df_deals, today, selected_managers)

    # 3. Динамика 30 дней
    section_header(
        "Динамика за 30 дней",
        "Касания по дням (по менеджерам) + пунктиром среднее за 7 дней. Светло-синий прямоугольник — текущая неделя.",
    )
    _render_activity_30d_chart(df_timeline, today, selected_managers)

    # 4. Таблица менеджер × метрика недели
    section_header(
        "Неделя по менеджерам",
        "Активность каждого BDM за текущую неделю + Δ касаний к предыдущей.",
    )
    _render_manager_week_table(df_pipe, df_deals, today, selected_managers)

    # 5. MTD vs прошлый MTD
    section_header(
        "Месяц-к-месяцу: MTD vs прошлый месяц",
        "Сравнение 1–сегодня текущего месяца с тем же периодом прошлого месяца.",
    )
    _render_mtd_comparison(df_pipe, df_deals, today, selected_managers)

    # 6. Успехи недели
    section_header(
        "Успехи недели",
        "Автоматические хайлайты: лидер по касаниям, крупнейшее КП, переходы в «Договор».",
    )
    _render_successes(df_pipe, df_deals, today, selected_managers)

    # 7. Фокус на следующую неделю (3 экспандера)
    section_header(
        "Фокус на следующую неделю",
        "Что требует внимания с понедельника: просрочки, зависшие компании, недозаполненные касания.",
    )

    overdue_cnt = len(_overdue_next_steps(df_deals, today, selected_managers))
    stalled_cnt = len(_stalled_companies(df_pipe, today, selected_managers))
    empty_cnt = len(_empty_result_touches(df_pipe, selected_managers))

    with st.expander(f"🔴 Просроченные next_step по сделкам ({overdue_cnt})", expanded=(overdue_cnt > 0 and overdue_cnt <= 15)):
        _render_focus_overdue(df_deals, today, selected_managers)

    with st.expander(f"🟡 Зависшие компании, >7 дней без касания ({stalled_cnt})", expanded=False):
        _render_focus_stalled(df_pipe, today, selected_managers)

    with st.expander(f"🟠 Пустые результаты касаний ({empty_cnt})", expanded=False):
        _render_focus_empty_results(df_pipe, selected_managers)

    # 8. Чеклист на понедельник
    _render_monday_checklist(df_pipe, df_deals, today, selected_managers)
