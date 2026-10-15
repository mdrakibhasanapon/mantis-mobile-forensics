"""Android Call Log Parser for calllog.db."""
import sqlite3
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime, timezone
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class AndroidCallsParser(BaseParser):
    parser_id = "android_calls"
    name = "Android Call Logs Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["calllog.db", "contacts2.db"]

    def can_parse(self, file_path: Path) -> bool:
        if file_path.name.lower() in self.target_files:
            try:
                with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='calls'")
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
                cur.execute("SELECT _id, number, date, duration, type, name FROM calls")
                rows = cur.fetchall()
            except sqlite3.OperationalError:
                return artifacts, timeline

            type_map = {1: "incoming", 2: "outgoing", 3: "missed", 4: "voicemail", 5: "rejected", 6: "blocked"}

            for r in rows:
                art_id = str(uuid.uuid4())
                epoch_ms = r["date"] or 0
                try:
                    dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
                    iso_ts = dt.isoformat()
                except Exception:
                    iso_ts = datetime.now(timezone.utc).isoformat()

                call_type_num = r["type"]
                call_type = type_map.get(call_type_num, "unknown")
                number = r["number"] or "Unknown"
                name = r["name"] or "Unknown"
                duration_sec = r["duration"] or 0

                raw = dict(r)
                normalized = {
                    "phone_number": number,
                    "caller_name": name,
                    "call_type": call_type,
                    "duration_seconds": duration_sec,
                    "timestamp": iso_ts
                }

                art = Artifact(
                    id=art_id,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    platform=self.platform,
                    category="calls",
                    subcategory="call_log",
                    raw_data=raw,
                    normalized_data=normalized,
                    timestamp_utc=iso_ts,
                    original_timestamp=str(epoch_ms),
                    source_file=file_path.name,
                    source_table="calls",
                    source_row_id=str(r["_id"]),
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
                    event_type="call",
                    title=f"Call ({call_type.capitalize()}): {number} ({name})",
                    description=f"Duration: {duration_sec}s | Type: {call_type}",
                    source_file=file_path.name,
                    raw_timestamp=str(epoch_ms),
                    details={
                        "phone_number": number,
                        "caller_name": name,
                        "call_type": call_type,
                        "duration": duration_sec,
                        "artifact_id": art_id
                    }
                )
                timeline.append(event)

        return artifacts, timeline
