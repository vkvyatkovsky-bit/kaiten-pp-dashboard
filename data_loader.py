"""Load and clean data from Google Sheets or local xlsx."""

import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

from config import (
    DATA_SOURCE,
    SPREADSHEET_ID,
    XLSX_PATH,
    SHEET_PIPELINE,
    SHEET_LONGLIST,
    SHEET_DEALS,
    STATUS_MAP,
    LONGLISTS,
)

# ──────────────────────────────────────────────
# Google Sheets helpers
# ──────────────────────────────────────────────

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _get_gsheet_client():
    """Create gspread client from Streamlit secrets."""
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )
    return gspread.authorize(creds)


def _load_sheet_as_df(sheet_name):
    """Load a single Google Sheets worksheet into a DataFrame."""
    client = _get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(sheet_name)
    data = worksheet.get_all_values()
    if len(data) < 2:
        return pd.DataFrame()
    # Deduplicate headers (Google Sheets can have duplicate column names)
    headers = data[0]
    seen = {}
    unique_headers = []
    for h in headers:
        if h in seen:
            seen[h] += 1
            unique_headers.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            unique_headers.append(h)
    df = pd.DataFrame(data[1:], columns=unique_headers)
    df = df.replace("", pd.NA)
    return df


def _load_from_xlsx(sheet_name):
    """Load a sheet from local xlsx file."""
    return pd.read_excel(XLSX_PATH, sheet_name=sheet_name, dtype=str)


def _load_raw(sheet_name):
    """Load raw data from configured source."""
    if DATA_SOURCE == "gsheet":
        return _load_sheet_as_df(sheet_name)
    return _load_from_xlsx(sheet_name)


# ──────────────────────────────────────────────
# Public data loaders (same interface as before)
# ──────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_pipeline():
    """Load 'Общий пайп' sheet, drop empty rows, normalize statuses."""
    df = _load_raw(SHEET_PIPELINE)

    if df.empty:
        return pd.DataFrame()

    # Rename columns to standard names (by position)
    col_map = {
        df.columns[0]: "company",
        df.columns[1]: "manager",
        df.columns[2]: "website",
        df.columns[3]: "phone",
        df.columns[4]: "email",
        df.columns[5]: "inn",
        df.columns[6]: "city",
        df.columns[7]: "status",
    }
    touch_cols = [
        "touch_1_date", "touch_1_result",
        "touch_2_date", "touch_2_result",
        "touch_3_date", "touch_3_result",
        "touch_4_date", "touch_4_result",
        "touch_5_date", "touch_5_result",
    ]
    for i, name in enumerate(touch_cols):
        idx = 8 + i
        if idx < len(df.columns):
            col_map[df.columns[idx]] = name

    # Comments column comes after all touches (index 18 for 5 touches)
    _comments_idx = 8 + len(touch_cols)
    if len(df.columns) > _comments_idx:
        col_map[df.columns[_comments_idx]] = "comments"
    elif len(df.columns) > 17:
        col_map[df.columns[17]] = "comments"

    df = df.rename(columns=col_map)

    # Filter out rows without company name or manager
    df = df.dropna(subset=["company"])
    df = df[df["manager"].notna() & (df["manager"].str.strip() != "")]

    # Normalize statuses
    df["status_raw"] = df["status"].fillna("")
    df["status"] = df["status_raw"].str.strip().str.lower().map(STATUS_MAP).fillna("Прочее")

    # Parse touch dates (handle "23.03" without year → assume current year)
    _current_year = str(pd.Timestamp.now().year)
    for col in ["touch_1_date", "touch_2_date", "touch_3_date", "touch_4_date", "touch_5_date"]:
        if col in df.columns:
            # First try full parse
            parsed = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            # For NaT rows where original value looks like DD.MM — append current year
            _mask = parsed.isna() & df[col].notna() & df[col].astype(str).str.match(r'^\d{1,2}\.\d{1,2}\.?$')
            if _mask.any():
                _with_year = df.loc[_mask, col].astype(str).str.rstrip('.') + '.' + _current_year
                parsed.loc[_mask] = pd.to_datetime(_with_year, errors="coerce", dayfirst=True)
            df[col] = parsed

    df["manager"] = df["manager"].str.strip()
    df = df.reset_index(drop=True)
    return df


@st.cache_data(ttl=300)
def load_longlist():
    """Load 'Лонглист Белкин' sheet (legacy, kept for compatibility)."""
    df = _load_raw(SHEET_LONGLIST)
    if df.empty:
        return df
    if len(df.columns) > 0:
        df = df.dropna(subset=[df.columns[0]])
    return df


@st.cache_data(ttl=300)
def load_all_longlists():
    """Load all longlist sheets, return dict {manager_name: row_count}."""
    result = {}
    for sheet_name, manager in LONGLISTS.items():
        try:
            df = _load_raw(sheet_name)
            if not df.empty and len(df.columns) > 0:
                df = df.dropna(subset=[df.columns[0]])
                result[manager] = len(df)
            else:
                result[manager] = 0
        except Exception:
            result[manager] = 0
    return result


@st.cache_data(ttl=300)
def load_deals():
    """Load deals sheet, parse amounts. Supports new structure with Команда column."""
    df = _load_raw(SHEET_DEALS)

    if df.empty or len(df.columns) < 16:
        return pd.DataFrame()

    # New structure (24 cols): ID, Команда, Партнёр, Тип, Отв.партнёрки, Отв.продаж, Клиент, ...
    col_names = [
        "id", "team", "partner", "partner_type", "partner_manager", "sales_manager",
        "client", "segment", "tariff", "industry", "lead_source", "date_received",
        "deal_stage", "probability", "kp_amount", "kp_date", "planned_amount", "mrr",
        "start_date", "next_step", "next_step_date", "risk", "partner_role", "comment",
    ]
    col_map = {}
    for i, name in enumerate(col_names):
        if i < len(df.columns):
            col_map[df.columns[i]] = name

    # Backward compat: if col[1] is not a team marker (CSM/BDM), use old mapping
    _sample = str(df.iloc[0, 1]).strip().upper() if len(df) > 0 and len(df.columns) > 1 else ""
    if _sample not in ("CSM", "BDM", "KAM"):
        # Old structure without Команда column
        col_names_old = [
            "id", "partner", "partner_type", "manager", "client", "segment",
            "tariff", "industry", "lead_source", "date_received", "deal_stage",
            "probability", "kp_amount", "kp_date", "planned_amount", "mrr",
            "start_date", "next_step", "next_step_date", "risk", "partner_role", "comment",
        ]
        col_map = {}
        for i, name in enumerate(col_names_old):
            if i < len(df.columns):
                col_map[df.columns[i]] = name

    df = df.rename(columns=col_map)

    # Ensure team column exists
    if "team" not in df.columns:
        df["team"] = "CSM"
    # Ensure manager column (compat with old code)
    if "partner_manager" in df.columns and "manager" not in df.columns:
        df["manager"] = df["partner_manager"]

    # Filter out empty rows
    df = df.dropna(subset=["id"])

    # Parse numeric fields (strip spaces from formatted numbers like "6 960 000")
    for col in ["probability", "kp_amount", "planned_amount", "mrr"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r"\s+", "", regex=True)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Use kp_amount as fallback if planned_amount is 0
    if "planned_amount" in df.columns and "kp_amount" in df.columns:
        mask = df["planned_amount"] == 0
        df.loc[mask, "planned_amount"] = df.loc[mask, "kp_amount"]

    # Parse dates
    for date_col in ["date_received", "next_step_date"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)

    # Weighted pipeline = planned_amount * probability / 100
    if "planned_amount" in df.columns and "probability" in df.columns:
        df["weighted_amount"] = df["planned_amount"] * df["probability"] / 100

    # Days in pipeline = today - date_received
    if "date_received" in df.columns:
        df["days_in_pipeline"] = (pd.Timestamp.now() - df["date_received"]).dt.days

    # Next step overdue flag
    if "next_step_date" in df.columns:
        df["next_step_overdue"] = df["next_step_date"] < pd.Timestamp.now()

    df = df.reset_index(drop=True)
    return df


def _last_touch_date(row):
    """Return the latest non-null touch date for a pipeline row."""
    for col in ["touch_5_date", "touch_4_date", "touch_3_date", "touch_2_date", "touch_1_date"]:
        if col in row.index and pd.notna(row[col]):
            return row[col]
    return pd.NaT


def compute_bdm_kpi(df_pipeline, df_deals, manager_name, year_month=None):
    """Compute BDM personal KPI facts for a given manager and optional month.

    Args:
        df_pipeline: pipeline DataFrame
        df_deals: deals DataFrame
        manager_name: BDM manager name (e.g. "Ирина Баксанова")
        year_month: optional tuple (year, month) to filter by month, or None for all time

    Returns:
        dict with keys: activated, first_sale, revenue
    """
    # --- Activated partners: status "Договор" or "Подписан" for this manager ---
    mgr_pipe = df_pipeline[df_pipeline["manager"] == manager_name]
    activated_df = mgr_pipe[mgr_pipe["status"].isin(["Договор", "Подписан"])].copy()
    if year_month and not activated_df.empty:
        activated_df["_act_date"] = activated_df.apply(_last_touch_date, axis=1)
        activated_df = activated_df[
            (activated_df["_act_date"].dt.year == year_month[0])
            & (activated_df["_act_date"].dt.month == year_month[1])
        ]
    activated = len(activated_df)

    # --- First sale & Revenue: BDM deals with "оплачено" ---
    first_sale = 0
    revenue = 0
    if not df_deals.empty and "team" in df_deals.columns:
        bdm_deals = df_deals[
            (df_deals["team"].astype(str).str.upper() == "BDM")
            & (df_deals["partner_manager"].astype(str).str.strip() == manager_name)
        ]
        paid = bdm_deals[
            bdm_deals["deal_stage"].astype(str).str.lower().str.contains("оплачено", na=False)
        ]
        if year_month and not paid.empty and "date_received" in paid.columns:
            paid = paid[
                (paid["date_received"].dt.year == year_month[0])
                & (paid["date_received"].dt.month == year_month[1])
            ]
        first_sale = paid["partner"].nunique() if not paid.empty else 0
        revenue = paid["planned_amount"].sum() if not paid.empty else 0

    return {"activated": activated, "first_sale": first_sale, "revenue": revenue}


def build_touches_timeline(df_pipeline):
    """Build a timeline of all touches for activity dynamics chart."""
    records = []
    for _, row in df_pipeline.iterrows():
        manager = row["manager"]
        for i in range(1, 6):
            date_col = f"touch_{i}_date"
            if date_col in row.index and pd.notna(row[date_col]):
                records.append({
                    "manager": manager,
                    "date": row[date_col],
                    "company": row.get("company", ""),
                })
    if not records:
        return pd.DataFrame(columns=["manager", "date", "company", "week"])
    timeline = pd.DataFrame(records)
    timeline["week"] = timeline["date"].dt.to_period("W").apply(lambda p: p.start_time)
    return timeline
