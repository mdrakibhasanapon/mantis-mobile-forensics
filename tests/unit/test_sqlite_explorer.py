"""Unit tests for SQLite Forensic Explorer."""
import sqlite3
import pytest
import tempfile
from pathlib import Path

from mmf_core.parsers.sqlite.explorer import SqliteForensicExplorer

def test_sqlite_detection_and_header():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE evidence (id INTEGER PRIMARY KEY, item TEXT)")
            conn.execute("INSERT INTO evidence VALUES (1, 'USB Thumb Drive')")

        assert SqliteForensicExplorer.is_sqlite_database(db_path) is True
        header = SqliteForensicExplorer.get_database_header(db_path)
        assert header["page_size"] > 0
        assert header["encoding"] in ["UTF-8", "UTF-16le", "UTF-16be"]

def test_sqlite_schema_inspection():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test_schema.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, email TEXT)")
            conn.execute("INSERT INTO users VALUES (1, 'examiner', 'examiner@forensics.lab')")

        schema = SqliteForensicExplorer.get_schema(db_path)
        assert len(schema) == 1
        assert schema[0]["name"] == "users"
        assert schema[0]["row_count"] == 1
        col_names = [c["name"] for c in schema[0]["columns"]]
        assert "username" in col_names
        assert "email" in col_names

def test_sqlite_query_execution():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test_query.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE logs (id INTEGER PRIMARY KEY, msg TEXT)")
            conn.execute("INSERT INTO logs VALUES (1, 'System started')")
            conn.execute("INSERT INTO logs VALUES (2, 'Device connected')")

        res = SqliteForensicExplorer.execute_read_query(db_path, "SELECT * FROM logs", limit=10)
        assert res["count"] == 2
        assert len(res["rows"]) == 2
        assert res["columns"] == ["id", "msg"]

def test_sqlite_forbidden_query_rejection():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test_block.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE sensitive (id INTEGER PRIMARY KEY, val TEXT)")

        with pytest.raises(PermissionError):
            SqliteForensicExplorer.execute_read_query(db_path, "DROP TABLE sensitive")

        with pytest.raises(PermissionError):
            SqliteForensicExplorer.execute_read_query(db_path, "DELETE FROM sensitive")

def test_sqlite_blob_and_garbage_sanitization():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test_blob.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE forensics (id INTEGER PRIMARY KEY, raw_blob BLOB, noisy_str TEXT)")
            # Insert binary PNG magic header and control-character string
            conn.execute("INSERT INTO forensics VALUES (1, ?, ?)", (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", "Data\x00Value\x07"))

        res = SqliteForensicExplorer.execute_read_query(db_path, "SELECT * FROM forensics")
        assert res["count"] == 1
        row = res["rows"][0]
        # Verify BLOB is safely structured
        assert isinstance(row["raw_blob"], dict)
        assert row["raw_blob"]["__type__"] == "blob"
        assert row["raw_blob"]["tag"] == "PNG Image"
        assert row["raw_blob"]["mime"] == "image/png"
        assert row["raw_blob"]["size"] == 16
        # Verify string control chars are sanitized without crash
        assert "Data" in row["noisy_str"]
        assert "\\x00" in row["noisy_str"]
