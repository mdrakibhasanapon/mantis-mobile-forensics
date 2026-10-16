"""Android and Mobile Downloads forensic parser (downloads.db, browser downloads)."""
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Tuple
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class AndroidDownloadsParser(BaseParser):
    """Parses Android DownloadManager database (downloads.db) and browser download records."""
    parser_id = "android_downloads"
    name = "Android Download Manager Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["downloads.db", "download.db", "downloads.db-wal"]

    def can_parse(self, file_path: Path) -> bool:
        name = file_path.name.lower()
        return "download" in name and file_path.suffix.lower() in [".db", ".sqlite", ""]

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts: List[Artifact] = []
        timeline_events: List[TimelineEvent] = []

        try:
            conn = sqlite3.connect(f"file:{file_path.resolve()}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row["name"] for row in cursor.fetchall()]

            target_table = None
            for candidate in ["downloads", "download_info", "downloads_history"]:
                if candidate in tables:
                    target_table = candidate
                    break

            if target_table:
                cursor.execute(f"PRAGMA table_info({target_table})")
                cols = {c["name"] for c in cursor.fetchall()}

                uri_col = "uri" if "uri" in cols else ("url" if "url" in cols else "tab_url")
                path_col = "_data" if "_data" in cols else ("target_path" if "target_path" in cols else "local_filename")
                title_col = "title" if "title" in cols else ("display_name" if "display_name" in cols else "filename")
                size_col = "total_bytes" if "total_bytes" in cols else ("filesize" if "filesize" in cols else "bytes_total")
                mime_col = "mimetype" if "mimetype" in cols else "mime_type"
                status_col = "status" if "status" in cols else "state"
                ts_col = "lastmod" if "lastmod" in cols else ("start_time" if "start_time" in cols else "created_time")

                query = f"SELECT rowid AS row_id"
                if title_col in cols: query += f", {title_col} as file_title"
                if uri_col in cols: query += f", {uri_col} as source_url"
                if path_col in cols: query += f", {path_col} as dest_path"
                if size_col in cols: query += f", {size_col} as size_bytes"
                if mime_col in cols: query += f", {mime_col} as mime"
                if status_col in cols: query += f", {status_col} as dl_status"
                if ts_col in cols: query += f", {ts_col} as dl_timestamp"
                query += f" FROM {target_table} ORDER BY rowid ASC"

                cursor.execute(query)
                for row in cursor.fetchall():
                    row_dict = dict(row)
                    row_id = str(row_dict.get("row_id") if row_dict.get("row_id") is not None else row[0])
                    title = row_dict.get("file_title") or ""
                    url = row_dict.get("source_url") or ""
                    dest = row_dict.get("dest_path") or ""
                    size = row_dict.get("size_bytes") or 0
                    mime = row_dict.get("mime") or "application/octet-stream"
                    raw_status = row_dict.get("dl_status")
                    raw_ts = row_dict.get("dl_timestamp")

                    # If title is empty, infer from path or URL
                    if not title:
                        if dest:
                            title = Path(dest).name
                        elif url:
                            title = url.rstrip("/").split("/")[-1].split("?")[0]
                        else:
                            title = f"Download_{row_id}"

                    # Timestamp conversion
                    dt_str = None
                    if raw_ts and isinstance(raw_ts, (int, float)) and raw_ts > 0:
                        ts_sec = raw_ts / 1000.0 if raw_ts > 10000000000 else raw_ts
                        try:
                            dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
                            dt_str = dt.isoformat()
                        except Exception:
                            pass

                    # Status classification
                    status_text = "Completed"
                    if raw_status is not None:
                        if raw_status == 200 or raw_status == 1:
                            status_text = "Completed (200)"
                        elif raw_status == 192:
                            status_text = "Running / In-Progress"
                        elif raw_status >= 400:
                            status_text = f"Failed ({raw_status})"

                    normalized = {
                        "filename": title,
                        "source_url": url,
                        "destination_path": dest,
                        "file_size_bytes": size,
                        "mime_type": mime,
                        "download_status": status_text,
                        "timestamp_utc": dt_str,
                        "raw_timestamp": raw_ts
                    }

                    artifacts.append(Artifact(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        evidence_id=evidence_id,
                        platform="android",
                        category="downloads",
                        subcategory="android_download",
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
                        notes=f"Download: {title} from {url[:50] if url else 'Local'} ({size} bytes)"
                    ))

                    if dt_str:
                        timeline_events.append(TimelineEvent(
                            id=str(uuid.uuid4()),
                            case_id=case_id,
                            evidence_id=evidence_id,
                            timestamp_utc=dt_str,
                            event_type="download",
                            title=f"File Downloaded: {title}",
                            description=f"Source: {url[:80] if url else 'N/A'}. Size: {size:,} bytes.",
                            source_file=file_path.name,
                            raw_timestamp=str(raw_ts),
                            details={"filename": title, "url": url, "size": size, "path": dest}
                        ))

            conn.close()
        except Exception:
            pass

        return artifacts, timeline_events
