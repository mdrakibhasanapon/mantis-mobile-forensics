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

def test_messenger_parser():
    from mmf_core.parsers.apps.messenger import MessengerParser
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "threads_db2"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
            CREATE TABLE messages (
                msg_id TEXT PRIMARY KEY,
                thread_key TEXT,
                text TEXT,
                sender TEXT,
                timestamp_ms INTEGER,
                attachments TEXT
            );
            """)
            conn.execute("INSERT INTO messages VALUES ('m1', 't1', 'Messenger forensic message', 'Suspect_Alice', 1672538000000, '[]');")

        parser = MessengerParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert len(timeline) == 1
        assert artifacts[0].normalized_data["text"] == "Messenger forensic message"
        assert artifacts[0].normalized_data["sender"] == "Suspect_Alice"

def test_imo_parser():
    from mmf_core.parsers.apps.imo import ImoParser
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "imofriends.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE friends (buid TEXT PRIMARY KEY, alias TEXT, name TEXT, phone TEXT);")
            conn.execute("CREATE TABLE chat_messages (buid TEXT, message TEXT, timestamp INTEGER);")
            conn.execute("INSERT INTO friends VALUES ('b1', 'ImoFriend', 'Bob', '+8801700000000');")
            conn.execute("INSERT INTO chat_messages VALUES ('b1', 'Hello from IMO', 1672538000000);")

        parser = ImoParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 2
        assert any(a.category == "contacts" and a.normalized_data["phone_number"] == "+8801700000000" for a in artifacts)
        assert any(a.category == "messages" and a.normalized_data["text"] == "Hello from IMO" for a in artifacts)

def test_instagram_parser():
    from mmf_core.parsers.apps.instagram import InstagramDirectParser
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "direct_v2.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
            CREATE TABLE messages (
                message_id TEXT PRIMARY KEY,
                thread_id TEXT,
                user_id TEXT,
                text TEXT,
                timestamp INTEGER,
                message_type TEXT
            );
            """)
            conn.execute("INSERT INTO messages VALUES ('ig1', 't100', 'user_cyber', 'Secret Instagram DM', 1672538000000000, 'text');")

        parser = InstagramDirectParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert artifacts[0].normalized_data["text"] == "Secret Instagram DM"
        assert artifacts[0].normalized_data["user_id"] == "user_cyber"

def test_discord_parser():
    from mmf_core.parsers.apps.discord import DiscordParser
    with tempfile.TemporaryDirectory() as td:
        disc_dir = Path(td) / "discord_cache"
        disc_dir.mkdir()
        db_path = disc_dir / "messages.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
            CREATE TABLE messages (
                id TEXT PRIMARY KEY,
                channel_id TEXT,
                author_username TEXT,
                content TEXT,
                timestamp INTEGER
            );
            """)
            conn.execute("INSERT INTO messages VALUES ('d1', 'c1', 'DarkOperator', 'Discord operational payload', 1672538000000);")

        parser = DiscordParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert artifacts[0].normalized_data["author"] == "DarkOperator"
        assert artifacts[0].normalized_data["content"] == "Discord operational payload"

def test_android_dictionary_parser():
    from mmf_core.parsers.android.clipboard import AndroidDictionaryParser
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "user_dict.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE words (word TEXT, frequency INTEGER, locale TEXT, appid TEXT);")
            conn.execute("INSERT INTO words VALUES ('cryptopass123', 250, 'en_US', 'gboard');")

        parser = AndroidDictionaryParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert artifacts[0].normalized_data["word"] == "cryptopass123"
        assert artifacts[0].normalized_data["frequency"] == 250

def test_exif_gps_parser():
    from mmf_core.parsers.media.exif import ExifGpsParser
    from PIL import Image
    from fractions import Fraction
    with tempfile.TemporaryDirectory() as td:
        img_path = Path(td) / "evidence.jpg"
        img = Image.new("RGB", (50, 50), color=(10, 20, 30))
        exif = img.getexif()
        exif[271] = "Apple"
        exif[272] = "iPhone 14 Pro"
        gps_ifd = exif.get_ifd(0x8825)
        gps_ifd[1] = "N"
        gps_ifd[2] = (Fraction(23, 1), Fraction(48, 1), Fraction(37, 1))
        gps_ifd[3] = "E"
        gps_ifd[4] = (Fraction(90, 1), Fraction(24, 1), Fraction(45, 1))
        img.save(img_path, exif=exif)

        parser = ExifGpsParser()
        assert parser.can_parse(img_path)
        artifacts, timeline = parser.parse(img_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert artifacts[0].normalized_data["has_gps"] is True
        assert artifacts[0].normalized_data["camera_make"] == "Apple"
        assert round(artifacts[0].normalized_data["latitude"], 2) == 23.81
        assert round(artifacts[0].normalized_data["longitude"], 2) == 90.41

def test_deep_triage_scanner():
    from mmf_core.triage.analyzer import TriageAnalyzer
    from mmf_core.models import Artifact, RecoveryStatus
    import uuid

    arts = [
        Artifact(
            id=str(uuid.uuid4()),
            case_id="case_1",
            evidence_id="ev_1",
            platform="android",
            category="messages",
            source_file="msg.db",
            parser_id="test",
            normalized_data={"text": "Send ransom to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh right now"}
        ),
        Artifact(
            id=str(uuid.uuid4()),
            case_id="case_1",
            evidence_id="ev_1",
            platform="android",
            category="browser",
            source_file="hist.db",
            parser_id="test",
            normalized_data={"url": "http://darknetvault5h3j4k.onion/market"}
        ),
        Artifact(
            id=str(uuid.uuid4()),
            case_id="case_1",
            evidence_id="ev_1",
            platform="android",
            category="messages",
            source_file="msg.db",
            parser_id="test",
            normalized_data={"text": "Card detail: 4532 0150 1234 5671"}
        )
    ]

    findings = TriageAnalyzer.scan_artifacts("case_1", arts)
    categories = [f.category for f in findings]
    assert "cryptocurrency" in categories
    assert "suspicious_url" in categories
    assert "financial_card" in categories

def test_communication_link_analysis():
    from mmf_core.correlation.engine import CorrelationEngine
    from mmf_core.models import Artifact
    import uuid

    arts = [
        Artifact(
            id=str(uuid.uuid4()),
            case_id="c1",
            evidence_id="e1",
            platform="android",
            category="calls",
            subcategory="calls",
            timestamp_utc="2025-06-20T14:30:00Z",
            source_file="calls.db",
            parser_id="test",
            normalized_data={"sender_or_recipient": "+15551234567"}
        ),
        Artifact(
            id=str(uuid.uuid4()),
            case_id="c1",
            evidence_id="e1",
            platform="android",
            category="messages",
            subcategory="whatsapp",
            timestamp_utc="2025-06-20T15:00:00Z",
            source_file="msgstore.db",
            parser_id="test",
            normalized_data={"sender_or_recipient": "+15551234567", "text": "Are you ready?"}
        )
    ]

    graph = CorrelationEngine.build_communication_graph("c1", arts)
    assert graph["metrics"]["total_interactions"] == 2
    assert len(graph["nodes"]) >= 2
    assert any(n["id"] == "+15551234567" for n in graph["nodes"])
    assert "whatsapp" in graph["metrics"]["channel_distribution"]

def test_android_downloads_parser():
    from mmf_core.parsers.android.downloads import AndroidDownloadsParser
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "downloads.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
            CREATE TABLE downloads (
                _id INTEGER PRIMARY KEY,
                uri TEXT,
                _data TEXT,
                mimetype TEXT,
                title TEXT,
                total_bytes INTEGER,
                status INTEGER,
                lastmod INTEGER
            );
            """)
            conn.execute("INSERT INTO downloads VALUES (1, 'https://test.org/trojan.apk', '/sdcard/Download/trojan.apk', 'application/vnd.android.package-archive', 'trojan.apk', 1048576, 200, 1672538000000);")

        parser = AndroidDownloadsParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert len(timeline) == 1
        assert artifacts[0].normalized_data["filename"] == "trojan.apk"
        assert artifacts[0].normalized_data["source_url"] == "https://test.org/trojan.apk"
        assert artifacts[0].normalized_data["file_size_bytes"] == 1048576

def test_android_notifications_parser():
    from mmf_core.parsers.android.notifications import AndroidNotificationsParser
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "notification_log.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
            CREATE TABLE notifications (
                _id INTEGER PRIMARY KEY,
                package_name TEXT,
                title TEXT,
                text TEXT,
                timestamp INTEGER
            );
            """)
            conn.execute("INSERT INTO notifications VALUES (1, 'com.whatsapp', '+15551234', 'Secret deleted message preview', 1672538000000);")

        parser = AndroidNotificationsParser()
        assert parser.can_parse(db_path)
        artifacts, timeline = parser.parse(db_path, "ev_test", "case_test")
        assert len(artifacts) == 1
        assert len(timeline) == 1
        assert artifacts[0].normalized_data["package_name"] == "com.whatsapp"
        assert artifacts[0].normalized_data["message_preview"] == "Secret deleted message preview"



