import csv
import os
from datetime import datetime

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://claude_muanda_2@localhost:5432/ibcb_rocketmail"
)

CLICKFUNNELS_FILE = "/Users/claude_muanda_2/Documents/Documents - Claude_Muanda_2’s MacBook Pro/IBCB_LLC/CLEANED_BACKUP_CLICKLIST.csv"

BABYCARE_FILE = "/Users/claude_muanda_2/Documents/Documents - Claude_Muanda_2’s MacBook Pro/iBCB_RocketMail/babycare_leads_consolidated_2026-08-07.csv"

engine = create_engine(DATABASE_URL)


def clean_email(value):
    if not value:
        return None
    value = value.strip().lower()
    return value or None


def clean_name(value):
    if not value:
        return None
    value = value.strip()
    return value or None


def get_segment_id(conn, code):
    return conn.execute(
        text("SELECT id FROM segments WHERE code = :code"),
        {"code": code},
    ).scalar_one()


def upsert_contact(conn, email, first_name=None, last_name=None, language=None):
    row = conn.execute(
        text("""
            INSERT INTO contacts (
                email,
                first_name,
                last_name,
                language,
                created_at
            )
            VALUES (
                :email,
                :first_name,
                :last_name,
                :language,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (email)
            DO UPDATE SET
                first_name = COALESCE(
                    NULLIF(contacts.first_name, ''),
                    EXCLUDED.first_name
                ),
                last_name = COALESCE(
                    NULLIF(contacts.last_name, ''),
                    EXCLUDED.last_name
                ),
                language = COALESCE(
                    NULLIF(contacts.language, ''),
                    EXCLUDED.language
                )
            RETURNING id
        """),
        {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "language": language,
        },
    ).first()

    return row[0]


def add_segment(conn, contact_id, segment_id, source):
    conn.execute(
        text("""
            INSERT INTO contact_segments (
                contact_id,
                segment_id,
                source,
                joined_at
            )
            VALUES (
                :contact_id,
                :segment_id,
                :source,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (contact_id, segment_id)
            DO NOTHING
        """),
        {
            "contact_id": contact_id,
            "segment_id": segment_id,
            "source": source,
        },
    )


def add_unsubscribe(conn, email, reason):
    conn.execute(
        text("""
            INSERT INTO unsubscribes (
                email,
                reason,
                created_at
            )
            VALUES (
                :email,
                :reason,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (email)
            DO NOTHING
        """),
        {
            "email": email,
            "reason": reason,
        },
    )


def import_clickfunnels(conn):
    segment_id = get_segment_id(
        conn,
        "clickfunnels_online_business"
    )

    processed = 0
    invalid = 0
    unsubscribed = 0

    with open(
        CLICKFUNNELS_FILE,
        newline="",
        encoding="utf-8-sig"
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:
            email = clean_email(row.get("Email"))

            if not email or "@" not in email:
                invalid += 1
                continue

            first_name = clean_name(row.get("First Name"))
            last_name = clean_name(row.get("Last Name"))

            contact_id = upsert_contact(
                conn,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )

            add_segment(
                conn,
                contact_id,
                segment_id,
                "clickfunnels"
            )

            unsubscribed_at = clean_name(
                row.get("Unsubscribed At")
            )

            if unsubscribed_at:
                add_unsubscribe(
                    conn,
                    email,
                    "Imported ClickFunnels unsubscribe"
                )
                unsubscribed += 1

            processed += 1

    return processed, invalid, unsubscribed


def import_babycare(conn):
    segment_id = get_segment_id(conn, "baby_care")

    processed = 0
    invalid = 0
    skipped_tests = 0

    with open(
        BABYCARE_FILE,
        newline="",
        encoding="utf-8-sig"
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:
            email = clean_email(row.get("email"))

            if not email or "@" not in email:
                invalid += 1
                continue

            test_flag = (row.get("test_flag") or "").strip().upper()

            if test_flag == "YES":
                skipped_tests += 1
                continue

            name = clean_name(row.get("name"))

            language = clean_name(row.get("langs"))

            contact_id = upsert_contact(
                conn,
                email=email,
                first_name=name,
                language=language,
            )

            add_segment(
                conn,
                contact_id,
                segment_id,
                "babycare_landing"
            )

            processed += 1

    return processed, invalid, skipped_tests


with engine.begin() as conn:
    before_contacts = conn.execute(
        text("SELECT COUNT(*) FROM contacts")
    ).scalar_one()

    cf = import_clickfunnels(conn)
    bc = import_babycare(conn)

    after_contacts = conn.execute(
        text("SELECT COUNT(*) FROM contacts")
    ).scalar_one()

    segment_counts = conn.execute(
        text("""
            SELECT
                s.code,
                COUNT(cs.contact_id)
            FROM segments s
            LEFT JOIN contact_segments cs
                ON cs.segment_id = s.id
            GROUP BY s.id, s.code
            ORDER BY s.id
        """)
    ).all()

    unsubscribe_count = conn.execute(
        text("SELECT COUNT(*) FROM unsubscribes")
    ).scalar_one()


print()
print("=== IMPORT COMPLETED ===")
print(f"Contacts before: {before_contacts}")
print(f"Contacts after : {after_contacts}")
print()

print("ClickFunnels:")
print(f"  Processed    : {cf[0]}")
print(f"  Invalid      : {cf[1]}")
print(f"  Unsubscribed : {cf[2]}")
print()

print("Baby Care:")
print(f"  Processed    : {bc[0]}")
print(f"  Invalid      : {bc[1]}")
print(f"  Tests skipped: {bc[2]}")
print()

print("Segments:")
for code, count in segment_counts:
    print(f"  {code}: {count}")

print()
print(f"Global unsubscribes: {unsubscribe_count}")
