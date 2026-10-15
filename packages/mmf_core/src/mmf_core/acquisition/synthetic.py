"""Synthetic mobile forensic dataset generator for verification, testing, and training."""
import sqlite3
import zipfile
import json
import os
import plistlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

def generate_synthetic_mobile_package(output_zip_path: Path) -> Path:
    """Generate a realistic mobile extraction package containing Android & iOS databases."""
    temp_dir = output_zip_path.parent / "temp_synthetic"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Device Info JSON
    dev_info = {
        "device_name": "Samsung Galaxy S22 Ultra",
        "device_id": "45ecr657864gd",
        "model": "SM-S908B",
        "manufacturer": "Samsung",
        "hardware": "exynos2200",
        "os_version": "Android 13 (Tiramisu)",
        "build_id": "TP1A.220624.014",
        "imei_1": "358686706706766",
        "imei_2": "358686706706767",
        "serial_number": "R5CR10ABCDE",
        "timezone": "UTC+00:00",
        "is_rooted": False,
        "extraction_type": "Advanced Logical Extraction"
    }
    with open(temp_dir / "device_metadata.json", "w", encoding="utf-8") as f:
        json.dump(dev_info, f, indent=2)

    # Base reference timestamps
    base_time = datetime(2025, 6, 20, 14, 30, 0, tzinfo=timezone.utc)

    # 2. Android Contacts SQLite DB: contacts2.db
    contacts_db_path = temp_dir / "contacts2.db"
    with sqlite3.connect(contacts_db_path) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE raw_contacts (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT,
            contact_id INTEGER
        );
        """)
        c.execute("""
        CREATE TABLE data (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_contact_id INTEGER,
            mimetype TEXT,
            data1 TEXT,
            data2 TEXT,
            data4 TEXT
        );
        """)
        contacts = [
            ("Noor-ul-Haq", "+15457845211", "noor.haq@secfore.org", "Intelligence Analyst"),
            ("Mr. Johnson", "+12025550199", "johnson@metropd.gov", "Detective Chief"),
            ("Rose Miller", "+447700900123", "rose.m@investigations.co.uk", "Forensic Auditor"),
            ("Jackie Robinson", "+14155552671", "jackie.r@cybersec.io", "Security Consultant"),
            ("Sarah Connor", "+13105559821", "s.connor@skydefense.net", "Operations Lead"),
            ("Alex Mercer", "+16465553948", "mercer@blackwatch.org", "Field Specialist"),
            ("Diana Prince", "+12025554321", "diana.p@themyscira.gov", "Diplomatic Envoy"),
            ("Victor Stone", "+13135557722", "vstone@star-labs.tech", "Network Architect"),
            ("Arthur Curry", "+12075558833", "acurry@atlantis-marine.org", "Marine Logistics"),
            ("Bruce Wayne", "+16095551939", "bwayne@wayne-enterprises.com", "CEO")
        ]
        for idx, (name, phone, email, title) in enumerate(contacts, 1):
            c.execute("INSERT INTO raw_contacts (_id, display_name, contact_id) VALUES (?, ?, ?)", (idx, name, idx))
            c.execute("INSERT INTO data (raw_contact_id, mimetype, data1, data2) VALUES (?, 'vnd.android.cursor.item/name', ?, ?)", (idx, name, title))
            c.execute("INSERT INTO data (raw_contact_id, mimetype, data1) VALUES (?, 'vnd.android.cursor.item/phone_v2', ?)", (idx, phone))
            c.execute("INSERT INTO data (raw_contact_id, mimetype, data1) VALUES (?, 'vnd.android.cursor.item/email_v2', ?)", (idx, email))
        conn.commit()

    # 3. Android SMS / MMS DB: mmssms.db
    sms_db_path = temp_dir / "mmssms.db"
    with sqlite3.connect(sms_db_path) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE sms (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT,
            date INTEGER,
            date_sent INTEGER,
            read INTEGER,
            type INTEGER,
            body TEXT
        );
        """)
        # type 1 = incoming, 2 = outgoing
        messages = [
            ("+15457845211", 1, "Hey examiner, the extraction report for target Alpha is ready for cross-correlation.", -180),
            ("+15457845211", 2, "Understood. Has the evidence vault verified the SHA-256 integrity hash?", -175),
            ("+15457845211", 1, "Affirmative, SHA-256 matches the laboratory intake record perfectly.", -170),
            ("+12025550199", 1, "Please verify if WhatsApp database contains unallocated freelist records.", -120),
            ("+12025550199", 2, "Running SQLite carver now. Freelist analysis active.", -115),
            ("+447700900123", 1, "Meeting scheduled with digital forensics oversight committee tomorrow.", -90),
            ("+14155552671", 1, "Target device backup imported. Manifest verification passed.", -60),
            ("+14155552671", 2, "Great, proceed with timeline reconstruction across both sources.", -55),
            ("+13105559821", 1, "Suspicious APK detected in download directory. Triggering malware triage.", -30),
            ("+16465553948", 1, "Field acquisition complete. Returning to headquarters with forensic write-blocker image.", -15)
        ]
        for addr, msg_type, body, min_offset in messages:
            ts_ms = int((base_time + timedelta(minutes=min_offset)).timestamp() * 1000)
            c.execute(
                "INSERT INTO sms (address, date, date_sent, read, type, body) VALUES (?, ?, ?, 1, ?, ?)",
                (addr, ts_ms, ts_ms, msg_type, body)
            )

        # Inject deleted SMS for recovery testing
        c.execute(
            "INSERT INTO sms (address, date, date_sent, read, type, body) VALUES (?, ?, ?, 1, 1, ?)",
            ("+19998887777", int(base_time.timestamp() * 1000), int(base_time.timestamp() * 1000), "DELETED_EVIDENCE: Transfer secret files to dropzone at 0400 hours.")
        )
        conn.commit()
        # Delete it to place it into the SQLite freelist / unallocated space
        c.execute("DELETE FROM sms WHERE address = '+19998887777'")
        conn.commit()

    # 4. Android Call Log DB: calllog.db
    call_db_path = temp_dir / "calllog.db"
    with sqlite3.connect(call_db_path) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE calls (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT,
            date INTEGER,
            duration INTEGER,
            type INTEGER,
            name TEXT
        );
        """)
        # type 1 = incoming, 2 = outgoing, 3 = missed
        calls = [
            ("+15457845211", 1, 342, "Noor-ul-Haq", -240),
            ("+12025550199", 2, 115, "Mr. Johnson", -200),
            ("+447700900123", 3, 0, "Rose Miller", -150),
            ("+14155552671", 1, 560, "Jackie Robinson", -110),
            ("+13105559821", 2, 85, "Sarah Connor", -75),
            ("+16465553948", 1, 230, "Alex Mercer", -45),
            ("+12025554321", 3, 0, "Diana Prince", -20)
        ]
        for num, c_type, dur, name, min_offset in calls:
            ts_ms = int((base_time + timedelta(minutes=min_offset)).timestamp() * 1000)
            c.execute("INSERT INTO calls (number, date, duration, type, name) VALUES (?, ?, ?, ?, ?)", (num, ts_ms, dur, c_type, name))
        conn.commit()

    # 5. Chrome Browser DB: History
    chrome_db_path = temp_dir / "History"
    with sqlite3.connect(chrome_db_path) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            title TEXT,
            visit_count INTEGER,
            last_visit_time INTEGER
        );
        """)
        urls = [
            ("https://github.com/google/mantis-forensics", "Mantis Mobile Forensics Research", 14, -300),
            ("https://www.kali.org/tools/forensics/", "Kali Linux Digital Forensics Toolsuite", 8, -250),
            ("https://cybersecurity.gov/advisories/APT-42", "Threat Intelligence Advisory APT-42", 5, -180),
            ("https://sqlite.org/fileformat.html", "SQLite Database File Format Documentation", 22, -100),
            ("https://duckduckgo.com/?q=android+wal+freelist+carving", "android wal freelist carving - DuckDuckGo", 3, -40),
            ("https://darkweb-portal.onion.fake/drop/8842", "Anonymous Secure Dropzone (FLAGGED)", 1, -10)
        ]
        for url, title, count, min_offset in urls:
            # Chrome epoch: microseconds since Jan 1, 1601
            epoch_diff = (base_time + timedelta(minutes=min_offset) - datetime(1601, 1, 1, tzinfo=timezone.utc)).total_seconds()
            chrome_ts = int(epoch_diff * 1_000_000)
            c.execute("INSERT INTO urls (url, title, visit_count, last_visit_time) VALUES (?, ?, ?, ?)", (url, title, count, chrome_ts))
        conn.commit()

    # 6. WhatsApp DB: msgstore.db
    wa_db_path = temp_dir / "msgstore.db"
    with sqlite3.connect(wa_db_path) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE messages (
            _id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_remote_jid TEXT,
            key_from_me INTEGER,
            key_id TEXT,
            status INTEGER,
            data TEXT,
            timestamp INTEGER
        );
        """)
        wa_messages = [
            ("15457845211@s.whatsapp.net", 0, "WA001", 0, "Case files encrypted using AES-256-GCM. Stored on local vault.", -160),
            ("15457845211@s.whatsapp.net", 1, "WA002", 2, "Confirmed. All examiners must log operations in append-only audit trail.", -155),
            ("447700900123@s.whatsapp.net", 0, "WA003", 0, "Timeline correlation confirmed link between phone +15457845211 and +12025550199.", -80)
        ]
        for jid, from_me, key_id, status, text, min_offset in wa_messages:
            ts_ms = int((base_time + timedelta(minutes=min_offset)).timestamp() * 1000)
            c.execute("INSERT INTO messages (key_remote_jid, key_from_me, key_id, status, data, timestamp) VALUES (?, ?, ?, ?, ?, ?)", (jid, from_me, key_id, status, text, ts_ms))
        conn.commit()

    # 7. iOS Backup Info.plist & Status.plist
    ios_info = {
        "Device Name": "iPhone 14 Pro",
        "Product Type": "iPhone15,2",
        "Product Version": "16.5",
        "Build Version": "20F66",
        "Serial Number": "F2LL70ABC9",
        "Unique Device ID": "00008110-001A24683A00801E",
        "GUID": "39A7A64C-1122-3344-5566-778899AABBCC",
        "Is Encrypted": False,
        "Last Backup Date": base_time.isoformat()
    }
    with open(temp_dir / "Info.plist", "wb") as f:
        plistlib.dump(ios_info, f)

    status_plist = {
        "BackupState": "completed",
        "Date": base_time.isoformat(),
        "IsFullBackup": True,
        "Version": "10.0"
    }
    with open(temp_dir / "Status.plist", "wb") as f:
        plistlib.dump(status_plist, f)

    # 8. Suspicious APK Manifest XML (for malware triage)
    manifest_xml = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="org.secfore.suspicious_service" android:versionCode="1" android:versionName="1.0">
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.READ_SMS" />
    <uses-permission android:name="android.permission.SEND_SMS" />
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
    <uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <application android:allowBackup="true" android:label="SystemUpdateService">
        <service android:name=".StealthPayload" android:exported="false" />
        <receiver android:name=".BootReceiver" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
            </intent-filter>
        </receiver>
    </application>
</manifest>
"""
    with open(temp_dir / "AndroidManifest.xml", "w", encoding="utf-8") as f:
        f.write(manifest_xml)

    # Compress into synthetic mobile package ZIP
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in temp_dir.iterdir():
            if file.is_file():
                zipf.write(file, arcname=file.name)

    # Clean up temp files
    for file in temp_dir.iterdir():
        if file.is_file():
            file.unlink()
    temp_dir.rmdir()

    return output_zip_path
