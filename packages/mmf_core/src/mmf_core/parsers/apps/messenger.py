"""Facebook Messenger mobile database forensic parser."""
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Tuple
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class MessengerParser(BaseParser):
    """Parses Facebook Messenger SQLite database (threads_db2)."""
    parser_id = "app_messenger"
    name = "Facebook Messenger Mobile Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["threads_db2", "threads_db2-wal", "threads_db"]

    def can_parse(self, file_path: Path) -> bool:
        name = file_path.name.lower()
        return "threads_db" in name or name in ["threads_db2", "messenger.db"]

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts: List[Artifact] = []
        timeline_events: List[TimelineEvent] = []

        try:
            conn = sqlite3.connect(f"file:{file_path.resolve()}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Query messages if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('messages', 'threads')")
            tables = [row["name"] for row in cursor.fetchall()]

            if "messages" in tables:
                cursor.execute("""
                    SELECT 
                        msg_id, 
                        thread_key, 
                        text, 
                        sender, 
                        timestamp_ms, 
                        attachments
                    FROM messages
                    ORDER BY timestamp_ms ASC
                """)
                rows = cursor.fetchall()

                for row in rows:
                    msg_id = str(row["msg_id"] or uuid.uuid4())
                    text = row["text"] or ""
                    sender_raw = str(row["sender"] or "Unknown")
                    ts_ms = row["timestamp_ms"]
                    attachments = str(row["attachments"] or "")

                    dt_str = None
                    if ts_ms and isinstance(ts_ms, (int, float)) and ts_ms > 0:
                        try:
                            dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
                            dt_str = dt.isoformat()
                        except Exception:
                            pass

                    normalized = {
                        "message_id": msg_id,
                        "text": text,
                        "sender": sender_raw,
                        "sender_or_recipient": sender_raw,
                        "thread_key": row["thread_key"],
                        "timestamp_ms": ts_ms,
                        "timestamp_utc": dt_str,
                        "has_attachments": bool(attachments and attachments != "[]"),
                        "app": "Facebook Messenger"
                    }

                    art = Artifact(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        evidence_id=evidence_id,
                        platform="android",
                        category="messages",
                        subcategory="messenger",
                        raw_data=dict(row),
                        normalized_data=normalized,
                        timestamp_utc=dt_str,
                        original_timestamp=str(ts_ms),
                        source_file=file_path.name,
                        source_table="messages",
                        source_row_id=msg_id,
                        parser_id=self.parser_id,
                        confidence=1.0,
                        recovery_status=RecoveryStatus.INTACT,
                        notes=f"Messenger text: {text[:60] if text else '[Attachment]'}"
                    )
                    artifacts.append(art)

                    if dt_str:
                        timeline_events.append(TimelineEvent(
                            id=str(uuid.uuid4()),
                            case_id=case_id,
                            evidence_id=evidence_id,
                            timestamp_utc=dt_str,
                            event_type="message",
                            title=f"Messenger: {sender_raw[:25]}",
                            description=f"Message: {text[:100] if text else '[Attachment/Media]'}",
                            source_file=file_path.name,
                            raw_timestamp=str(ts_ms),
                            details={"sender": sender_raw, "thread": row["thread_key"], "app": "messenger"}
                        ))

            conn.close()
        except Exception as e:
            pass

        return artifacts, timeline_events
