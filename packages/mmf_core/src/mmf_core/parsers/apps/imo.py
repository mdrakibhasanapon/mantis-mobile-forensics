"""IMO Messenger mobile forensic parser."""
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Tuple
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class ImoParser(BaseParser):
    """Parses IMO Messenger SQLite databases (imofriends.db, messages.db, account.db)."""
    parser_id = "app_imo"
    name = "IMO Messenger Mobile Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["imofriends.db", "messages.db", "account.db", "imo.db"]

    def can_parse(self, file_path: Path) -> bool:
        name = file_path.name.lower()
        return "imo" in name or name in ["imofriends.db", "account.db"]

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts: List[Artifact] = []
        timeline_events: List[TimelineEvent] = []

        try:
            conn = sqlite3.connect(f"file:{file_path.resolve()}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row["name"] for row in cursor.fetchall()]

            # 1. Contacts/Friends table
            if "friends" in tables:
                cursor.execute("SELECT buid, alias, name, phone FROM friends")
                for row in cursor.fetchall():
                    phone = row["phone"] or ""
                    name = row["name"] or row["alias"] or "IMO Contact"
                    artifacts.append(Artifact(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        evidence_id=evidence_id,
                        platform="android",
                        category="contacts",
                        subcategory="imo_contact",
                        raw_data=dict(row),
                        normalized_data={
                            "display_name": name,
                            "phone_number": phone,
                            "sender_or_recipient": phone or name,
                            "buid": row["buid"],
                            "app": "IMO"
                        },
                        source_file=file_path.name,
                        source_table="friends",
                        source_row_id=str(row["buid"]),
                        parser_id=self.parser_id,
                        confidence=1.0,
                        recovery_status=RecoveryStatus.INTACT,
                        notes=f"IMO contact: {name} ({phone})"
                    ))

            # 2. Chat messages table
            msg_table = None
            for candidate in ["chat_messages", "messages", "im_messages"]:
                if candidate in tables:
                    msg_table = candidate
                    break

            if msg_table:
                cursor.execute(f"PRAGMA table_info({msg_table})")
                cols = [c["name"] for c in cursor.fetchall()]

                ts_col = "timestamp" if "timestamp" in cols else ("time" if "time" in cols else "created_time")
                text_col = "message" if "message" in cols else ("text" if "text" in cols else "body")
                sender_col = "buid" if "buid" in cols else ("sender" if "sender" in cols else "author")

                if text_col in cols:
                    query = f"SELECT rowid, {text_col} as msg_text, {sender_col if sender_col in cols else 'NULL'} as sender_val"
                    if ts_col in cols:
                        query += f", {ts_col} as msg_ts"
                    query += f" FROM {msg_table}"

                    cursor.execute(query)
                    for row in cursor.fetchall():
                        text = row["msg_text"] or ""
                        sender = str(row["sender_val"] or "Unknown")
                        ts_val = row["msg_ts"] if "msg_ts" in row.keys() else None

                        dt_str = None
                        if ts_val and isinstance(ts_val, (int, float)) and ts_val > 0:
                            # Might be seconds or milliseconds
                            ts_sec = ts_val / 1000.0 if ts_val > 10000000000 else ts_val
                            try:
                                dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
                                dt_str = dt.isoformat()
                            except Exception:
                                pass

                        art = Artifact(
                            id=str(uuid.uuid4()),
                            case_id=case_id,
                            evidence_id=evidence_id,
                            platform="android",
                            category="messages",
                            subcategory="imo",
                            raw_data=dict(row),
                            normalized_data={
                                "text": text,
                                "sender": sender,
                                "sender_or_recipient": sender,
                                "timestamp_utc": dt_str,
                                "app": "IMO"
                            },
                            timestamp_utc=dt_str,
                            original_timestamp=str(ts_val),
                            source_file=file_path.name,
                            source_table=msg_table,
                            source_row_id=str(row["rowid"]),
                            parser_id=self.parser_id,
                            confidence=1.0,
                            recovery_status=RecoveryStatus.INTACT,
                            notes=f"IMO message: {text[:60]}"
                        )
                        artifacts.append(art)

                        if dt_str:
                            timeline_events.append(TimelineEvent(
                                id=str(uuid.uuid4()),
                                case_id=case_id,
                                evidence_id=evidence_id,
                                timestamp_utc=dt_str,
                                event_type="message",
                                title=f"IMO Message: {sender[:20]}",
                                description=f"{text[:100]}",
                                source_file=file_path.name,
                                raw_timestamp=str(ts_val),
                                details={"sender": sender, "app": "imo"}
                            ))

            conn.close()
        except Exception:
            pass

        return artifacts, timeline_events
