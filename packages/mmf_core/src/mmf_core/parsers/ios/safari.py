"""iOS Safari Browser History Parser for History.db."""
import sqlite3
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime, timezone
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus
from .sms import cocoa_to_iso

class IosSafariParser(BaseParser):
    parser_id = "ios_safari"
    name = "iOS Safari Browser History Parser"
    version = "1.0.0"
    platform = "ios"
    target_files = ["history.db"]

    def can_parse(self, file_path: Path) -> bool:
        if file_path.name.lower() in self.target_files or "safari" in str(file_path).lower():
            try:
                with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('history_visits', 'history_items')")
                    return cur.fetchone() is not None
            except Exception:
                return False
        return False

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts: List[Artifact] = []
        timeline: List[TimelineEvent] = []

        with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            query = """
            SELECT 
                hv.id as visit_id,
                hi.url as page_url,
                hv.title as page_title,
                hv.visit_time as visit_time_cocoa,
                hi.visit_count as visit_count
            FROM history_visits hv
            JOIN history_items hi ON hv.history_item = hi.id
            """
            try:
                cur.execute(query)
                rows = cur.fetchall()
            except Exception:
                return artifacts, timeline

            for r in rows:
                art_id = str(uuid.uuid4())
                raw_date = r["visit_time_cocoa"]
                iso_ts = cocoa_to_iso(raw_date)

                url = str(r["page_url"] or "")
                title = str(r["page_title"] or url)
                visit_count = int(r["visit_count"] or 1)

                raw = {
                    "visit_id": r["visit_id"],
                    "url": url,
                    "title": title,
                    "visit_time_cocoa": raw_date,
                    "visit_count": visit_count
                }
                normalized = {
                    "browser": "Safari",
                    "url": url,
                    "title": title,
                    "visit_count": visit_count,
                    "timestamp": iso_ts
                }

                art = Artifact(
                    id=art_id,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    platform=self.platform,
                    category="browser",
                    subcategory="safari",
                    raw_data=raw,
                    normalized_data=normalized,
                    timestamp_utc=iso_ts,
                    original_timestamp=str(raw_date) if raw_date else None,
                    source_file=file_path.name,
                    source_table="history_visits",
                    source_row_id=str(r["visit_id"]),
                    parser_id=self.parser_id,
                    parser_version=self.version,
                    confidence=1.0,
                    recovery_status=RecoveryStatus.INTACT
                )
                artifacts.append(art)

                timeline.append(TimelineEvent(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    evidence_id=evidence_id,
                    timestamp_utc=iso_ts,
                    event_type="web_visit",
                    title=f"Safari: {title[:50]}",
                    description=url if len(url) <= 100 else url[:97] + "...",
                    source_file=file_path.name,
                    details=normalized
                ))

        return artifacts, timeline
