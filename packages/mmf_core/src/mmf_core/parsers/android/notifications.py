"""Mobile notification and push alert forensic parser (notification_log.db, wpndatabase.db)."""
import sqlite3
import uuid
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Tuple
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

def extract_clean_text_from_payload(payload: str) -> str:
    """Extract human-readable preview text from raw XML or JSON toast payload."""
    if not payload:
        return ""
    # Strip XML tags e.g. <text id="1">Hello</text>
    clean = re.sub(r"<[^>]+>", " ", payload)
    clean = " ".join(clean.split())
    return clean

class AndroidNotificationsParser(BaseParser):
    """Parses system and third-party push notification databases."""
    parser_id = "android_notifications"
    name = "Mobile Notification & Toast History Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["notification_log.db", "wpndatabase.db", "notifications.db", "notification.db"]

    def can_parse(self, file_path: Path) -> bool:
        name = file_path.name.lower()
        return ("notification" in name or "wpn" in name) and file_path.suffix.lower() in [".db", ".sqlite", ""]

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts: List[Artifact] = []
        timeline_events: List[TimelineEvent] = []

        try:
            conn = sqlite3.connect(f"file:{file_path.resolve()}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row["name"] for row in cursor.fetchall()]

            # 1. Format: Android notification_log / notifications table
            target_table = None
            for candidate in ["notifications", "log", "notification_log", "records", "Notification"]:
                if candidate in tables:
                    target_table = candidate
                    break

            if target_table:
                cursor.execute(f"PRAGMA table_info({target_table})")
                cols = {c["name"] for c in cursor.fetchall()}

                # Match columns
                pkg_col = "package_name" if "package_name" in cols else ("pkg" if "pkg" in cols else ("app_id" if "app_id" in cols else "package"))
                title_col = "title" if "title" in cols else ("sender" if "sender" in cols else "header")
                text_col = "text" if "text" in cols else ("message" if "message" in cols else ("body" if "body" in cols else ("Payload" if "Payload" in cols else "content")))
                ts_col = "timestamp" if "timestamp" in cols else ("post_time" if "post_time" in cols else ("ArrivalTime" if "ArrivalTime" in cols else ("time" if "time" in cols else "created_at")))

                query = f"SELECT rowid AS row_id"
                if pkg_col in cols: query += f", {pkg_col} as pkg_name"
                if title_col in cols: query += f", {title_col} as notif_title"
                if text_col in cols: query += f", {text_col} as notif_text"
                if ts_col in cols: query += f", {ts_col} as notif_time"
                query += f" FROM {target_table} ORDER BY rowid ASC"

                cursor.execute(query)
                for row in cursor.fetchall():
                    row_dict = dict(row)
                    row_id = str(row_dict.get("row_id") if row_dict.get("row_id") is not None else row[0])
                    pkg = str(row_dict.get("pkg_name") or "System Notification")
                    title = str(row_dict.get("notif_title") or "")
                    raw_text = str(row_dict.get("notif_text") or "")
                    clean_text = extract_clean_text_from_payload(raw_text)
                    raw_ts = row_dict.get("notif_time")

                    # Timestamp conversion
                    dt_str = None
                    if raw_ts:
                        if isinstance(raw_ts, (int, float)) and raw_ts > 0:
                            # Windows FileTime (100ns since 1601) check
                            if raw_ts > 10000000000000000:
                                try:
                                    # Convert Windows FileTime to Unix epoch
                                    unix_sec = (raw_ts - 116444736000000000) / 10000000.0
                                    dt = datetime.fromtimestamp(unix_sec, tz=timezone.utc)
                                    dt_str = dt.isoformat()
                                except Exception:
                                    pass
                            else:
                                ts_sec = raw_ts / 1000.0 if raw_ts > 10000000000 else raw_ts
                                try:
                                    dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
                                    dt_str = dt.isoformat()
                                except Exception:
                                    pass
                        elif isinstance(raw_ts, str) and ("T" in raw_ts or "-" in raw_ts):
                            dt_str = raw_ts

                    # Clean readable app label
                    app_label = pkg.split(".")[-1].capitalize() if "." in pkg else pkg

                    normalized = {
                        "package_name": pkg,
                        "app_label": app_label,
                        "title": title or app_label,
                        "message_preview": clean_text,
                        "timestamp_utc": dt_str,
                        "raw_timestamp": raw_ts
                    }

                    artifacts.append(Artifact(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        evidence_id=evidence_id,
                        platform="android",
                        category="notifications",
                        subcategory="push_notification",
                        raw_data=row_dict,
                        normalized_data=normalized,
                        timestamp_utc=dt_str,
                        original_timestamp=str(raw_ts),
                        source_file=file_path.name,
                        source_table=target_table,
                        source_row_id=row_id,
                        parser_id=self.parser_id,
                        confidence=1.0,
                        recovery_status=RecoveryStatus.INTACT,
                        notes=f"Notification [{app_label}]: {title} - {clean_text[:60]}"
                    ))

                    if dt_str:
                        timeline_events.append(TimelineEvent(
                            id=str(uuid.uuid4()),
                            case_id=case_id,
                            evidence_id=evidence_id,
                            timestamp_utc=dt_str,
                            event_type="notification",
                            title=f"Notification ({app_label}): {title[:30]}",
                            description=clean_text[:120] if clean_text else "System alert",
                            source_file=file_path.name,
                            raw_timestamp=str(raw_ts),
                            details={"package": pkg, "title": title, "text": clean_text}
                        ))

            conn.close()
        except Exception:
            pass

        return artifacts, timeline_events
