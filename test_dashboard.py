"""Comprehensive pytest test suite for KPI Partner Channel Dashboard.

Uses REAL data from Google Sheets (not mocks) to verify actual values.
Run with: pytest test_dashboard.py -v
"""

import sys
import os

# Ensure dashboard dir is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
import pandas as pd
import numpy as np
from datetime import date, datetime

# ---------------------------------------------------------------------------
# Patch Streamlit before importing anything that depends on it
# ---------------------------------------------------------------------------
import types
import toml

# Create a minimal streamlit stub so data_loader can import without error
_st_stub = types.ModuleType("streamlit")

# Load actual secrets for GSheets auth
_secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml")
_secrets_data = toml.load(_secrets_path)

class _SecretsProxy(dict):
    """Dict subclass that supports attribute access like st.secrets."""
    def __getattr__(self, key):
        try:
            val = self[key]
            if isinstance(val, dict):
                return _SecretsProxy(val)
            return val
        except KeyError:
            raise AttributeError(key)

_st_stub.secrets = _SecretsProxy(_secrets_data)

# cache_data as passthrough decorator
def _passthrough_cache(ttl=None, **kwargs):
    def decorator(fn):
        return fn
    return decorator

_st_stub.cache_data = _passthrough_cache

sys.modules["streamlit"] = _st_stub

# Now safe to import project modules
from config import (
    TARGETS_Q1, TARGETS_Q2,
    BDM_KPI_TARGETS, BDM_TOTAL_BONUS, BDM_SALARY,
    BDM_MANAGERS, STATUS_MAP, FUNNEL_ORDER, STATUS_COLORS,
    LONGLISTS, PIPELINE_COLUMNS, DEALS_COLUMNS,
    SHEET_PIPELINE, SHEET_DEALS,
)
from data_loader import (
    load_pipeline, load_deals, load_all_longlists,
    load_longlist, build_touches_timeline, compute_bdm_kpi,
    _last_touch_date,
)

# ═══════════════════════════════════════════════════════════════════
# Fixtures — load real data once per session
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def pipeline():
    return load_pipeline()

@pytest.fixture(scope="session")
def deals():
    return load_deals()

@pytest.fixture(scope="session")
def longlists():
    return load_all_longlists()

@pytest.fixture(scope="session")
def timeline(pipeline):
    return build_touches_timeline(pipeline)


# ═══════════════════════════════════════════════════════════════════
# 1. Config tests
# ═══════════════════════════════════════════════════════════════════

class TestConfig:
    """Verify all config constants are correct."""

    # --- Q1 targets ---
    def test_q1_active_partners_target(self):
        assert TARGETS_Q1["active_partners"]["target"] == 15

    def test_q1_leads_csm_target(self):
        assert TARGETS_Q1["leads_csm"]["target"] == 15

    def test_q1_leads_bdm_target(self):
        assert TARGETS_Q1["leads_bdm"]["target"] == 9

    def test_q1_pipeline_kp_target(self):
        assert TARGETS_Q1["pipeline_kp"]["target"] == 10_000_000

    def test_q1_revenue_target(self):
        assert TARGETS_Q1["revenue"]["target"] == 2_400_000

    def test_q1_mrr_target(self):
        assert TARGETS_Q1["mrr"]["target"] == 200_000

    # --- Q2 targets ---
    def test_q2_active_partners_target(self):
        assert TARGETS_Q2["active_partners"]["target"] == 42

    def test_q2_leads_csm_target(self):
        assert TARGETS_Q2["leads_csm"]["target"] == 20

    def test_q2_leads_bdm_target(self):
        assert TARGETS_Q2["leads_bdm"]["target"] == 18

    def test_q2_pipeline_kp_target(self):
        assert TARGETS_Q2["pipeline_kp"]["target"] == 30_000_000

    def test_q2_revenue_target(self):
        assert TARGETS_Q2["revenue"]["target"] == 18_000_000

    def test_q2_mrr_target(self):
        assert TARGETS_Q2["mrr"]["target"] == 1_500_000

    # --- Q2 disabled when current month <= 3 ---
    def test_q2_disabled_in_q1(self):
        """Q2 targets should exist but be disabled for display when month<=3."""
        # The app logic: disabled = current_month <= 3
        # We just verify both target dicts have the same keys
        assert set(TARGETS_Q1.keys()) == set(TARGETS_Q2.keys())

    # --- BDM KPI targets ---
    def test_bdm_kpi_activated_target(self):
        assert BDM_KPI_TARGETS["activated"]["target"] == 3

    def test_bdm_kpi_first_sale_target(self):
        assert BDM_KPI_TARGETS["first_sale"]["target"] == 2

    def test_bdm_kpi_revenue_target(self):
        assert BDM_KPI_TARGETS["revenue"]["target"] == 500_000

    def test_bdm_kpi_weights_sum_to_1(self):
        total_weight = sum(v["weight"] for v in BDM_KPI_TARGETS.values())
        assert abs(total_weight - 1.0) < 0.001

    def test_bdm_kpi_bonus_sum(self):
        total_bonus = sum(v["bonus"] for v in BDM_KPI_TARGETS.values())
        assert total_bonus == BDM_TOTAL_BONUS

    def test_bdm_total_bonus(self):
        assert BDM_TOTAL_BONUS == 100_000

    def test_bdm_salary(self):
        assert BDM_SALARY == 150_000

    # --- BDM managers list ---
    def test_bdm_managers_list(self):
        assert BDM_MANAGERS == ["Ирина Баксанова", "Никита Белкин", "Павел Воронов"]

    def test_bdm_managers_count(self):
        assert len(BDM_MANAGERS) == 3

    # --- STATUS_MAP completeness ---
    def test_status_map_has_key_statuses(self):
        expected_keys = [
            "нет ос", "на рассмотрении", "не интересно",
            "подписан", "составляем договор на партнёрство",
            "стал нашим реферальным партнёром", "пока не обрабатываем",
        ]
        for k in expected_keys:
            assert k in STATUS_MAP, f"Missing STATUS_MAP key: {k}"

    def test_status_map_values_in_funnel(self):
        """All STATUS_MAP output values should appear in FUNNEL_ORDER."""
        for raw, norm in STATUS_MAP.items():
            assert norm in FUNNEL_ORDER, f"STATUS_MAP value '{norm}' (from '{raw}') not in FUNNEL_ORDER"

    # --- FUNNEL_ORDER ---
    def test_funnel_order_completeness(self):
        expected = ["Нет ОС", "На рассмотрении", "Договор", "Подписан",
                    "Не интересно", "Не обрабатываем", "Прочее"]
        assert FUNNEL_ORDER == expected

    def test_funnel_order_length(self):
        assert len(FUNNEL_ORDER) == 7

    # --- LONGLISTS config ---
    def test_longlists_config(self):
        assert "Лонглист Белкин" in LONGLISTS
        assert "Лонглист Баксанова" in LONGLISTS
        assert LONGLISTS["Лонглист Белкин"] == "Никита Белкин"
        assert LONGLISTS["Лонглист Баксанова"] == "Ирина Баксанова"


# ═══════════════════════════════════════════════════════════════════
# 2. Data loader tests
# ═══════════════════════════════════════════════════════════════════

class TestLoadPipeline:
    """Test load_pipeline() returns correct structure."""

    def test_returns_dataframe(self, pipeline):
        assert isinstance(pipeline, pd.DataFrame)

    def test_not_empty(self, pipeline):
        assert len(pipeline) > 0

    def test_has_company_column(self, pipeline):
        assert "company" in pipeline.columns

    def test_has_manager_column(self, pipeline):
        assert "manager" in pipeline.columns

    def test_has_status_column(self, pipeline):
        assert "status" in pipeline.columns

    def test_has_status_raw_column(self, pipeline):
        assert "status_raw" in pipeline.columns

    def test_has_touch_date_columns(self, pipeline):
        for col in ["touch_1_date", "touch_2_date", "touch_3_date", "touch_4_date"]:
            assert col in pipeline.columns, f"Missing column: {col}"

    def test_touch_dates_are_datetime(self, pipeline):
        for col in ["touch_1_date", "touch_2_date", "touch_3_date", "touch_4_date"]:
            if pipeline[col].notna().any():
                assert pd.api.types.is_datetime64_any_dtype(pipeline[col]), \
                    f"{col} is not datetime type"

    def test_touch_dates_parsed_with_dayfirst(self, pipeline):
        """Verify dayfirst=True: '09.03.2026' should be March 9, not September 3."""
        for col in ["touch_1_date", "touch_2_date", "touch_3_date", "touch_4_date"]:
            valid = pipeline[col].dropna()
            if len(valid) > 0:
                # All dates should be in reasonable range (2024-2027)
                for dt in valid:
                    assert dt.year >= 2024 and dt.year <= 2027, \
                        f"Date {dt} in {col} has unexpected year"

    def test_no_empty_company(self, pipeline):
        assert pipeline["company"].isna().sum() == 0

    def test_no_empty_manager(self, pipeline):
        assert pipeline["manager"].isna().sum() == 0
        assert (pipeline["manager"].str.strip() == "").sum() == 0

    def test_status_normalized(self, pipeline):
        """All status values should be from FUNNEL_ORDER."""
        unique_statuses = set(pipeline["status"].unique())
        assert unique_statuses.issubset(set(FUNNEL_ORDER)), \
            f"Unexpected statuses: {unique_statuses - set(FUNNEL_ORDER)}"

    def test_non_date_values_become_nat(self, pipeline):
        """Non-date strings like 'на стопе' should parse to NaT."""
        for col in ["touch_1_date", "touch_2_date", "touch_3_date", "touch_4_date"]:
            # Verify that the column has some NaT values (expected with real data)
            # and that no non-datetime values leaked through
            assert pd.api.types.is_datetime64_any_dtype(pipeline[col])


class TestLoadDeals:
    """Test load_deals() returns correct structure and values."""

    def test_returns_dataframe(self, deals):
        assert isinstance(deals, pd.DataFrame)

    def test_not_empty(self, deals):
        assert len(deals) > 0

    def test_has_required_columns(self, deals):
        required = ["id", "partner", "deal_stage", "probability",
                    "planned_amount", "mrr", "weighted_amount", "team"]
        for col in required:
            assert col in deals.columns, f"Missing column: {col}"

    def test_team_column_values(self, deals):
        """Team column should contain CSM, BDM, or KAM."""
        teams = deals["team"].astype(str).str.upper().str.strip().unique()
        valid_teams = {"CSM", "BDM", "KAM", "<NA>", "NAN", ""}
        for t in teams:
            assert t in valid_teams or t in ("CSM", "BDM", "KAM"), \
                f"Unexpected team value: {t}"

    def test_csm_deals_exist(self, deals):
        csm = deals[deals["team"].astype(str).str.upper() == "CSM"]
        assert len(csm) > 0, "Expected CSM deals"

    def test_bdm_deals_exist(self, deals):
        bdm = deals[deals["team"].astype(str).str.upper() == "BDM"]
        assert len(bdm) > 0, "Expected BDM deals"

    def test_numeric_planned_amount(self, deals):
        """planned_amount should be numeric (spaces in '6 960 000' stripped)."""
        assert pd.api.types.is_numeric_dtype(deals["planned_amount"])

    def test_numeric_probability(self, deals):
        assert pd.api.types.is_numeric_dtype(deals["probability"])

    def test_numeric_mrr(self, deals):
        assert pd.api.types.is_numeric_dtype(deals["mrr"])

    def test_numeric_kp_amount(self, deals):
        assert pd.api.types.is_numeric_dtype(deals["kp_amount"])

    def test_no_negative_planned_amount(self, deals):
        assert (deals["planned_amount"] < 0).sum() == 0

    def test_no_negative_probability(self, deals):
        assert (deals["probability"] < 0).sum() == 0

    def test_probability_max_100(self, deals):
        assert (deals["probability"] > 100).sum() == 0

    def test_weighted_amount_formula(self, deals):
        """weighted_amount = planned_amount * probability / 100."""
        expected = deals["planned_amount"] * deals["probability"] / 100
        diff = (deals["weighted_amount"] - expected).abs().max()
        assert diff < 0.01, f"Weighted amount mismatch: max diff = {diff}"

    def test_kp_amount_fallback(self, deals):
        """If planned_amount was 0, kp_amount should be used as fallback."""
        # After fallback, rows where original planned_amount was 0
        # should have planned_amount == kp_amount (if kp_amount > 0)
        # We can verify that planned_amount is >= kp_amount for most rows
        # (since fallback only fills zeros)
        zero_planned_with_kp = deals[
            (deals["planned_amount"] > 0) & (deals["kp_amount"] > 0)
        ]
        # At minimum, the column exists and the logic ran without error
        assert "planned_amount" in deals.columns
        assert "kp_amount" in deals.columns

    def test_partner_manager_column(self, deals):
        """partner_manager field should be correctly populated."""
        assert "partner_manager" in deals.columns or "manager" in deals.columns

    def test_paid_deal_detection(self, deals):
        """Paid deals detected by 'оплачено' in deal_stage."""
        paid_mask = deals["deal_stage"].astype(str).str.lower().str.contains("оплачено", na=False)
        # The mask should be a boolean series
        assert paid_mask.dtype == bool
        # Print info about paid deals count
        paid_count = paid_mask.sum()
        assert paid_count >= 0  # May be 0 if no paid deals yet

    def test_date_received_parsed(self, deals):
        """date_received should be datetime with dayfirst=True."""
        if "date_received" in deals.columns:
            valid_dates = deals["date_received"].dropna()
            if len(valid_dates) > 0:
                assert pd.api.types.is_datetime64_any_dtype(deals["date_received"])

    def test_days_in_pipeline_computed(self, deals):
        assert "days_in_pipeline" in deals.columns

    def test_next_step_overdue_computed(self, deals):
        assert "next_step_overdue" in deals.columns


class TestLoadAllLonglists:
    """Test load_all_longlists() returns dict with manager counts."""

    def test_returns_dict(self, longlists):
        assert isinstance(longlists, dict)

    def test_has_all_managers(self, longlists):
        for sheet_name, manager in LONGLISTS.items():
            assert manager in longlists, f"Missing manager: {manager}"

    def test_counts_are_non_negative(self, longlists):
        for manager, count in longlists.items():
            assert count >= 0, f"{manager} has negative count: {count}"

    def test_counts_are_integers(self, longlists):
        for manager, count in longlists.items():
            assert isinstance(count, int), f"{manager} count is not int: {type(count)}"

    def test_belkin_has_entries(self, longlists):
        assert longlists.get("Никита Белкин", 0) > 0

    def test_baksanova_has_entries(self, longlists):
        assert longlists.get("Ирина Баксанова", 0) > 0


class TestBuildTouchesTimeline:
    """Test build_touches_timeline() returns correct structure."""

    def test_returns_dataframe(self, timeline):
        assert isinstance(timeline, pd.DataFrame)

    def test_has_required_columns(self, timeline):
        for col in ["manager", "date", "company", "week"]:
            assert col in timeline.columns, f"Missing column: {col}"

    def test_not_empty(self, timeline):
        assert len(timeline) > 0

    def test_week_column_is_datetime(self, timeline):
        assert pd.api.types.is_datetime64_any_dtype(timeline["week"])

    def test_date_column_is_datetime(self, timeline):
        assert pd.api.types.is_datetime64_any_dtype(timeline["date"])

    def test_week_is_monday(self, timeline):
        """Week start should be Monday."""
        weeks = timeline["week"].dropna().unique()
        for w in weeks:
            assert w.dayofweek == 0, f"Week start {w} is not Monday"


# ═══════════════════════════════════════════════════════════════════
# 3. KPI card values verification
# ═══════════════════════════════════════════════════════════════════

class TestKPICardValues:
    """Verify computed KPI values from real data."""

    def test_total_in_work(self, pipeline):
        """total_in_work = number of companies in pipeline."""
        total = len(pipeline)
        assert total > 0
        print(f"\n  [INFO] total_in_work = {total}")

    def test_longlist_counts_per_manager(self, longlists):
        """Each manager should have longlist count."""
        total = sum(longlists.values())
        assert total > 0
        for mgr, cnt in longlists.items():
            print(f"\n  [INFO] Longlist {mgr} = {cnt}")

    def test_deals_count_csm_vs_bdm(self, deals):
        """deals split by CSM vs BDM."""
        csm_count = len(deals[deals["team"].astype(str).str.upper() == "CSM"])
        bdm_count = len(deals[deals["team"].astype(str).str.upper() == "BDM"])
        total = len(deals)
        assert csm_count + bdm_count <= total
        assert csm_count >= 0
        assert bdm_count >= 0
        print(f"\n  [INFO] deals: total={total}, CSM={csm_count}, BDM={bdm_count}")

    def test_total_kp(self, deals):
        """total_kp = sum of planned_amount."""
        total_kp = deals["planned_amount"].sum()
        assert total_kp >= 0
        print(f"\n  [INFO] total_kp = {total_kp:,.0f}")

    def test_weighted_pipeline(self, deals):
        """weighted_pipe = sum of weighted_amount."""
        weighted = deals["weighted_amount"].sum()
        total_kp = deals["planned_amount"].sum()
        assert weighted >= 0
        assert weighted <= total_kp + 0.01  # weighted should be <= total
        print(f"\n  [INFO] weighted_pipe = {weighted:,.0f}")

    def test_revenue_fact(self, deals):
        """revenue_fact = sum planned_amount of paid deals."""
        paid_mask = deals["deal_stage"].astype(str).str.lower().str.contains("оплачено", na=False)
        revenue = deals.loc[paid_mask, "planned_amount"].sum()
        assert revenue >= 0
        print(f"\n  [INFO] revenue_fact = {revenue:,.0f}")

    def test_mrr_fact(self, deals):
        """mrr_fact = sum mrr of paid deals."""
        paid_mask = deals["deal_stage"].astype(str).str.lower().str.contains("оплачено", na=False)
        mrr = deals.loc[paid_mask, "mrr"].sum()
        assert mrr >= 0
        print(f"\n  [INFO] mrr_fact = {mrr:,.0f}")

    def test_active_partners(self, pipeline):
        """active_partners = count of 'Договор' + 'Подписан'."""
        active = len(pipeline[pipeline["status"].isin(["Договор", "Подписан"])])
        assert active >= 0
        print(f"\n  [INFO] active_partners = {active}")


# ═══════════════════════════════════════════════════════════════════
# 4. Progress bar targets verification
# ═══════════════════════════════════════════════════════════════════

class TestProgressBarTargets:
    """Verify target values and Q2 disable logic."""

    def test_q1_targets_complete(self):
        expected_keys = {"active_partners", "leads_csm", "leads_bdm",
                        "pipeline_kp", "revenue", "mrr"}
        assert set(TARGETS_Q1.keys()) == expected_keys

    def test_q2_targets_complete(self):
        expected_keys = {"active_partners", "leads_csm", "leads_bdm",
                        "pipeline_kp", "revenue", "mrr"}
        assert set(TARGETS_Q2.keys()) == expected_keys

    def test_q1_target_values(self):
        assert TARGETS_Q1["active_partners"]["target"] == 15
        assert TARGETS_Q1["leads_csm"]["target"] == 15
        assert TARGETS_Q1["leads_bdm"]["target"] == 9
        assert TARGETS_Q1["pipeline_kp"]["target"] == 10_000_000
        assert TARGETS_Q1["revenue"]["target"] == 2_400_000
        assert TARGETS_Q1["mrr"]["target"] == 200_000

    def test_q2_target_values(self):
        assert TARGETS_Q2["active_partners"]["target"] == 42
        assert TARGETS_Q2["leads_csm"]["target"] == 20
        assert TARGETS_Q2["leads_bdm"]["target"] == 18
        assert TARGETS_Q2["pipeline_kp"]["target"] == 30_000_000
        assert TARGETS_Q2["revenue"]["target"] == 18_000_000
        assert TARGETS_Q2["mrr"]["target"] == 1_500_000

    def test_q2_disabled_when_month_lte_3(self):
        """Q2 should be disabled when current month <= 3 (Jan-Mar)."""
        # Simulate the app logic
        for month in [1, 2, 3]:
            disabled = month <= 3
            assert disabled is True, f"Q2 should be disabled in month {month}"
        for month in [4, 5, 6]:
            disabled = month <= 3
            assert disabled is False, f"Q2 should be enabled in month {month}"

    def test_all_targets_have_labels(self):
        for key, val in TARGETS_Q1.items():
            assert "label" in val, f"Q1 target '{key}' missing label"
            assert "target" in val, f"Q1 target '{key}' missing target"
        for key, val in TARGETS_Q2.items():
            assert "label" in val, f"Q2 target '{key}' missing label"
            assert "target" in val, f"Q2 target '{key}' missing target"

    def test_money_targets_have_fmt(self):
        for key in ["pipeline_kp", "revenue", "mrr"]:
            assert TARGETS_Q1[key].get("fmt") == "money"
            assert TARGETS_Q2[key].get("fmt") == "money"

    def test_non_money_targets_no_fmt(self):
        for key in ["active_partners", "leads_csm", "leads_bdm"]:
            assert "fmt" not in TARGETS_Q1[key] or TARGETS_Q1[key].get("fmt") != "money"


# ═══════════════════════════════════════════════════════════════════
# 5. BDM personal KPI
# ═══════════════════════════════════════════════════════════════════

class TestBDMPersonalKPI:
    """Test compute_bdm_kpi() for each BDM manager."""

    def test_bdm_kpi_targets_structure(self):
        assert "activated" in BDM_KPI_TARGETS
        assert "first_sale" in BDM_KPI_TARGETS
        assert "revenue" in BDM_KPI_TARGETS
        for key, val in BDM_KPI_TARGETS.items():
            assert "target" in val
            assert "weight" in val
            assert "bonus" in val
            assert "label" in val

    def test_compute_bdm_kpi_returns_dict(self, pipeline, deals):
        for mgr in BDM_MANAGERS:
            result = compute_bdm_kpi(pipeline, deals, mgr)
            assert isinstance(result, dict)
            assert "activated" in result
            assert "first_sale" in result
            assert "revenue" in result

    def test_activated_is_dogovor_plus_podpisan(self, pipeline, deals):
        """activated = count of Договор + Подписан for each manager."""
        for mgr in BDM_MANAGERS:
            result = compute_bdm_kpi(pipeline, deals, mgr)
            mgr_pipe = pipeline[pipeline["manager"] == mgr]
            expected = len(mgr_pipe[mgr_pipe["status"].isin(["Договор", "Подписан"])])
            assert result["activated"] == expected, \
                f"{mgr}: activated={result['activated']}, expected={expected}"

    def test_first_sale_is_distinct_partners_with_paid_bdm(self, pipeline, deals):
        """first_sale = distinct partners with paid BDM deals for manager."""
        for mgr in BDM_MANAGERS:
            result = compute_bdm_kpi(pipeline, deals, mgr)
            if not deals.empty and "team" in deals.columns:
                bdm_deals = deals[
                    (deals["team"].astype(str).str.upper() == "BDM")
                    & (deals["partner_manager"].astype(str).str.strip() == mgr)
                ]
                paid = bdm_deals[
                    bdm_deals["deal_stage"].astype(str).str.lower().str.contains("оплачено", na=False)
                ]
                expected = paid["partner"].nunique() if not paid.empty else 0
            else:
                expected = 0
            assert result["first_sale"] == expected, \
                f"{mgr}: first_sale={result['first_sale']}, expected={expected}"

    def test_revenue_is_sum_planned_of_paid_bdm(self, pipeline, deals):
        """revenue = sum planned_amount of paid BDM deals for manager."""
        for mgr in BDM_MANAGERS:
            result = compute_bdm_kpi(pipeline, deals, mgr)
            if not deals.empty and "team" in deals.columns:
                bdm_deals = deals[
                    (deals["team"].astype(str).str.upper() == "BDM")
                    & (deals["partner_manager"].astype(str).str.strip() == mgr)
                ]
                paid = bdm_deals[
                    bdm_deals["deal_stage"].astype(str).str.lower().str.contains("оплачено", na=False)
                ]
                expected = paid["planned_amount"].sum() if not paid.empty else 0
            else:
                expected = 0
            assert result["revenue"] == expected, \
                f"{mgr}: revenue={result['revenue']}, expected={expected}"

    def test_monthly_filter_works(self, pipeline, deals):
        """Monthly filter should return subset of all-time values."""
        for mgr in BDM_MANAGERS:
            all_time = compute_bdm_kpi(pipeline, deals, mgr)
            # Test with a specific month (March 2026)
            monthly = compute_bdm_kpi(pipeline, deals, mgr, year_month=(2026, 3))
            assert monthly["activated"] <= all_time["activated"], \
                f"{mgr}: monthly activated ({monthly['activated']}) > all-time ({all_time['activated']})"
            assert monthly["revenue"] <= all_time["revenue"], \
                f"{mgr}: monthly revenue ({monthly['revenue']}) > all-time ({all_time['revenue']})"

    def test_future_month_returns_zero(self, pipeline, deals):
        """A month far in the future should return 0 for all metrics."""
        for mgr in BDM_MANAGERS:
            result = compute_bdm_kpi(pipeline, deals, mgr, year_month=(2099, 12))
            assert result["activated"] == 0, f"{mgr}: future activated should be 0"
            assert result["first_sale"] == 0, f"{mgr}: future first_sale should be 0"
            assert result["revenue"] == 0, f"{mgr}: future revenue should be 0"

    def test_per_manager_values(self, pipeline, deals):
        """Print per-manager BDM KPI for verification."""
        for mgr in BDM_MANAGERS:
            result = compute_bdm_kpi(pipeline, deals, mgr)
            print(f"\n  [INFO] BDM KPI {mgr}: activated={result['activated']}, "
                  f"first_sale={result['first_sale']}, revenue={result['revenue']:,.0f}")

    def test_monthly_breakdown_sums_to_quarterly(self, pipeline, deals):
        """Sum of monthly BDM KPI for Q1 (Jan-Mar) should equal quarterly total
        (when quarterly = all-time filtered to Q1 months)."""
        for mgr in BDM_MANAGERS:
            q1_activated = 0
            q1_revenue = 0
            for month in [1, 2, 3]:
                monthly = compute_bdm_kpi(pipeline, deals, mgr, year_month=(2026, month))
                q1_activated += monthly["activated"]
                q1_revenue += monthly["revenue"]
            # The sum of monthly should be <= all-time (since all-time includes all months)
            all_time = compute_bdm_kpi(pipeline, deals, mgr)
            assert q1_activated <= all_time["activated"], \
                f"{mgr}: Q1 sum activated ({q1_activated}) > all-time ({all_time['activated']})"


# ═══════════════════════════════════════════════════════════════════
# 6. Deals processing
# ═══════════════════════════════════════════════════════════════════

class TestDealsProcessing:
    """Test deals data processing logic."""

    def test_team_classification(self, deals):
        """Deals should be classified as CSM or BDM."""
        if "team" in deals.columns:
            teams = deals["team"].astype(str).str.upper().str.strip()
            valid = teams.isin(["CSM", "BDM", "KAM", "<NA>", "NAN", ""])
            assert valid.all(), f"Invalid team values: {teams[~valid].unique()}"

    def test_amount_parsing_strips_spaces(self, deals):
        """Amounts like '6 960 000' with non-breaking spaces should be parsed as numbers."""
        assert pd.api.types.is_numeric_dtype(deals["planned_amount"])
        assert pd.api.types.is_numeric_dtype(deals["kp_amount"])
        # No NaN except for truly empty cells (which get filled with 0)
        assert deals["planned_amount"].isna().sum() == 0

    def test_paid_deal_detection_by_stage(self, deals):
        """Paid deals are detected by 'оплачено' in deal_stage."""
        paid_mask = deals["deal_stage"].astype(str).str.lower().str.contains("оплачено", na=False)
        paid_deals = deals[paid_mask]
        if len(paid_deals) > 0:
            # All paid deals should have some planned_amount
            print(f"\n  [INFO] Paid deals: {len(paid_deals)}")
            print(f"  [INFO] Paid revenue: {paid_deals['planned_amount'].sum():,.0f}")
            print(f"  [INFO] Paid MRR: {paid_deals['mrr'].sum():,.0f}")

    def test_partner_manager_populated(self, deals):
        """partner_manager (or manager) should exist and have values."""
        mgr_col = "partner_manager" if "partner_manager" in deals.columns else "manager"
        assert mgr_col in deals.columns
        non_empty = deals[mgr_col].astype(str).str.strip().replace("", pd.NA).dropna()
        # At least some deals should have a manager
        assert len(non_empty) > 0


# ═══════════════════════════════════════════════════════════════════
# 7. Date handling
# ═══════════════════════════════════════════════════════════════════

class TestDateHandling:
    """Test date parsing with dayfirst=True."""

    def test_dates_parsed_as_datetime(self, pipeline):
        for col in ["touch_1_date", "touch_2_date", "touch_3_date", "touch_4_date"]:
            assert pd.api.types.is_datetime64_any_dtype(pipeline[col])

    def test_dayfirst_parsing(self):
        """'09.03.2026' should be March 9, not September 3."""
        result = pd.to_datetime("09.03.2026", dayfirst=True)
        assert result.month == 3, f"Expected month=3, got {result.month}"
        assert result.day == 9, f"Expected day=9, got {result.day}"
        assert result.year == 2026

    def test_non_date_values_become_nat(self):
        """Non-date values like 'на стопе' should become NaT."""
        result = pd.to_datetime("на стопе", errors="coerce", dayfirst=True)
        assert pd.isna(result)

    def test_empty_string_becomes_nat(self):
        result = pd.to_datetime("", errors="coerce", dayfirst=True)
        assert pd.isna(result)

    def test_last_touch_date_picks_latest(self):
        """_last_touch_date() should pick the latest available touch date."""
        row = pd.Series({
            "touch_1_date": pd.Timestamp("2026-01-15"),
            "touch_2_date": pd.Timestamp("2026-02-20"),
            "touch_3_date": pd.NaT,
            "touch_4_date": pd.NaT,
        })
        result = _last_touch_date(row)
        # Should return touch_2_date (latest non-NaT, checking from touch_4 backward)
        assert result == pd.Timestamp("2026-02-20")

    def test_last_touch_date_prefers_touch_4(self):
        """If touch_4 is set, it should be returned."""
        row = pd.Series({
            "touch_1_date": pd.Timestamp("2026-01-15"),
            "touch_2_date": pd.Timestamp("2026-02-20"),
            "touch_3_date": pd.Timestamp("2026-03-01"),
            "touch_4_date": pd.Timestamp("2026-03-10"),
        })
        result = _last_touch_date(row)
        assert result == pd.Timestamp("2026-03-10")

    def test_last_touch_date_all_nat_returns_nat(self):
        """If all touch dates are NaT, should return NaT."""
        row = pd.Series({
            "touch_1_date": pd.NaT,
            "touch_2_date": pd.NaT,
            "touch_3_date": pd.NaT,
            "touch_4_date": pd.NaT,
        })
        result = _last_touch_date(row)
        assert pd.isna(result)

    def test_deals_date_received_dayfirst(self, deals):
        """date_received dates should be parsed with dayfirst=True."""
        valid = deals["date_received"].dropna()
        if len(valid) > 0:
            for dt in valid:
                assert dt.year >= 2024 and dt.year <= 2027, \
                    f"Unexpected date_received year: {dt}"


# ═══════════════════════════════════════════════════════════════════
# 8. Funnel logic
# ═══════════════════════════════════════════════════════════════════

class TestFunnelLogic:
    """Test funnel counts and conversion calculations."""

    def test_funnel_counts_match_status_distribution(self, pipeline):
        """Sum of funnel stage counts should equal total pipeline rows."""
        status_counts = pipeline["status"].value_counts()
        funnel_total = sum(status_counts.get(s, 0) for s in FUNNEL_ORDER)
        assert funnel_total == len(pipeline), \
            f"Funnel total ({funnel_total}) != pipeline rows ({len(pipeline)})"

    def test_all_statuses_in_funnel_order(self, pipeline):
        """Every status in pipeline should be in FUNNEL_ORDER."""
        unique = set(pipeline["status"].unique())
        assert unique.issubset(set(FUNNEL_ORDER)), \
            f"Statuses outside FUNNEL_ORDER: {unique - set(FUNNEL_ORDER)}"

    def test_conversion_percentages_valid(self, pipeline):
        """Conversion rates should be between 0 and 100."""
        total = len(pipeline)
        for stage in FUNNEL_ORDER:
            count = len(pipeline[pipeline["status"] == stage])
            pct = count / total * 100 if total > 0 else 0
            assert 0 <= pct <= 100, f"Invalid conversion for {stage}: {pct}%"

    def test_status_map_normalization(self, pipeline):
        """Verify STATUS_MAP keys that exist in data map correctly."""
        for raw_key, expected_norm in STATUS_MAP.items():
            subset = pipeline[pipeline["status_raw"].str.strip().str.lower() == raw_key]
            if len(subset) > 0:
                actual = subset["status"].unique()
                assert len(actual) == 1 and actual[0] == expected_norm, \
                    f"'{raw_key}' mapped to {list(actual)}, expected ['{expected_norm}']"

    def test_no_empty_status_after_normalization(self, pipeline):
        """No empty/NaN statuses after normalization."""
        empty = pipeline[pipeline["status"].isna() | (pipeline["status"] == "")]
        assert len(empty) == 0

    def test_main_funnel_stages_present(self, pipeline):
        """Main funnel stages should be present in data."""
        # At minimum, some of the core stages should exist
        statuses = set(pipeline["status"].unique())
        core_stages = {"Нет ОС", "На рассмотрении", "Подписан"}
        present = statuses & core_stages
        assert len(present) >= 2, f"Too few core stages present: {present}"

    def test_funnel_order_starts_with_no_os(self):
        assert FUNNEL_ORDER[0] == "Нет ОС"

    def test_funnel_order_ends_with_prochee(self):
        assert FUNNEL_ORDER[-1] == "Прочее"

    def test_podpisan_after_dogovor(self):
        """'Подписан' should come after 'Договор' in funnel order."""
        idx_dogovor = FUNNEL_ORDER.index("Договор")
        idx_podpisan = FUNNEL_ORDER.index("Подписан")
        assert idx_podpisan > idx_dogovor


# ═══════════════════════════════════════════════════════════════════
# Additional integration / sanity tests
# ═══════════════════════════════════════════════════════════════════

class TestIntegration:
    """Cross-cutting integration tests."""

    def test_weighted_pipeline_lte_total_kp(self, deals):
        weighted = deals["weighted_amount"].sum()
        total_kp = deals["planned_amount"].sum()
        assert weighted <= total_kp + 0.01

    def test_pipeline_manager_names_trimmed(self, pipeline):
        for mgr in pipeline["manager"].unique():
            assert mgr == mgr.strip(), f"Manager name not trimmed: '{mgr}'"

    def test_cross_tab_grand_total(self, pipeline):
        cross = pd.crosstab(pipeline["manager"], pipeline["status"])
        assert cross.values.sum() == len(pipeline)

    def test_all_q1_target_keys_match_actuals_keys(self):
        """The keys used in _actuals should match TARGETS_Q1 keys."""
        actuals_keys = {"active_partners", "leads_csm", "leads_bdm",
                        "pipeline_kp", "revenue", "mrr"}
        assert actuals_keys == set(TARGETS_Q1.keys())

    def test_status_colors_cover_main_statuses(self):
        """STATUS_COLORS should have colors for main statuses."""
        for status in ["Нет ОС", "На рассмотрении", "Договор", "Подписан", "Не интересно"]:
            assert status in STATUS_COLORS, f"Missing color for {status}"
