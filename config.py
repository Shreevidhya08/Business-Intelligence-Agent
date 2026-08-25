"""
config.py

Central place for environment variables, board IDs, and column ID
mappings. Keeping these here (instead of scattered across files) means
when monday's schema changes or you add columns, there's one place to update.
"""

import os

from dotenv import load_dotenv

load_dotenv()

MONDAY_TOKEN = os.environ.get("MONDAY_TOKEN")
if not MONDAY_TOKEN:
    raise RuntimeError("MONDAY_TOKEN missing — check your .env file.")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY missing — check your .env file.")

MONDAY_MCP_URL = "https://mcp.monday.com/mcp"

# --- Board IDs ---
# Set these in your .env. Find each board's ID in its URL:
# https://yourteam.monday.com/boards/1234567890 -> 1234567890
WORK_ORDERS_BOARD_ID = int(os.environ["WORK_ORDERS_BOARD_ID"])
DEALS_BOARD_ID = int(os.environ["DEALS_BOARD_ID"])

# --- Known column IDs (from get_board_info / get_deals_columns.py) ---

WORK_ORDERS_COLUMNS = {
    "serial_number": "dropdown_mm6jc5k",       # Serial # — the real unique row identifier
    "customer_code": "dropdown_mm6jwqbt",      # Customer Name Code
    "nature_of_work": "color_mm6jba84",
    "execution_status": "color_mm6jm6w9",
    "sector": "color_mm6jx8n6",
    "type_of_work": "color_mm6jsj3",
    "document_type": "color_mm6j3vqa",
    "probable_start_date": "date_mm6jcfk9",
    "probable_end_date": "date_mm6jsh8r",
    "amount_receivable": "numeric_mm6jdg22",
    "invoice_status": "color_mm6jthje",
    "wo_status": "color_mm6jfggj",
    "billing_status": "color_mm6jtbh8",
}

DEALS_COLUMNS = {
    "owner_code": "text_mm6jzy04",          # Owner code
    "client_code": "dropdown_mm6jw97g",     # Client Code — join key back to Work Orders' customer_code
    "deal_status": "color_mm6jxewd",        # Deal Status
    "close_date": "date_mm6jc60v",          # Close Date (A)
    "closure_probability": "color_mm6jmzeb",# Closure Probability
    "deal_value": "numeric_mm6jwrwp",       # Masked Deal value
    "tentative_close_date": "date_mm6jycx5",# Tentative Close Date
    "deal_stage": "dropdown_mm6j1j4v",      # Deal Stage
    "product_deal": "color_mm6jmhbc",       # Product deal
    "sector": "dropdown_mm6jdbsb",          # Sector/service
    "created_date": "date_mm6jee9s",        # Created Date
}

# Known data-quality caveats — surfaced to the LLM via the system prompt so
# it can warn users rather than silently mis-answering. Keep this list updated
# as you discover more during testing.
KNOWN_DATA_ISSUES = [
    "Type of Work column can hold combined values as a single label "
    "(e.g. 'Hydrology, Topography Survey: RGB' is one label, not two) — "
    "filtering for a single work type may miss combined-label rows.",
    "Quantities as per PO mixes units freely in one field (hectares, acres, "
    "km, months, 'NA', etc.) — treat as unstructured text, not a clean number.",
    "Collection Date is stored as free text, not a real date column — date "
    "comparisons/filters on it are unreliable.",
    "Deals' 'Masked Deal value' is anonymized/scaled, not real currency — "
    "treat as relative/comparative only, never report as an actual amount.",
]