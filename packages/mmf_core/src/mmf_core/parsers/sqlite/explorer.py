"""SQLite forensic analysis engine: schema inspection, safe read-only queries, and freelist forensics."""
import sqlite3
import re
import struct
from pathlib import Path
from typing import Dict, Any, List, Optional
from ...models import RecoveredItem, RecoveryStatus

SQLITE3_MAGIC = b"SQLite format 3\x00"

class SqliteForensicExplorer:
    """Read-only forensic examiner for SQLite databases and unallocated space."""

    @staticmethod
    def is_sqlite_database(file_path: Path) -> bool:
        if not file_path.is_file() or file_path.stat().st_size < 100:
            return False
        with open(file_path, "rb") as f:
            header = f.read(16)
            return header == SQLITE3_MAGIC

    @staticmethod
    def get_database_header(file_path: Path) -> Dict[str, Any]:
        """Parse the 100-byte SQLite database header."""
        if not SqliteForensicExplorer.is_sqlite_database(file_path):
            raise ValueError(f"File is not a valid SQLite database: {file_path}")

        with open(file_path, "rb") as f:
            raw = f.read(100)

        page_size = struct.unpack(">H", raw[16:18])[0]
        if page_size == 1:
            page_size = 65536
        freelist_pages = struct.unpack(">I", raw[36:40])[0]
        change_counter = struct.unpack(">I", raw[24:28])[0]
        schema_cookie = struct.unpack(">I", raw[40:44])[0]
        encoding = struct.unpack(">I", raw[56:60])[0]
        encoding_name = {1: "UTF-8", 2: "UTF-16le", 3: "UTF-16be"}.get(encoding, f"Unknown ({encoding})")

        wal_path = file_path.parent / f"{file_path.name}-wal"
        shm_path = file_path.parent / f"{file_path.name}-shm"

        return {
            "page_size": page_size,
            "file_size": file_path.stat().st_size,
            "total_pages": file_path.stat().st_size // page_size if page_size else 0,
            "freelist_pages": freelist_pages,
            "change_counter": change_counter,
            "schema_cookie": schema_cookie,
            "encoding": encoding_name,
            "wal_present": wal_path.exists(),
            "shm_present": shm_path.exists()
        }

    @staticmethod
    def get_schema(file_path: Path) -> List[Dict[str, Any]]:
        """List all tables, views, and schemas in the SQLite database."""
        with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT type, name, tbl_name, rootpage, sql FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name")
            tables = []
            for r in cur.fetchall():
                t_name = r["name"]
                if t_name.startswith("sqlite_stat"):
                    continue
                # Get column info
                cols = []
                try:
                    c_cur = conn.cursor()
                    c_cur.execute(f"PRAGMA table_info('{t_name}')")
                    for c_row in c_cur.fetchall():
                        cols.append({
                            "cid": c_row[0],
                            "name": c_row[1],
                            "type": c_row[2],
                            "notnull": bool(c_row[3]),
                            "dflt_value": c_row[4],
                            "pk": bool(c_row[5])
                        })
                    c_cur.execute(f"SELECT COUNT(*) FROM '{t_name}'")
                    row_count = c_cur.fetchone()[0]
                except Exception:
                    row_count = 0

                tables.append({
                    "type": r["type"],
                    "name": t_name,
                    "rootpage": r["rootpage"],
                    "sql": r["sql"],
                    "columns": cols,
                    "row_count": row_count
                })
            return tables

    @staticmethod
    def serialize_cell(val: Any) -> Any:
        """Convert raw SQLite types (including BLOBs and binary data) into safe, human-interpretable format."""
        if val is None:
            return None
        if isinstance(val, (int, float, bool)):
            return val
        if isinstance(val, bytes):
            # Check if it's UTF-8 decodable and printable text
            try:
                decoded = val.decode("utf-8")
                if len(decoded) > 0 and all(c.isprintable() or c in "\r\n\t" for c in decoded):
                    return decoded
            except Exception:
                pass

            import base64
            tag = "BLOB"
            mime = "application/octet-stream"
            if val.startswith(b"\x89PNG\r\n\x1a\n"):
                tag = "PNG Image"
                mime = "image/png"
            elif val.startswith(b"\xff\xd8\xff"):
                tag = "JPEG Image"
                mime = "image/jpeg"
            elif val.startswith(b"GIF8"):
                tag = "GIF Image"
                mime = "image/gif"
            elif val.startswith(b"RIFF") and b"WEBP" in val[:16]:
                tag = "WebP Image"
                mime = "image/webp"
            elif val.startswith(b"bplist00"):
                tag = "Apple Binary Plist"
                mime = "application/x-plist"
            elif val.startswith(b"SQLite format 3\x00"):
                tag = "Embedded SQLite DB"
                mime = "application/vnd.sqlite3"
            elif val.startswith(b"PK\x03\x04"):
                tag = "ZIP Archive"
                mime = "application/zip"

            b64 = base64.b64encode(val).decode("ascii")
            hex_str = val[:128].hex()
            return {
                "__type__": "blob",
                "tag": tag,
                "mime": mime,
                "size": len(val),
                "hex": hex_str,
                "has_more_hex": len(val) > 128,
                "base64": b64 if len(val) <= 1024 * 50 else b64[:5000],
                "display": f"[{tag}: {len(val)}B | 0x{hex_str[:16]}...]"
            }
        if isinstance(val, str):
            # Clean non-printable control characters that corrupt rendering
            cleaned = []
            for ch in val:
                if ch.isprintable() or ch in "\r\n\t":
                    cleaned.append(ch)
                else:
                    cleaned.append(f"\\x{ord(ch):02x}")
            return "".join(cleaned)
        return str(val)

    @staticmethod
    def execute_read_query(file_path: Path, sql_query: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Safely execute a bounded SELECT query."""
        # Enforce read-only constraint
        forbidden = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "ATTACH", "DETACH", "PRAGMA", "REINDEX", "VACUUM"]
        normalized = sql_query.strip().upper()
        for kw in forbidden:
            if re.search(rf"\b{kw}\b", normalized):
                raise PermissionError(f"Forbidden statement: {kw} is not permitted in read-only forensic mode")

        # Strip existing trailing semicolon and apply LIMIT/OFFSET if not present
        clean_query = sql_query.rstrip("; \t\n")
        if "LIMIT" not in clean_query.upper():
            clean_query += f" LIMIT {limit} OFFSET {offset}"

        with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(clean_query)
            col_names = [d[0] for d in cur.description] if cur.description else []
            raw_rows = cur.fetchall()
            rows = []
            for r in raw_rows:
                row_dict = {}
                for col in col_names:
                    row_dict[col] = SqliteForensicExplorer.serialize_cell(r[col])
                rows.append(row_dict)

            return {
                "columns": col_names,
                "rows": rows,
                "count": len(rows),
                "query": clean_query
            }

    @staticmethod
    def carve_freelist_strings(file_path: Path, min_length: int = 6) -> List[Dict[str, Any]]:
        """Carve readable text fragments from unallocated space / freelists."""
        if not file_path.is_file():
            return []

        results = []
        with open(file_path, "rb") as f:
            data = f.read()

        # Simple ASCII/UTF-8 carving pattern
        pattern = re.compile(rb"[\x20-\x7E]{" + str(min_length).encode() + rb",}")
        for match in pattern.finditer(data):
            offset = match.start()
            matched_bytes = match.group()
            text = matched_bytes.decode("ascii", errors="ignore")
            # Filter noise
            if any(marker in text for marker in ["SELECT", "CREATE TABLE", "SQLite format", "index"]):
                continue
            if len(text.strip()) >= min_length:
                results.append({
                    "offset": offset,
                    "text": text.strip()[:200],
                    "length": len(matched_bytes)
                })

        return results[:200]  # Cap results for performance
