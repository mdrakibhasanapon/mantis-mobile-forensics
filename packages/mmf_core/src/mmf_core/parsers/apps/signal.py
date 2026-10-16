"""Signal Messenger Database Parser for signal.db."""
import sqlite3
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime, timezone
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class SignalParser(BaseParser):
    parser_id = "signal_messages"
    name = "Signal Private Messenger Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["signal.db", "signal_backup.db"]

    def can_parse(self, file_path: Path) -> bool:
        if file_path.name.lower() in self.target_files or "signal" in file_path.name.lower():
            try:
                with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('sms', 'mms', 'message', 'recipient')")
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

            # Map recipients if available
            recipients_map: Dict[Any, str] = {}
            try:
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='recipient'")
                if cur.fetchone():
                    cur.execute("SELECT _id, phone, system_display_name, profile_joined_name FROM recipient")
                    for r in cur.fetchall():
                        name = r["system_display_name"] or r["profile_joined_name"] or r["phone"] or f"Recipient_{r['_id']}"
                        recipients_map[r["_id"]] = name
            except Exception:
                pass

            # Detect message table (sms, message, or mms)
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('message', 'sms')")
            row = cur.fetchone()
            if not row:
                return artifacts, timeline
            tbl_name = row["name"]

            cur.execute(f"PRAGMA table_info({tbl_name})")
            cols = {c["name"] for c in cur.fetchall()}

            id_col = "_id" if "_id" in cols else "id"
            date_col = "date_sent" if "date_sent" in cols else "date" if "date" in cols else "timestamp"
            body_col = "body" if "body" in cols else "text"
            address_col = "address" if "address" in cols else "recipient_id" if "recipient_id" in cols else "thread_id"

            query = f"SELECT {id_col} as msg_id, {date_col} as msg_date, {address_col} as recipient, {body_col} as msg_body FROM {tbl_name}"
            try:
                cur.execute(query)
                rows = cur.fetchall()
            except Exception:
                return artifacts, timeline

            for r in rows:
                art_id = str(uuid.uuid4())
                epoch_ms = r["msg_date"] or 0
                try:
                    dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
                    iso_ts = dt.isoformat()
                except Exception:
                    iso_ts = datetime.now(timezone.utc).isoformat()

                rec_val = r["recipient"]
                sender = recipients_map.get(rec_val, str(rec_val or "Unknown"))
                body = str(r["msg_body"] or "")

                raw = {
                    "id": r["msg_id"],
                    "recipient_id": rec_val,
                    "date": epoch_ms,
                    "body": body
                }
                normalized = {
                    "app": "Signal",
                    "contact_or_recipient": sender,
                    "message_body": body,
                    "timestamp": iso_ts
                }

                art = Artifact(
                    id=art_id,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    platform=self.platform,
                    category="messages",
                    subcategory="signal",
                    raw_data=raw,
                    normalized_data=normalized,
                    timestamp_utc=iso_ts,
                    original_timestamp=str(epoch_ms),
                    source_file=file_path.name,
                    source_table=tbl_name,
                    source_row_id=str(r["msg_id"]),
                    parser_id=self.parser_id,
                    parser_version=self.version,
                    confidence=1.0,
                    recovery_status=RecoveryStatus.INTACT
                )
                artifacts.append(art)

                event = TimelineEvent(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    evidence_id=evidence_id,
                    timestamp_utc=iso_ts,
                    event_type="message",
                    title=f"Signal Message: {sender}",
                    description=body if len(body) <= 80 else body[:77] + "...",
                    source_file=file_path.name,
                    raw_timestamp=str(epoch_ms),
                    details={
                        "app": "Signal",
                        "sender": sender,
                        "artifact_id": art_id
                    }
                )
                timeline.append(event)

        return artifacts, timeline
