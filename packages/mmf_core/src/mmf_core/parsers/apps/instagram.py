"""Instagram Direct message mobile forensic parser."""
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Tuple
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class InstagramDirectParser(BaseParser):
    """Parses Instagram Direct Messages database (direct_v2.db)."""
    parser_id = "app_instagram"
    name = "Instagram Direct Messages Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["direct_v2.db", "direct_v2.db-wal", "instagram.db"]

    def can_parse(self, file_path: Path) -> bool:
        name = file_path.name.lower()
        return "direct_v2" in name or name in ["direct.db", "instagram_direct.db"]

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts: List[Artifact] = []
        timeline_events: List[TimelineEvent] = []

        try:
            conn = sqlite3.connect(f"file:{file_path.resolve()}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('messages', 'threads')")
            tables = [row["name"] for row in cursor.fetchall()]

            if "messages" in tables:
                cursor.execute("""
                    SELECT 
                        message_id, 
                        thread_id, 
                        user_id, 
                        text, 
                        timestamp, 
                        message_type 
                    FROM messages
                    ORDER BY timestamp ASC
                """)
                for row in cursor.fetchall():
                    msg_id = str(row["message_id"] or uuid.uuid4())
                    text = row["text"] or ""
                    user_id = str(row["user_id"] or "Unknown")
                    ts_raw = row["timestamp"]
                    msg_type = row["message_type"] or "text"

                    dt_str = None
                    if ts_raw and isinstance(ts_raw, (int, float)) and ts_raw > 0:
                        # Microseconds or milliseconds
                        ts_sec = ts_raw / 1000000.0 if ts_raw > 10000000000000 else (ts_raw / 1000.0 if ts_raw > 10000000000 else ts_raw)
                        try:
                            dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
                            dt_str = dt.isoformat()
                        except Exception:
                            pass

                    normalized = {
                        "message_id": msg_id,
                        "thread_id": row["thread_id"],
                        "user_id": user_id,
                        "sender_or_recipient": user_id,
                        "text": text,
                        "message_type": msg_type,
                        "timestamp_utc": dt_str,
                        "app": "Instagram"
                    }

                    artifacts.append(Artifact(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        evidence_id=evidence_id,
                        platform="android",
                        category="messages",
                        subcategory="instagram",
                        raw_data=dict(row),
                        normalized_data=normalized,
                        timestamp_utc=dt_str,
                        original_timestamp=str(ts_raw),
                        source_file=file_path.name,
                        source_table="messages",
                        source_row_id=msg_id,
                        parser_id=self.parser_id,
                        confidence=1.0,
                        recovery_status=RecoveryStatus.INTACT,
                        notes=f"Instagram DM ({msg_type}): {text[:50]}"
                    ))

                    if dt_str:
                        timeline_events.append(TimelineEvent(
                            id=str(uuid.uuid4()),
                            case_id=case_id,
                            evidence_id=evidence_id,
                            timestamp_utc=dt_str,
                            event_type="message",
                            title=f"Instagram DM: User {user_id[:15]}",
                            description=f"{text[:100] if text else f'[{msg_type}]'}",
                            source_file=file_path.name,
                            raw_timestamp=str(ts_raw),
                            details={"user_id": user_id, "type": msg_type, "app": "instagram"}
                        ))

            conn.close()
        except Exception:
            pass

        return artifacts, timeline_events
