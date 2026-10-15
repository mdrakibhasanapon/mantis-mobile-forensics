"""Android Contacts Parser for contacts2.db."""
import sqlite3
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime, timezone
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class AndroidContactsParser(BaseParser):
    parser_id = "android_contacts"
    name = "Android Contacts Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["contacts2.db", "contacts.db"]

    def can_parse(self, file_path: Path) -> bool:
        if file_path.name.lower() in self.target_files:
            try:
                with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('raw_contacts', 'contacts')")
                    return cur.fetchone() is not None
            except Exception:
                return False
        return False

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts = []
        timeline = []
        now_str = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            try:
                cur.execute("""
                SELECT rc._id AS raw_id, rc.display_name,
                       MAX(CASE WHEN d.mimetype = 'vnd.android.cursor.item/phone_v2' THEN d.data1 END) AS phone,
                       MAX(CASE WHEN d.mimetype = 'vnd.android.cursor.item/email_v2' THEN d.data1 END) AS email,
                       MAX(CASE WHEN d.mimetype = 'vnd.android.cursor.item/organization' THEN d.data1 END) AS company,
                       MAX(CASE WHEN d.mimetype = 'vnd.android.cursor.item/name' THEN d.data2 END) AS job_title
                FROM raw_contacts rc
                LEFT JOIN data d ON rc._id = d.raw_contact_id
                GROUP BY rc._id
                """)
                rows = cur.fetchall()
            except sqlite3.OperationalError:
                return artifacts, timeline

            for r in rows:
                art_id = str(uuid.uuid4())
                name = r["display_name"] or "Unknown"
                phone = r["phone"] or ""
                email = r["email"] or ""
                
                raw = dict(r)
                normalized = {
                    "contact_name": name,
                    "phone_number": phone,
                    "email_address": email,
                    "company": r["company"] or "",
                    "job_title": r["job_title"] or ""
                }

                art = Artifact(
                    id=art_id,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    platform=self.platform,
                    category="contacts",
                    subcategory="address_book",
                    raw_data=raw,
                    normalized_data=normalized,
                    timestamp_utc=now_str,
                    source_file=file_path.name,
                    source_table="raw_contacts",
                    source_row_id=str(r["raw_id"]),
                    parser_id=self.parser_id,
                    parser_version=self.version,
                    confidence=1.0,
                    recovery_status=RecoveryStatus.INTACT
                )
                artifacts.append(art)

        return artifacts, timeline
