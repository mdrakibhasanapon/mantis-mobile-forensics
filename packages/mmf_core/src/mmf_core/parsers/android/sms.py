"""Android SMS and MMS Parser for mmssms.db."""
import sqlite3
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime, timezone
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class AndroidSmsParser(BaseParser):
    parser_id = "android_sms"
    name = "Android SMS/MMS Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["mmssms.db"]

    def can_parse(self, file_path: Path) -> bool:
        if file_path.name.lower() in self.target_files:
            try:
                with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sms'")
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
                cur.execute("SELECT _id, address, date, date_sent, read, type, body FROM sms")
                rows = cur.fetchall()
            except sqlite3.OperationalError:
                return artifacts, timeline

            for r in rows:
                art_id = str(uuid.uuid4())
                epoch_ms = r["date"] or 0
                try:
                    dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
                    iso_ts = dt.isoformat()
                except Exception:
                    iso_ts = datetime.now(timezone.utc).isoformat()

                msg_type = r["type"]
                direction = "incoming" if msg_type == 1 else "outgoing" if msg_type == 2 else "other"
                body = r["body"] or ""
                address = r["address"] or "Unknown"

                raw = dict(r)
                normalized = {
                    "sender_or_recipient": address,
                    "direction": direction,
                    "message_body": body,
                    "read_status": bool(r["read"]),
                    "timestamp": iso_ts
                }

                art = Artifact(
                    id=art_id,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    platform=self.platform,
                    category="messages",
                    subcategory="sms",
                    raw_data=raw,
                    normalized_data=normalized,
                    timestamp_utc=iso_ts,
                    original_timestamp=str(epoch_ms),
                    source_file=file_path.name,
                    source_table="sms",
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
                    event_type="message",
                    title=f"SMS ({direction.upper()}): {address}",
                    description=body if len(body) <= 80 else body[:77] + "...",
                    source_file=file_path.name,
                    raw_timestamp=str(epoch_ms),
                    details={
                        "direction": direction,
                        "address": address,
                        "full_body": body,
                        "artifact_id": art_id
                    }
                )
                timeline.append(event)

        return artifacts, timeline
