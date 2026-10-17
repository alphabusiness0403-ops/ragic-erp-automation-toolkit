"""Ragic ERP Batch Synchronization Module.

Provides a fault-tolerant HTTP client for fetching unsynchronized dispatch
work orders from Ragic ERP, transforming records into standardized calendar
payloads, and updating synchronization states with exponential backoff retry.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import logging
from pathlib import Path
import time
from typing import Any, Dict, Optional
import requests

try:
    import config as cfg  # type: ignore[import-not-found]
except ImportError:
    _spec = importlib.util.spec_from_file_location(
        "config", Path(__file__).with_name("config.example.py")
    )
    if _spec is None or _spec.loader is None:
        raise RuntimeError("Unable to load configuration from config.py or config.example.py")
    cfg = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(cfg)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ragic_sync")


class RagicSyncError(Exception):
    """Custom exception raised when Ragic ERP synchronization fails."""


@dataclass(frozen=True)
class DispatchEventPayload:
    """Normalized dispatch event payload ready for calendar ingestion."""

    record_id: str
    work_order_id: str
    summary: str
    location: str
    start_iso: str
    end_iso: str
    assigned_team: str
    raw_status: str


class RagicClient:
    """Fault-tolerant REST client for Ragic ERP sheet operations."""

    def __init__(self) -> None:
        self.endpoint = (
            f"{cfg.RAGIC_BASE_URL.rstrip('/')}/"
            f"{cfg.RAGIC_ACCOUNT_NAME}/"
            f"{cfg.RAGIC_TAB_FOLDER}/"
            f"{cfg.RAGIC_SHEET_INDEX}"
        )
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Basic {cfg.RAGIC_API_KEY}",
            "Accept": "application/json",
        })

    def _request_with_retry(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Executes an HTTP request with exponential backoff for 429/5xx errors."""
        for attempt in range(1, cfg.RAGIC_MAX_RETRIES + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_payload,
                    timeout=cfg.RAGIC_REQUEST_TIMEOUT_SEC,
                )
                if response.status_code == 429 or response.status_code >= 500:
                    retry_after = response.headers.get("Retry-After")
                    sleep_sec = (
                        float(retry_after)
                        if retry_after and retry_after.isdigit()
                        else cfg.RAGIC_BACKOFF_FACTOR ** attempt
                    )
                    logger.warning(
                        "HTTP %s received (attempt %d/%d). Retrying in %.1fs...",
                        response.status_code,
                        attempt,
                        cfg.RAGIC_MAX_RETRIES,
                        sleep_sec,
                    )
                    time.sleep(sleep_sec)
                    continue

                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                if attempt == cfg.RAGIC_MAX_RETRIES:
                    raise RagicSyncError(f"Exhausted retries for {url}: {exc}") from exc
                sleep_sec = cfg.RAGIC_BACKOFF_FACTOR ** attempt
                logger.warning("Network error (%s). Retrying in %.1fs...", exc, sleep_sec)
                time.sleep(sleep_sec)

        raise RagicSyncError("Unreachable retry state")

    def fetch_unsynced_records(self) -> Dict[str, Any]:
        """Fetches batch records from Ragic sheet with pagination limit."""
        params = {
            "api": "",
            "limit": cfg.RAGIC_BATCH_SIZE,
            "naming": "EID",
        }
        return self._request_with_retry("GET", self.endpoint, params=params)

    def mark_record_synced(self, record_id: str) -> None:
        """Marks a specific Ragic record as synced with current UTC timestamp."""
        now_utc = datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M:%S")
        payload = {
            cfg.RAGIC_FIELD_MAPPING["sync_flag"]: "Synced",
            cfg.RAGIC_FIELD_MAPPING["last_synced_at"]: now_utc,
        }
        url = f"{self.endpoint}/{record_id}"
        self._request_with_retry("POST", url, params={"api": ""}, json_payload=payload)


def transform_record(record_id: str, row: Dict[str, Any]) -> Optional[DispatchEventPayload]:
    """Validates and converts a raw Ragic row dict into a DispatchEventPayload."""
    fmap = cfg.RAGIC_FIELD_MAPPING
    if row.get(fmap["sync_flag"]) == "Synced":
        return None

    work_order = str(row.get(fmap["work_order_id"], "")).strip()
    title = str(row.get(fmap["project_title"], "")).strip()
    start_str = str(row.get(fmap["scheduled_start"], "")).strip()
    end_str = str(row.get(fmap["scheduled_end"], "")).strip()

    if not (work_order and title and start_str and end_str):
        logger.debug("Skipping incomplete record ID %s", record_id)
        return None

    raw_status = str(row.get(fmap["dispatch_status"], "Pending")).strip()
    prefix = cfg.STATUS_PREFIX_MAP.get(raw_status, "[PENDING]")
    summary = f"{prefix} {work_order} - {title}"

    return DispatchEventPayload(
        record_id=record_id,
        work_order_id=work_order,
        summary=summary,
        location=str(row.get(fmap["client_site"], "")).strip(),
        start_iso=start_str,
        end_iso=end_str,
        assigned_team=str(row.get(fmap["assigned_team"], "Unassigned")).strip(),
        raw_status=raw_status,
    )


def run_sync(dry_run: bool = False) -> int:
    """Executes the synchronization pipeline and returns processed count."""
    client = RagicClient()
    raw_data = client.fetch_unsynced_records()
    processed_count = 0

    for record_id, row in raw_data.items():
        if not isinstance(row, dict):
            continue
        payload = transform_record(record_id, row)
        if payload is None:
            continue

        logger.info("Prepared dispatch payload: %s (%s)", payload.summary, payload.assigned_team)
        if not dry_run:
            client.mark_record_synced(payload.record_id)
        processed_count += 1

    logger.info("Batch sync completed. Total records processed: %d (dry_run=%s)", processed_count, dry_run)
    return processed_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize Ragic ERP dispatch records.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and transform records without writing state back to Ragic.",
    )
    args = parser.parse_args()
    run_sync(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
