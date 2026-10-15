import pytest
from pathlib import Path
from mmf_core.evidence.vault import EvidenceVault
from mmf_core.parsers.sqlite.explorer import SqliteForensicExplorer
from mmf_core.security.protection import validate_session_token, SESSION_TOKEN_ENV_VAR
import os

def test_sqlite_forbidden_queries(tmp_path: Path):
    db_file = tmp_path / "test.db"
    import sqlite3
    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE users (id INT, name TEXT);")
        conn.execute("INSERT INTO users VALUES (1, 'admin');")
        conn.commit()

    # Allowed read query
    res = SqliteForensicExplorer.execute_read_query(db_file, "SELECT * FROM users")
    assert res["count"] == 1

    # Forbidden DROP query
    with pytest.raises(PermissionError):
        SqliteForensicExplorer.execute_read_query(db_file, "DROP TABLE users;")

    # Forbidden INSERT query
    with pytest.raises(PermissionError):
        SqliteForensicExplorer.execute_read_query(db_file, "INSERT INTO users VALUES (2, 'hacker');")

    # Forbidden ATTACH query
    with pytest.raises(PermissionError):
        SqliteForensicExplorer.execute_read_query(db_file, "ATTACH DATABASE 'malicious.db' AS evil;")

def test_session_token_validation():
    os.environ[SESSION_TOKEN_ENV_VAR] = "SECRET_HEX_TOKEN_998877"
    assert validate_session_token("SECRET_HEX_TOKEN_998877") is True
    assert validate_session_token("WRONG_TOKEN") is False
    assert validate_session_token(None) is False
