"""Telegram Android Messenger Database Parser for cache4.db."""
import sqlite3
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime, timezone
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class TelegramParser(BaseParser):
    parser_id = "telegram_messages"
    name = "Telegram Messenger Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["cache4.db", "tgnet.dat"]

    def can_parse(self, file_path: Path) -> bool:
        if file_path.name.lower() in self.target_files or "telegram" in file_path.name.lower():
            try:
                with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('messages_v2', 'messages', 'users', 'dialogs')")
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

            # 1. Map users/contacts if users table exists
            users_map: Dict[int, str] = {}
            try:
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                if cur.fetchone():
                    cur.execute("SELECT uid, name FROM users")
                    for u in cur.fetchall():
                        users_map[u["uid"]] = u["name"] or f"User_{u['uid']}"
            except Exception:
                pass

            # 2. Identify messages table (messages_v2 or messages)
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('messages_v2', 'messages')")
            row = cur.fetchone()
            if not row:
                return artifacts, timeline
            tbl_name = row["name"]

            # Check columns
            cur.execute(f"PRAGMA table_info({tbl_name})")
            cols = {c["name"] for c in cur.fetchall()}

            mid_col = "mid" if "mid" in cols else "_id" if "_id" in cols else "id"
            date_col = "date" if "date" in cols else "time"
            body_col = "message" if "message" in cols else "data" if "data" in cols else "body"
            uid_col = "uid" if "uid" in cols else "peer_id" if "peer_id" in cols else "from_id"

            query = f"SELECT {mid_col} as msg_id, {date_col} as msg_date, {uid_col} as peer, {body_col} as msg_body FROM {tbl_name}"
            try:
                cur.execute(query)
                rows = cur.fetchall()
            except Exception:
                return artifacts, timeline

            for r in rows:
                art_id = str(uuid.uuid4())
                epoch_sec = r["msg_date"] or 0
                try:
                    if epoch_sec > 10000000000:  # milliseconds
                        dt = datetime.fromtimestamp(epoch_sec / 1000.0, tz=timezone.utc)
                    else:
                        dt = datetime.fromtimestamp(epoch_sec, tz=timezone.utc)
                    iso_ts = dt.isoformat()
                except Exception:
                    iso_ts = datetime.now(timezone.utc).isoformat()

                peer_id = r["peer"] or 0
                sender_name = users_map.get(peer_id, f"Peer_{peer_id}")
                
                body = r["msg_body"]
                if isinstance(body, bytes):
                    try:
                        body_text = body.decode("utf-8", errors="replace").strip("\x00")
                    except Exception:
                        body_text = "[Binary Payload]"
                else:
                    body_text = str(body or "")

                raw = {
                    "mid": r["msg_id"],
                    "peer_id": peer_id,
                    "date": epoch_sec,
                    "body_preview": body_text[:200]
                }
                normalized = {
                    "app": "Telegram",
                    "sender_or_peer": sender_name,
                    "peer_id": peer_id,
                    "message_body": body_text,
                    "timestamp": iso_ts
                }

                art = Artifact(
                    id=art_id,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    platform=self.platform,
                    category="messages",
                    subcategory="telegram",
                    raw_data=raw,
                    normalized_data=normalized,
                    timestamp_utc=iso_ts,
                    original_timestamp=str(epoch_sec),
                    source_file=file_path.name,
                    source_table=tbl_name,
                    source_row_id=str(r["msg_id"]),
                    parser_id=self.parser_id,
                    parser_version=self.version,
                    confidence=1.0,
                    recovery_status=RecoveryStatus.INTACT
                )
                artifacts.append(art)

                # Timeline event
                event = TimelineEvent(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    evidence_id=evidence_id,
                    timestamp_utc=iso_ts,
                    event_type="message",
                    title=f"Telegram Chat: {sender_name}",
                    description=body_text if len(body_text) <= 80 else body_text[:77] + "...",
                    source_file=file_path.name,
                    raw_timestamp=str(epoch_sec),
                    details={
                        "app": "Telegram",
                        "peer_id": peer_id,
                        "sender_name": sender_name,
                        "artifact_id": art_id
                    }
                )
                timeline.append(event)

        return artifacts, timeline
