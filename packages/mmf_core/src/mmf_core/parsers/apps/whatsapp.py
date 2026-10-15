"""WhatsApp Messenger Parser for msgstore.db."""
import sqlite3
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime, timezone
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class WhatsAppParser(BaseParser):
    parser_id = "whatsapp_msgstore"
    name = "WhatsApp Message Store Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["msgstore.db"]

    def can_parse(self, file_path: Path) -> bool:
        if file_path.name.lower() in self.target_files:
            try:
                with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
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
                cur.execute("SELECT _id, key_remote_jid, key_from_me, key_id, status, data, timestamp FROM messages WHERE data IS NOT NULL")
                rows = cur.fetchall()
            except sqlite3.OperationalError:
                return artifacts, timeline

            for r in rows:
                art_id = str(uuid.uuid4())
                epoch_ms = r["timestamp"] or 0
                try:
                    dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
                    iso_ts = dt.isoformat()
                except Exception:
                    iso_ts = datetime.now(timezone.utc).isoformat()

                from_me = bool(r["key_from_me"])
                direction = "outgoing" if from_me else "incoming"
                remote_jid = r["key_remote_jid"] or "unknown@s.whatsapp.net"
                participant = remote_jid.split("@")[0]
                text = r["data"] or ""

                raw = dict(r)
                normalized = {
                    "application": "WhatsApp",
                    "participant_jid": remote_jid,
                    "sender_or_recipient": participant,
                    "direction": direction,
                    "message_text": text,
                    "key_id": r["key_id"] or "",
                    "timestamp": iso_ts
                }

                art = Artifact(
                    id=art_id,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    platform=self.platform,
                    category="messages",
                    subcategory="whatsapp",
                    raw_data=raw,
                    normalized_data=normalized,
                    timestamp_utc=iso_ts,
                    original_timestamp=str(epoch_ms),
                    source_file=file_path.name,
                    source_table="messages",
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
                    title=f"WhatsApp ({direction.upper()}): {participant}",
                    description=text if len(text) <= 80 else text[:77] + "...",
                    source_file=file_path.name,
                    raw_timestamp=str(epoch_ms),
                    details={
                        "application": "WhatsApp",
                        "remote_jid": remote_jid,
                        "direction": direction,
                        "full_text": text,
                        "artifact_id": art_id
                    }
                )
                timeline.append(event)

        return artifacts, timeline
