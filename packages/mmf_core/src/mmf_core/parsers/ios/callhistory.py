"""iOS Call History Parser for CallHistory.storedata."""
import sqlite3
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime, timezone
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus
from .sms import cocoa_to_iso

class IosCallHistoryParser(BaseParser):
    parser_id = "ios_callhistory"
    name = "iOS Call History Parser"
    version = "1.0.0"
    platform = "ios"
    target_files = ["callhistory.storedata", "call_history.db"]

    def can_parse(self, file_path: Path) -> bool:
        name_lower = file_path.name.lower()
        if name_lower in self.target_files or "callhistory" in name_lower:
            try:
                with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('ZCALLRECORD', 'calls')")
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

            # Detect CoreData table ZCALLRECORD or standard calls
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('ZCALLRECORD', 'calls')")
            row = cur.fetchone()
            if not row:
                return artifacts, timeline
            tbl_name = row["name"]

            cur.execute(f"PRAGMA table_info({tbl_name})")
            cols = {c["name"] for c in cur.fetchall()}

            pk_col = "Z_PK" if "Z_PK" in cols else "id" if "id" in cols else "ROWID"
            addr_col = "ZADDRESS" if "ZADDRESS" in cols else "address" if "address" in cols else "number"
            date_col = "ZDATE" if "ZDATE" in cols else "date"
            dur_col = "ZDURATION" if "ZDURATION" in cols else "duration"
            orig_col = "ZORIGINATED" if "ZORIGINATED" in cols else "originated"
            ans_col = "ZANSWERED" if "ZANSWERED" in cols else "answered"
            svc_col = "ZSERVICE_PROVIDER" if "ZSERVICE_PROVIDER" in cols else "'Telephony'"

            query = f"SELECT {pk_col} as call_id, {addr_col} as phone_number, {date_col} as call_date, {dur_col} as duration_sec, {orig_col} as is_originated, {ans_col} as is_answered, {svc_col} as service FROM {tbl_name}"
            try:
                cur.execute(query)
                rows = cur.fetchall()
            except Exception:
                return artifacts, timeline

            for r in rows:
                art_id = str(uuid.uuid4())
                raw_date = r["call_date"]
                iso_ts = cocoa_to_iso(raw_date)

                is_orig = bool(r["is_originated"])
                direction = "outgoing" if is_orig else "incoming"
                answered = bool(r["is_answered"])
                duration = int(r["duration_sec"] or 0)
                phone_num = str(r["phone_number"] or "Unknown")
                svc = str(r["service"] or "Telephony")

                raw = {
                    "id": r["call_id"],
                    "address": phone_num,
                    "date_cocoa": raw_date,
                    "duration": duration,
                    "originated": is_orig,
                    "answered": answered,
                    "service": svc
                }
                normalized = {
                    "phone_number": phone_num,
                    "direction": direction,
                    "answered": answered,
                    "duration_seconds": duration,
                    "service_provider": svc,
                    "timestamp": iso_ts
                }

                art = Artifact(
                    id=art_id,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    platform=self.platform,
                    category="calls",
                    subcategory="ios_call",
                    raw_data=raw,
                    normalized_data=normalized,
                    timestamp_utc=iso_ts,
                    original_timestamp=str(raw_date) if raw_date else None,
                    source_file=file_path.name,
                    source_table=tbl_name,
                    source_row_id=str(r["call_id"]),
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
                    event_type="call",
                    title=f"iOS Call ({direction.upper()}): {phone_num}",
                    description=f"Duration: {duration}s | Answered: {answered} | Service: {svc}",
                    source_file=file_path.name,
                    details=normalized
                ))

        return artifacts, timeline
