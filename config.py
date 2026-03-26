"""Configuration for KPI Partner Channel Dashboard."""

from pathlib import Path

# --- Data source mode: "gsheet" or "xlsx" ---
DATA_SOURCE = "gsheet"

# --- Google Sheets ---
SPREADSHEET_ID = "10-x50buPtV6FtfwnZ0U6qNcXEy0fpECeoXJwlqEzo7s"

# --- Local xlsx fallback ---
XLSX_PATH = Path(__file__).parent / "data" / "pipeline.xlsx"  # local fallback only

# --- Sheet names ---
SHEET_PIPELINE = "Общий пайп"
SHEET_LONGLIST = "Лонглист Белкин"
SHEET_DEALS = "Сделки партнёров CSM\\KAM\\BDM"

# --- All longlists: sheet_name → manager name ---
LONGLISTS = {
    "Лонглист Белкин": "Никита Белкин",
    "Лонглист Баксанова": "Ирина Баксанова",
    "Лонглист Воронов": "Павел Воронов",
}

# --- Column mappings: Общий пайп / Лонглист ---
PIPELINE_COLUMNS = {
    "A": "company",
    "B": "manager",
    "C": "website",
    "D": "phone",
    "E": "email",
    "F": "inn",
    "G": "city",
    "H": "status",
    "I": "touch_1_date",
    "J": "touch_1_result",
    "K": "touch_2_date",
    "L": "touch_2_result",
    "M": "touch_3_date",
    "N": "touch_3_result",
    "O": "touch_4_date",
    "P": "touch_4_result",
    "R": "comments",
}

# --- Column mappings: Сделки партнёров ---
DEALS_COLUMNS = {
    "A": "id",
    "B": "partner",
    "C": "partner_type",
    "D": "manager",
    "E": "client",
    "F": "segment",
    "G": "tariff",
    "H": "industry",
    "I": "lead_source",
    "J": "date_received",
    "K": "deal_stage",
    "L": "probability",
    "M": "kp_amount",
    "N": "kp_date",
    "O": "planned_amount",
    "P": "mrr",
    "Q": "start_date",
    "R": "next_step",
    "S": "next_step_date",
    "T": "risk",
    "U": "partner_role",
    "V": "comment",
}

# --- Status normalization ---
STATUS_MAP = {
    "нет ос": "Нет ОС",
    "на рассмотрении": "На рассмотрении",
    "не интересно": "Не интересно",
    "подписан": "Подписан",
    "составляем договор на партнёрство": "Договор",
    "стал нашим реферальным партнёром": "Подписан",
    "пока не обрабатываем": "Не обрабатываем",
}

# --- Funnel order (top to bottom) ---
FUNNEL_ORDER = [
    "Нет ОС",
    "На рассмотрении",
    "Договор",
    "Подписан",
    "Не интересно",
    "Не обрабатываем",
    "Прочее",
]

# --- Status colors ---
STATUS_COLORS = {
    "Нет ОС": "#B0BEC5",
    "На рассмотрении": "#FFB74D",
    "Договор": "#4FC3F7",
    "Подписан": "#81C784",
    "Не интересно": "#E57373",
    "Не обрабатываем": "#CE93D8",
}

# --- Manager colors ---
MANAGER_COLORS = {
    "Ирина Баксанова": "#42A5F5",
    "Никита Белкин": "#66BB6A",
    "Воронов Павел": "#FFA726",
}

# --- Targets by quarter (from KPI document) ---
TARGETS_Q1 = {
    "active_partners": {"label": "Активных партнёров", "target": 15, "source": "KPI Partner Lead"},
    "leads_csm": {"label": "Лиды CSM", "target": 15, "source": "KPI Partner Lead"},
    "leads_bdm": {"label": "Лиды BDM", "target": 9, "source": "KPI Partner Lead"},
    "pipeline_kp": {"label": "Сумма КП", "target": 10_000_000, "source": "KPI Partner Lead", "fmt": "money"},
    "revenue": {"label": "Revenue", "target": 2_400_000, "source": "KPI Partner Lead", "fmt": "money"},
    "mrr": {"label": "MRR", "target": 200_000, "source": "KPI Partner Lead", "fmt": "money"},
}

TARGETS_Q2 = {
    "active_partners": {"label": "Активных партнёров", "target": 42, "source": "KPI Partner Lead"},
    "leads_csm": {"label": "Лиды CSM", "target": 20, "source": "KPI Partner Lead"},
    "leads_bdm": {"label": "Лиды BDM", "target": 18, "source": "KPI Partner Lead"},
    "pipeline_kp": {"label": "Сумма КП", "target": 30_000_000, "source": "KPI Partner Lead", "fmt": "money"},
    "revenue": {"label": "Revenue", "target": 18_000_000, "source": "KPI Partner Lead", "fmt": "money"},
    "mrr": {"label": "MRR", "target": 1_500_000, "source": "KPI Partner Lead", "fmt": "money"},
}

# --- BDM personal KPI (monthly, per manager) ---
BDM_KPI_TARGETS = {
    "activated": {"label": "Активированные партнёры", "target": 3, "weight": 0.3, "bonus": 30_000},
    "first_sale": {"label": "Партнёры с первой продажей", "target": 2, "weight": 0.4, "bonus": 40_000},
    "revenue": {"label": "Выручка партнёров", "target": 500_000, "weight": 0.3, "bonus": 30_000, "fmt": "money"},
}
BDM_TOTAL_BONUS = 100_000
BDM_SALARY = 150_000

# --- BDM managers list ---
BDM_MANAGERS = ["Ирина Баксанова", "Никита Белкин", "Павел Воронов"]
