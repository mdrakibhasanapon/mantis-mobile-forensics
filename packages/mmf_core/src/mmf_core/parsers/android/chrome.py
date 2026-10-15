"""Chrome and Android Browser History Parser for History SQLite DB."""
import sqlite3
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime, timezone, timedelta
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

CHROME_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)

class ChromeHistoryParser(BaseParser):
    parser_id = "chrome_history"
    name = "Chrome / WebKit Browser History Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["history", "history.db", "browser.db"]

    def can_parse(self, file_path: Path) -> bool:
        if file_path.name.lower() in self.target_files:
            try:
                with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='urls'")
                    return cur.fetchone() is not None
            except Exception:
                return False
        return False

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts = []
        timeline = []

        with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            try:
                cur.execute("SELECT id, url, title, visit_count, last_visit_time FROM urls")
                rows = cur.fetchall()
            except sqlite3.OperationalError:
                return artifacts, timeline

            for r in rows:
                art_id = str(uuid.uuid4())
                chrome_micro = r["last_visit_time"] or 0
                
                # Convert Chrome microseconds since 1601 to UTC ISO string
                try:
                    dt = CHROME_EPOCH + timedelta(microseconds=chrome_micro)
                    iso_ts = dt.isoformat()
                except Exception:
                    iso_ts = datetime.now(timezone.utc).isoformat()

                url = r["url"] or ""
                title = r["title"] or url
                visits = r["visit_count"] or 1

                raw = dict(r)
                normalized = {
                    "url": url,
                    "page_title": title,
                    "visit_count": visits,
                    "last_visit_time": iso_ts
                }

                art = Artifact(
                    id=art_id,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    platform=self.platform,
                    category="browser",
                    subcategory="history",
                    raw_data=raw,
                    normalized_data=normalized,
                    timestamp_utc=iso_ts,
                    original_timestamp=str(chrome_micro),
                    source_file=file_path.name,
                    source_table="urls",
                    source_row_id=str(r["id"]),
                    parser_id=self.parser_id,
                    parser_version=self.version,
                    confidence=1.0,
                    recovery_status=RecoveryStatus.INTACT
                )
                artifacts.append(art)

                # Timeline event
                ev_id = str(uuid.uuid4())
                event = TimelineEvent(
                    id=ev_id,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    timestamp_utc=iso_ts,
                    event_type="web_visit",
                    title=f"Web Visit: {title}",
                    description=url if len(url) <= 90 else url[:87] + "...",
                    source_file=file_path.name,
                    raw_timestamp=str(chrome_micro),
                    details={
                        "url": url,
                        "title": title,
                        "visit_count": visits,
                        "artifact_id": art_id
                    }
                )
                timeline.append(event)

        return artifacts, timeline
