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
from mmf_core.parsers.android.wifi import AndroidWifiParser
from mmf_core.parsers.android.bluetooth import AndroidBluetoothParser
from mmf_core.parsers.android.packages import AndroidPackagesParser
from mmf_core.parsers.apps.whatsapp import WhatsAppParser
from mmf_core.parsers.apps.telegram import TelegramParser
from mmf_core.parsers.apps.signal import SignalParser
from mmf_core.parsers.ios.plist import IosPlistParser
from mmf_core.parsers.ios.sms import IosSmsParser
from mmf_core.parsers.ios.callhistory import IosCallHistoryParser
from mmf_core.parsers.ios.safari import IosSafariParser

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

def test_telegram_parser():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "cache4.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE users (uid INTEGER PRIMARY KEY, name TEXT);")
            conn.execute("CREATE TABLE messages_v2 (mid INTEGER PRIMARY KEY, uid INTEGER, date INTEGER, message TEXT);")
            conn.execute("INSERT INTO users VALUES (12345, 'Agent Cooper');")
            conn.execute("INSERT INTO messages_v2 VALUES (101, 12345, 1672534000, 'Undercover payload dispatched');")

        parser = TelegramParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert len(timeline) == 1
        assert artifacts[0].normalized_data["sender_or_peer"] == "Agent Cooper"
        assert artifacts[0].normalized_data["message_body"] == "Undercover payload dispatched"

def test_signal_parser():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "signal.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE recipient (_id INTEGER PRIMARY KEY, phone TEXT, system_display_name TEXT, profile_joined_name TEXT);")
            conn.execute("CREATE TABLE message (_id INTEGER PRIMARY KEY, date_sent INTEGER, recipient_id INTEGER, body TEXT);")
            conn.execute("INSERT INTO recipient VALUES (1, '+15554445555', 'Sarah Connor', NULL);")
            conn.execute("INSERT INTO message VALUES (1, 1672535000000, 1, 'Encrypted signal transmission');")

        parser = SignalParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert len(timeline) == 1
        assert artifacts[0].normalized_data["contact_or_recipient"] == "Sarah Connor"
        assert artifacts[0].normalized_data["message_body"] == "Encrypted signal transmission"

def test_android_wifi_parser():
    with tempfile.TemporaryDirectory() as td:
        xml_path = Path(td) / "WifiConfigStore.xml"
        xml_content = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<WifiConfigStoreData>
  <Network>
    <WifiConfiguration>
      <string name="ConfigKey">&quot;Target_Secure_WiFi&quot;WPA_PSK</string>
      <string name="SSID">&quot;Target_Secure_WiFi&quot;</string>
      <string name="PreSharedKey">&quot;SuperSecretPass123!&quot;</string>
      <string name="KeyMgmt">WPA_PSK</string>
      <long name="CreationTime" value="1672536000000" />
    </WifiConfiguration>
  </Network>
</WifiConfigStoreData>"""
        xml_path.write_text(xml_content, encoding="utf-8")

        parser = AndroidWifiParser()
        assert parser.can_parse(xml_path)
        artifacts, timeline = parser.parse(xml_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert len(timeline) == 1
        assert artifacts[0].normalized_data["network_name"] == "Target_Secure_WiFi"
        assert artifacts[0].normalized_data["password"] == "SuperSecretPass123!"

def test_android_bluetooth_parser():
    with tempfile.TemporaryDirectory() as td:
        conf_path = Path(td) / "bt_config.conf"
        conf_content = """[00:1A:7D:DA:71:13]
Timestamp = 1672537000
DevClass = 00240404
DevType = 1
AddrType = 0
Manufacturer = 15
Name = Forensic_Target_Headphones
LinkKey = 11223344556677889900aabbccddeeff
"""
        conf_path.write_text(conf_content, encoding="utf-8")

        parser = AndroidBluetoothParser()
        assert parser.can_parse(conf_path)
        artifacts, timeline = parser.parse(conf_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert len(timeline) == 1
        assert artifacts[0].normalized_data["device_name"] == "Forensic_Target_Headphones"
        assert artifacts[0].normalized_data["mac_address"] == "00:1A:7D:DA:71:13"

def test_android_packages_parser():
    with tempfile.TemporaryDirectory() as td:
        pkg_path = Path(td) / "packages.xml"
        pkg_content = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<packages>
  <package name="org.suspicious.stalker" codePath="/data/app/org.suspicious.stalker-1" it="1672538000000" ut="1672538000000" installer="com.android.vending">
    <perms>
      <item name="android.permission.INTERNET" />
      <item name="android.permission.RECORD_AUDIO" />
      <item name="android.permission.ACCESS_FINE_LOCATION" />
      <item name="android.permission.READ_SMS" />
    </perms>
  </package>
</packages>"""
        pkg_path.write_text(pkg_content, encoding="utf-8")

        parser = AndroidPackagesParser()
        assert parser.can_parse(pkg_path)
        artifacts, timeline = parser.parse(pkg_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert len(timeline) == 1
        assert artifacts[0].normalized_data["package_name"] == "org.suspicious.stalker"
        assert artifacts[0].normalized_data["high_risk_surveillance"] is True

def test_ios_sms_parser():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "sms.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE handle (ROWID INTEGER PRIMARY KEY, id TEXT, service TEXT);")
            conn.execute("CREATE TABLE message (ROWID INTEGER PRIMARY KEY, guid TEXT, text TEXT, handle_id INTEGER, date INTEGER, is_from_me INTEGER, service TEXT);")
            conn.execute("INSERT INTO handle VALUES (1, '+15557778888', 'iMessage');")
            # Apple epoch 700000000000000000 ns -> 2023+
            conn.execute("INSERT INTO message VALUES (1, 'GUID-123', 'Exfiltrated token payload', 1, 700000000000000000, 0, 'iMessage');")

        parser = IosSmsParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert len(timeline) == 1
        assert artifacts[0].normalized_data["sender_or_recipient"] == "+15557778888"
        assert artifacts[0].normalized_data["message_body"] == "Exfiltrated token payload"

def test_ios_callhistory_parser():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "CallHistory.storedata"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE ZCALLRECORD (Z_PK INTEGER PRIMARY KEY, ZADDRESS TEXT, ZDATE REAL, ZDURATION INTEGER, ZORIGINATED INTEGER, ZANSWERED INTEGER, ZSERVICE_PROVIDER TEXT);")
            conn.execute("INSERT INTO ZCALLRECORD VALUES (1, '+15559990000', 700000000.0, 182, 1, 1, 'Telephony');")

        parser = IosCallHistoryParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert len(timeline) == 1
        assert artifacts[0].normalized_data["phone_number"] == "+15559990000"
        assert artifacts[0].normalized_data["duration_seconds"] == 182
        assert artifacts[0].normalized_data["direction"] == "outgoing"

def test_ios_safari_parser():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "History.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE history_items (id INTEGER PRIMARY KEY, url TEXT, visit_count INTEGER);")
            conn.execute("CREATE TABLE history_visits (id INTEGER PRIMARY KEY, history_item INTEGER, visit_time REAL, title TEXT);")
            conn.execute("INSERT INTO history_items VALUES (1, 'https://github.com/mdrakibhasanapon', 42);")
            conn.execute("INSERT INTO history_visits VALUES (1, 1, 700000000.0, 'Developer GitHub Profile');")

        parser = IosSafariParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert len(timeline) == 1
        assert artifacts[0].normalized_data["url"] == "https://github.com/mdrakibhasanapon"
        assert artifacts[0].normalized_data["title"] == "Developer GitHub Profile"
        assert artifacts[0].normalized_data["visit_count"] == 42

