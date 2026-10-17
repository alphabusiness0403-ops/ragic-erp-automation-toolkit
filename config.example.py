"""Configuration template for Ragic ERP Automation Toolkit.

Copy this file to `config.py` and replace the placeholder values with your
actual Ragic ERP credentials and Google Workspace calendar settings.
Never commit `config.py` or real credentials to version control.
"""

from typing import Dict

# ---------------------------------------------------------------------------
# Ragic ERP API Configuration
# ---------------------------------------------------------------------------
RAGIC_BASE_URL: str = "https://www.ragic.com"
RAGIC_ACCOUNT_NAME: str = "your-organization-account"
RAGIC_TAB_FOLDER: str = "field-operations"
RAGIC_SHEET_INDEX: str = "1"
RAGIC_API_KEY: str = "YOUR_RAGIC_64_CHAR_API_KEY_HERE"

# HTTP Client & Rate Limiting Settings
RAGIC_REQUEST_TIMEOUT_SEC: int = 30
RAGIC_MAX_RETRIES: int = 4
RAGIC_BACKOFF_FACTOR: float = 1.5
RAGIC_BATCH_SIZE: int = 100

# ---------------------------------------------------------------------------
# Ragic Internal Field ID Mapping
# Replace numeric field IDs with the corresponding IDs from your Ragic form.
# ---------------------------------------------------------------------------
RAGIC_FIELD_MAPPING: Dict[str, str] = {
    "work_order_id": "1000101",
    "project_title": "1000102",
    "client_site": "1000103",
    "scheduled_start": "1000104",
    "scheduled_end": "1000105",
    "dispatch_status": "1000106",
    "assigned_team": "1000107",
    "sync_flag": "1000108",
    "last_synced_at": "1000109",
}

# ---------------------------------------------------------------------------
# Google Calendar Integration Settings
# ---------------------------------------------------------------------------
DEFAULT_CALENDAR_ID: str = "dispatch-team@example-company.com"
DEFAULT_TIMEZONE: str = "Asia/Taipei"

STATUS_PREFIX_MAP: Dict[str, str] = {
    "Urgent": "[URGENT]",
    "Inspection": "[INSPECTION]",
    "Maintenance": "[MAINTENANCE]",
    "Pending": "[PENDING]",
    "Completed": "[COMPLETED]",
}
