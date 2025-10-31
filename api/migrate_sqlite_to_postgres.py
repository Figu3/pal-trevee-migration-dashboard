#!/usr/bin/env python3
"""
Migrate data from local SQLite database to Vercel Postgres
"""
import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime

# Paths
SQLITE_DB = "../data/migrations.db"
POSTGRES_URL = os.environ.get('POSTGRES_URL')

if not POSTGRES_URL:
    print("Error: POSTGRES_URL environment variable not set")
    exit(1)

def migrate_data():
    """Copy all migrations from SQLite to Postgres"""
    print(f"Connecting to SQLite database: {SQLITE_DB}")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    print(f"Connecting to Postgres database...")
    pg_conn = psycopg2.connect(POSTGRES_URL)
    pg_cursor = pg_conn.cursor()

    # Get all migrations from SQLite
    print("Fetching migrations from SQLite...")
    sqlite_cursor.execute("""
        SELECT
            tx_hash, from_address, to_address, amount_pal,
            block_number, block_timestamp, timestamp, log_index, source
        FROM migrations
        ORDER BY block_number ASC
    """)

    migrations = sqlite_cursor.fetchall()
    print(f"Found {len(migrations)} migrations in SQLite")

    # Clear existing data in Postgres (optional - comment out if you want to keep existing)
    print("Clearing existing Postgres data...")
    pg_cursor.execute("DELETE FROM migrations")
    pg_conn.commit()

    # Prepare data for batch insert
    print("Inserting migrations into Postgres...")
    insert_query = """
        INSERT INTO migrations
        (tx_hash, from_address, to_address, amount_pal, block_number,
         block_timestamp, timestamp, log_index, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (tx_hash) DO NOTHING
    """

    data = []
    for row in migrations:
        # Parse timestamp string back to datetime object
        timestamp_str = row['timestamp']
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = None
        else:
            timestamp = None

        data.append((
            row['tx_hash'],
            row['from_address'],
            row['to_address'],
            float(row['amount_pal']),
            row['block_number'],
            row['block_timestamp'],
            timestamp,
            row['log_index'],
            row['source'] or 'unknown'
        ))

    # Batch insert
    execute_batch(pg_cursor, insert_query, data, page_size=100)
    pg_conn.commit()

    # Verify count
    pg_cursor.execute("SELECT COUNT(*) FROM migrations")
    pg_count = pg_cursor.fetchone()[0]

    print(f"\n✅ Migration complete!")
    print(f"   SQLite: {len(migrations)} migrations")
    print(f"   Postgres: {pg_count} migrations")

    # Update sync metadata
    sqlite_cursor.execute("SELECT MAX(block_number) FROM migrations")
    max_block = sqlite_cursor.fetchone()[0]

    if max_block:
        pg_cursor.execute("""
            INSERT INTO sync_metadata (id, last_synced_block, last_sync_time)
            VALUES (1, %s, NOW())
            ON CONFLICT (id) DO UPDATE
            SET last_synced_block = %s, last_sync_time = NOW()
        """, (max_block, max_block))
        pg_conn.commit()
        print(f"   Last synced block: {max_block}")

    # Close connections
    sqlite_cursor.close()
    sqlite_conn.close()
    pg_cursor.close()
    pg_conn.close()

    print("\n✅ All data successfully migrated to Postgres!")

if __name__ == '__main__':
    migrate_data()
