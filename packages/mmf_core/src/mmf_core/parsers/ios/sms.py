"""iOS iMessage & SMS Parser for sms.db."""
import sqlite3
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime, timezone
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

APPLE_EPOCH_OFFSET = 978307200  # Seconds between 1970-01-01 and 2001-01-01

def cocoa_to_iso(val: Any) -> str:
    """Convert iOS Cocoa timestamp (nanoseconds or seconds since 2001-01-01) to ISO-8601 UTC."""
    if not val:
        return datetime.now(timezone.utc).isoformat()
    try:
        raw_val = float(val)
        if raw_val > 100000000000:  # Nanoseconds (iOS 11+)
            unix_sec = (raw_val / 1e9) + APPLE_EPOCH_OFFSET
        else:  # Seconds
            unix_sec = raw_val + APPLE_EPOCH_OFFSET
        return datetime.fromtimestamp(unix_sec, tz=timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()

class IosSmsParser(BaseParser):
    parser_id = "ios_sms"
    name = "iOS iMessage & SMS Parser"
    version = "1.0.0"
    platform = "ios"
    target_files = ["sms.db"]

    def can_parse(self, file_path: Path) -> bool:
        if file_path.name.lower() in self.target_files or "sms.db" in file_path.name.lower():
            try:
                with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message'")
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

            # Map handles (senders/recipients)
            handle_map: Dict[int, str] = {}
            try:
                cur.execute("SELECT ROWID, id, service FROM handle")
                for h in cur.fetchall():
                    handle_map[h["ROWID"]] = h["id"] or f"Handle_{h['ROWID']}"
            except Exception:
                pass

            # Check message columns
            cur.execute("PRAGMA table_info(message)")
            cols = {c["name"] for c in cur.fetchall()}

            text_col = "text" if "text" in cols else "body"
            date_col = "date" if "date" in cols else "date_delivered"
            from_me_col = "is_from_me" if "is_from_me" in cols else "0"
            service_col = "service" if "service" in cols else "'iMessage'"
            handle_col = "handle_id" if "handle_id" in cols else "0"

            query = f"SELECT ROWID, guid, {text_col} as msg_text, {handle_col} as h_id, {date_col} as msg_date, {from_me_col} as is_outgoing, {service_col} as service_type FROM message"
            try:
                cur.execute(query)
                rows = cur.fetchall()
            except Exception:
                return artifacts, timeline

            for r in rows:
                art_id = str(uuid.uuid4())
                raw_date = r["msg_date"]
                iso_ts = cocoa_to_iso(raw_date)

                h_id = r["h_id"] or 0
                address = handle_map.get(h_id, f"Handle_{h_id}")
                is_out = bool(r["is_outgoing"])
                direction = "outgoing" if is_out else "incoming"
                body = r["msg_text"] or ""
                service = r["service_type"] or "iMessage"

                raw = {
                    "rowid": r["ROWID"],
                    "guid": r["guid"],
                    "handle_id": h_id,
                    "date_cocoa": raw_date,
                    "is_from_me": is_out,
                    "service": service,
                    "body": body
                }
                normalized = {
                    "service": service,
                    "direction": direction,
                    "sender_or_recipient": address,
                    "message_body": body,
                    "timestamp": iso_ts
                }

                art = Artifact(
                    id=art_id,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    platform=self.platform,
                    category="messages",
                    subcategory="imessage" if "imessage" in service.lower() else "sms",
                    raw_data=raw,
                    normalized_data=normalized,
                    timestamp_utc=iso_ts,
                    original_timestamp=str(raw_date) if raw_date else None,
                    source_file=file_path.name,
                    source_table="message",
                    source_row_id=str(r["ROWID"]),
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
                    event_type="message",
                    title=f"{service} ({direction.upper()}): {address}",
                    description=body if len(body) <= 80 else body[:77] + "...",
                    source_file=file_path.name,
                    details=normalized
                ))

        return artifacts, timeline
