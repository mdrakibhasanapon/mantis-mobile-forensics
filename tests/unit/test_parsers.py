"""Unit tests for mobile forensic parsers."""
import sqlite3
import plistlib
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from mmf_core.parsers.android.contacts import AndroidContactsParser
from mmf_core.parsers.android.sms import AndroidSmsParser
from mmf_core.parsers.android.calls import AndroidCallsParser
from mmf_core.parsers.android.chrome import ChromeHistoryParser
from mmf_core.parsers.apps.whatsapp import WhatsAppParser
from mmf_core.parsers.ios.plist import IosPlistParser

def test_android_contacts_parser():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "contacts2.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
            CREATE TABLE raw_contacts (_id INTEGER PRIMARY KEY, display_name TEXT);
            """)
            conn.execute("""
            CREATE TABLE data (
                raw_contact_id INTEGER,
                mimetype TEXT,
                data1 TEXT,
                data2 TEXT
            );
            """)
            conn.execute("INSERT INTO raw_contacts VALUES (1, 'John Doe')")
            conn.execute("INSERT INTO data VALUES (1, 'vnd.android.cursor.item/phone_v2', '+15551234567', NULL)")
            conn.execute("INSERT INTO data VALUES (1, 'vnd.android.cursor.item/email_v2', 'john@example.com', NULL)")

        parser = AndroidContactsParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert artifacts[0].normalized_data["contact_name"] == "John Doe"
        assert artifacts[0].normalized_data["phone_number"] == "+15551234567"

def test_android_sms_parser():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "mmssms.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
            CREATE TABLE sms (_id INTEGER PRIMARY KEY, address TEXT, date INTEGER, date_sent INTEGER, read INTEGER, type INTEGER, body TEXT);
            """)
            conn.execute("INSERT INTO sms VALUES (1, '+15559876543', 1672531199000, 1672531199000, 1, 1, 'Meeting at confidential location.')")

        parser = AndroidSmsParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert len(timeline) == 1
        assert artifacts[0].normalized_data["sender_or_recipient"] == "+15559876543"
        assert "Meeting at confidential location" in artifacts[0].normalized_data["message_body"]

def test_android_calls_parser():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "contacts2.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
            CREATE TABLE calls (_id INTEGER PRIMARY KEY, number TEXT, date INTEGER, duration INTEGER, type INTEGER, name TEXT);
            """)
            conn.execute("INSERT INTO calls VALUES (1, '+15552345678', 1672532000000, 145, 1, 'Alice Smith')")

        parser = AndroidCallsParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert len(timeline) == 1
        assert artifacts[0].normalized_data["caller_name"] == "Alice Smith"
        assert artifacts[0].normalized_data["call_type"] == "incoming"

def test_whatsapp_parser():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "msgstore.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
            CREATE TABLE messages (_id INTEGER PRIMARY KEY, key_remote_jid TEXT, key_from_me INTEGER, key_id TEXT, status INTEGER, data TEXT, timestamp INTEGER);
            """)
            conn.execute("INSERT INTO messages VALUES (1, '15553334444@s.whatsapp.net', 0, 'MSG123', 0, 'Encrypted rendezvous confirmation', 1672533000000)")

        parser = WhatsAppParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert len(timeline) == 1
        assert artifacts[0].normalized_data["application"] == "WhatsApp"
        assert artifacts[0].normalized_data["message_text"] == "Encrypted rendezvous confirmation"

def test_ios_plist_parser():
    with tempfile.TemporaryDirectory() as td:
        plist_path = Path(td) / "Info.plist"
        data = {
            "Device Name": "Jane's iPhone",
            "Product Type": "iPhone14,2",
            "Product Version": "16.5",
            "Serial Number": "F2LZXXXXX",
            "Unique Device ID": "00008110-001234567890ABCD",
            "Is Encrypted": True
        }
        with open(plist_path, "wb") as f:
            plistlib.dump(data, f)

        parser = IosPlistParser()
        assert parser.can_parse(plist_path)
        artifacts, timeline = parser.parse(plist_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert artifacts[0].normalized_data["device_name"] == "Jane's iPhone"
        assert artifacts[0].normalized_data["product_version"] == "16.5"
        assert artifacts[0].normalized_data["is_encrypted"] is True
