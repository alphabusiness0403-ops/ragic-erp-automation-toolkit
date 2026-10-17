# ragic-erp-automation-toolkit

Lightweight, fault-tolerant automation toolkit for synchronizing field service work orders between Ragic ERP and Google Calendar. Built for operations and engineering teams that rely on Ragic as a flexible back-office ERP and Google Workspace as a real-time field dispatch layer.

## Problem Statement & Pain Points Solved

Small and mid-sized engineering and field-service organizations frequently store structured project records in Ragic ERP while coordinating on-site technicians through shared Google Calendars. Bridging these two platforms manually introduces three operational bottlenecks:

1. **Manual Double-Entry & Sync Drift**: Dispatchers spend hours copying work order numbers, site addresses, and time windows from Ragic sheets into Google Calendar, leading to transcription errors and stale schedules when work orders change.
2. **API Rate-Limiting & Transient Network Failures**: Bulk polling or updating hundreds of Ragic records without exponential backoff frequently triggers `HTTP 429 Too Many Requests` or transient timeout drops, leaving records in an inconsistent half-synced state.
3. **Visual Clutter in Shared Dispatch Calendars**: Standard calendar feeds display all synced events in a single default color, making it difficult for field supervisors to distinguish urgent callouts, routine inspections, preventative maintenance, and completed jobs at a glance.

`ragic-erp-automation-toolkit` solves these problems by combining a strongly typed, retry-aware Python synchronization client (`ragic_sync.py`) with an automated Google Apps Script color classifier (`calendar_batch_dispatch.gs`).

## Key Features

- **Resilient Ragic REST API Client**: Implements exponential backoff and `Retry-After` header inspection for HTTP 429 and 5xx responses.
- **Strict Data Validation & Type Safety**: Uses Python `dataclass` payloads and full PEP 484 type annotations to reject incomplete ERP records before calendar ingestion.
- **Idempotent State Write-Back**: Marks processed Ragic records as `Synced` with a UTC timestamp to prevent duplicate dispatch entries.
- **Automated Visual Triage**: Scans Google Calendar windows via Google Apps Script and applies standardized `CalendarApp.EventColor` taxonomy based on status tags.

## Repository Structure

| File | Purpose |
| :--- | :--- |
| `config.example.py` | Sanitized configuration template for Ragic API endpoints, field ID mappings, and Google Calendar targets |
| `ragic_sync.py` | Python batch synchronization script with retry logic, payload transformation, and CLI dry-run mode |
| `calendar_batch_dispatch.gs` | Google Apps Script for batch filtering dispatch events and applying status-based color coding |
| `README.md` | Project documentation, setup guide, and MIT license terms |

## Installation & Setup

### 1. Clone the Repository and Install Dependencies

```bash
git clone [https://github.com/alphabusiness0403-ops/ragic-erp-automation-toolkit.git](https://github.com/alphabusiness0403-ops/ragic-erp-automation-toolkit.git)
cd ragic-erp-automation-toolkit
python3 -m venv .venv
source .venv/bin/activate
pip install requests
```

### 2. Configure Environment Parameters

```bash
cp config.example.py config.py
```

### 3. Execute the Ragic Batch Sync Script

Validate your configuration and inspect transformed records without modifying Ragic state using `--dry-run`:

```bash
python3 ragic_sync.py --dry-run
```

Run the live synchronization job via cron or CI scheduler:

```bash
python3 ragic_sync.py
```

### 4. Deploy the Google Apps Script Classifier

1. Open Google Apps Script and create a new standalone script project.
2. Copy the contents of `calendar_batch_dispatch.gs` into `Code.gs`.
3. Update `DISPATCH_CONFIG.CALENDAR_ID` with your shared dispatch calendar address.
4. Configure a time-driven trigger to execute `batchClassifyDispatchEvents` every 15 or 30 minutes.

## Event Color Classification Matrix

| Status Prefix | Operational Meaning | Google Calendar Color Enum |
| :--- | :--- | :--- |
| `[URGENT]` | Emergency callout or SLA-critical repair | `CalendarApp.EventColor.RED` |
| `[INSPECTION]` | Scheduled regulatory or quality inspection | `CalendarApp.EventColor.YELLOW` |
| `[MAINTENANCE]` | Routine preventative maintenance visit | `CalendarApp.EventColor.BLUE` |
| `[PENDING]` | Tentative dispatch awaiting technician confirmation | `CalendarApp.EventColor.GRAY` |
| `[COMPLETED]` | Work order verified and closed on site | `CalendarApp.EventColor.GREEN` |

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
