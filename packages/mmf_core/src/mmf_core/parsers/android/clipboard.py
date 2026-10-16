"""Android user dictionary and keyboard/clipboard forensics parser."""
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Tuple
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class AndroidDictionaryParser(BaseParser):
    """Parses Android user dictionary database (user_dict.db)."""
    parser_id = "android_user_dict"
    name = "Android User Dictionary & Keyboard Input Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["user_dict.db", "user_dict.db-wal", "userdict.db"]

    def can_parse(self, file_path: Path) -> bool:
        name = file_path.name.lower()
        return "user_dict" in name or name in ["userdict.db", "words.db"]

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts: List[Artifact] = []
        timeline_events: List[TimelineEvent] = []

        try:
            conn = sqlite3.connect(f"file:{file_path.resolve()}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('words', 'user_words')")
            tables = [row["name"] for row in cursor.fetchall()]

            target_table = "words" if "words" in tables else ("user_words" if "user_words" in tables else None)

            if target_table:
                cursor.execute(f"PRAGMA table_info({target_table})")
                cols = {c["name"] for c in cursor.fetchall()}

                word_col = "word" if "word" in cols else "text"
                freq_col = "frequency" if "frequency" in cols else "count"
                locale_col = "locale" if "locale" in cols else "language"
                app_col = "appid" if "appid" in cols else "shortcut"

                query = f"SELECT rowid, {word_col} as word_val"
                if freq_col in cols:
                    query += f", {freq_col} as freq_val"
                if locale_col in cols:
                    query += f", {locale_col} as locale_val"
                if app_col in cols:
                    query += f", {app_col} as app_val"
                query += f" FROM {target_table} ORDER BY rowid ASC"

                cursor.execute(query)
                for row in cursor.fetchall():
                    word = row["word_val"] or ""
                    freq = row["freq_val"] if "freq_val" in row.keys() else 1
                    loc = row["locale_val"] if "locale_val" in row.keys() else ""
                    app_id = row["app_val"] if "app_val" in row.keys() else ""

                    normalized = {
                        "word": word,
                        "frequency": freq,
                        "locale": loc,
                        "appid": app_id,
                        "type": "user_dictionary_entry"
                    }

                    artifacts.append(Artifact(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        evidence_id=evidence_id,
                        platform="android",
                        category="app_data",
                        subcategory="keyboard_dictionary",
                        raw_data=dict(row),
                        normalized_data=normalized,
                        source_file=file_path.name,
                        source_table=target_table,
                        source_row_id=str(row["rowid"]),
                        parser_id=self.parser_id,
                        confidence=1.0,
                        recovery_status=RecoveryStatus.INTACT,
                        notes=f"Custom keyboard word: '{word}' (Freq: {freq})"
                    ))

            conn.close()
        except Exception:
            pass

        return artifacts, timeline_events
