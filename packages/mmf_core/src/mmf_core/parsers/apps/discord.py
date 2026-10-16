"""Discord Mobile database forensic parser."""
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Tuple
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class DiscordParser(BaseParser):
    """Parses Discord mobile SQLite databases (messages.db, discord.db)."""
    parser_id = "app_discord"
    name = "Discord Mobile Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["messages.db", "discord.db", "channels.db"]

    def can_parse(self, file_path: Path) -> bool:
        name = file_path.name.lower()
        parent = str(file_path.parent).lower()
        return ("discord" in name or "discord" in parent) and file_path.suffix.lower() in [".db", ".sqlite"]

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts: List[Artifact] = []
        timeline_events: List[TimelineEvent] = []

        try:
            conn = sqlite3.connect(f"file:{file_path.resolve()}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row["name"] for row in cursor.fetchall()]

            if "messages" in tables:
                cursor.execute("PRAGMA table_info(messages)")
                cols = {c["name"] for c in cursor.fetchall()}

                author_col = "author_username" if "author_username" in cols else ("author" if "author" in cols else "user_id")
                content_col = "content" if "content" in cols else "text"
                ts_col = "timestamp" if "timestamp" in cols else "created_at"

                query = f"SELECT id, channel_id, {content_col} as body"
                if author_col in cols:
                    query += f", {author_col} as author_name"
                if ts_col in cols:
                    query += f", {ts_col} as msg_time"
                query += " FROM messages ORDER BY id ASC"

                cursor.execute(query)
                for row in cursor.fetchall():
                    msg_id = str(row["id"] or uuid.uuid4())
                    content = row["body"] or ""
                    author = str(row["author_name"]) if "author_name" in row.keys() else "Unknown"
                    raw_ts = row["msg_time"] if "msg_time" in row.keys() else None

                    dt_str = None
                    if raw_ts:
                        if isinstance(raw_ts, (int, float)) and raw_ts > 0:
                            ts_sec = raw_ts / 1000.0 if raw_ts > 10000000000 else raw_ts
                            try:
                                dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
                                dt_str = dt.isoformat()
                            except Exception:
                                pass
                        elif isinstance(raw_ts, str) and ("T" in raw_ts or "-" in raw_ts):
                            dt_str = raw_ts

                    normalized = {
                        "message_id": msg_id,
                        "channel_id": str(row["channel_id"] or ""),
                        "author": author,
                        "sender_or_recipient": author,
                        "content": content,
                        "timestamp_utc": dt_str,
                        "app": "Discord"
                    }

                    artifacts.append(Artifact(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        evidence_id=evidence_id,
                        platform="android",
                        category="messages",
                        subcategory="discord",
                        raw_data=dict(row),
                        normalized_data=normalized,
                        timestamp_utc=dt_str,
                        original_timestamp=str(raw_ts),
                        source_file=file_path.name,
                        source_table="messages",
                        source_row_id=msg_id,
                        parser_id=self.parser_id,
                        confidence=1.0,
                        recovery_status=RecoveryStatus.INTACT,
                        notes=f"Discord message: {content[:60]}"
                    ))

                    if dt_str:
                        timeline_events.append(TimelineEvent(
                            id=str(uuid.uuid4()),
                            case_id=case_id,
                            evidence_id=evidence_id,
                            timestamp_utc=dt_str,
                            event_type="message",
                            title=f"Discord: {author[:20]}",
                            description=f"{content[:100]}",
                            source_file=file_path.name,
                            raw_timestamp=str(raw_ts),
                            details={"author": author, "channel": row["channel_id"], "app": "discord"}
                        ))

            conn.close()
        except Exception:
            pass

        return artifacts, timeline_events
