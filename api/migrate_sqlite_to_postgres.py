#!/usr/bin/env python3
"""
Migrate data from local SQLite database to Vercel Postgres

Usage:
  python3 migrate_sqlite_to_postgres.py                  # Safe mode (no delete)
  python3 migrate_sqlite_to_postgres.py --force          # Delete existing data first
  python3 migrate_sqlite_to_postgres.py --dry-run        # Show what would be done
"""
import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
import argparse

# Get script directory for platform-independent paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB = os.path.join(SCRIPT_DIR, "..", "data", "migrations.db")


def migrate_data(force_delete=False, dry_run=False):
    """
    Copy all migrations from SQLite to Postgres

    Args:
        force_delete: If True, deletes existing Postgres data before migration
        dry_run: If True, shows what would be done without making changes
    """
    # Check for Postgres URL
    postgres_url = os.environ.get('POSTGRES_URL')
    if not postgres_url:
        print("\n❌ Error: POSTGRES_URL environment variable not set")
        print("Set it with: export POSTGRES_URL='your_postgres_connection_string'")
        sys.exit(1)

    sqlite_conn = None
    pg_conn = None

    try:
        # Connect to SQLite
        print(f"Connecting to SQLite database: {SQLITE_DB}")
        if not os.path.exists(SQLITE_DB):
            print(f"Error: SQLite database not found at {SQLITE_DB}")
            sys.exit(1)

        sqlite_conn = sqlite3.connect(SQLITE_DB)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()

        # Connect to Postgres
        print(f"Connecting to Postgres database...")
        pg_conn = psycopg2.connect(postgres_url)
        pg_cursor = pg_conn.cursor()

        # Get migration count from SQLite
        print("\nFetching migrations from SQLite...")
        sqlite_cursor.execute("""
            SELECT
                tx_hash, from_address, to_address, amount_pal,
                block_number, block_timestamp, timestamp, log_index, source
            FROM migrations
            ORDER BY block_number ASC
        """)

        migrations = sqlite_cursor.fetchall()
        print(f"✓ Found {len(migrations)} migrations in SQLite")

        # Get existing count from Postgres
        pg_cursor.execute("SELECT COUNT(*) FROM migrations")
        existing_count = pg_cursor.fetchone()[0]
        print(f"✓ Found {existing_count} existing migrations in Postgres")

        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be made")
            print(f"   Would migrate {len(migrations)} migrations from SQLite to Postgres")
            if force_delete:
                print(f"   Would DELETE {existing_count} existing records first")
            else:
                print(f"   Would use UPSERT (ON CONFLICT DO NOTHING)")
            return

        # Handle existing data
        if force_delete:
            print(f"\n⚠️  WARNING: About to DELETE all {existing_count} existing migrations from Postgres!")
            confirm = input("Type 'DELETE' to confirm: ")
            if confirm != 'DELETE':
                print("Aborted.")
                return

            print("Clearing existing Postgres data...")
            pg_cursor.execute("DELETE FROM migrations")
            pg_conn.commit()
            print("✓ Existing data cleared")
        else:
            print("\n✓ Running in safe mode - will skip duplicates (ON CONFLICT DO NOTHING)")

        # Prepare data for batch insert
        print(f"\nInserting {len(migrations)} migrations into Postgres...")
        insert_query = """
            INSERT INTO migrations
            (tx_hash, from_address, to_address, amount_pal, block_number,
             block_timestamp, timestamp, log_index, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tx_hash) DO NOTHING
        """

        data = []
        failed_parses = 0

        for row in migrations:
            # Parse timestamp string back to datetime object
            timestamp_str = row['timestamp']
            timestamp = None

            if timestamp_str:
                try:
                    # Handle ISO format timestamps
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError) as e:
                    failed_parses += 1
                    if failed_parses <= 3:  # Only show first 3 errors
                        print(f"  Warning: Failed to parse timestamp '{timestamp_str}': {e}")
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

        if failed_parses > 3:
            print(f"  ... and {failed_parses - 3} more timestamp parse warnings")

        # Batch insert
        execute_batch(pg_cursor, insert_query, data, page_size=100)
        pg_conn.commit()
        print("✓ Batch insert completed")

        # Verify migration
        print("\n📊 Verification:")
        pg_cursor.execute("SELECT COUNT(*) FROM migrations")
        final_count = pg_cursor.fetchone()[0]

        print(f"   SQLite migrations:  {len(migrations)}")
        print(f"   Postgres migrations: {final_count}")

        if force_delete and final_count != len(migrations):
            print(f"   ⚠️  WARNING: Count mismatch! Expected {len(migrations)} but got {final_count}")
        else:
            print(f"   ✓ Migration successful!")

        # Update sync metadata
        sqlite_cursor.execute("SELECT MAX(block_number) FROM migrations")
        max_block = sqlite_cursor.fetchone()[0]

        if max_block:
            print(f"\nUpdating sync metadata...")
            pg_cursor.execute("""
                INSERT INTO sync_metadata (id, last_synced_block, last_sync_time)
                VALUES (1, %s, NOW())
                ON CONFLICT (id) DO UPDATE
                SET last_synced_block = EXCLUDED.last_synced_block,
                    last_sync_time = NOW()
            """, (max_block,))
            pg_conn.commit()
            print(f"✓ Last synced block updated to: {max_block}")

        # Show statistics
        pg_cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT from_address) as unique_addresses,
                SUM(amount_pal) as total_pal
            FROM migrations
        """)
        stats = pg_cursor.fetchone()

        print(f"\n📈 Final Statistics:")
        print(f"   Total migrations: {stats[0]}")
        print(f"   Unique addresses: {stats[1]}")
        print(f"   Total PAL: {stats[2]:,.2f}")

        print("\n✅ Migration completed successfully!")

    except psycopg2.Error as e:
        print(f"\n❌ Postgres error: {e}")
        if pg_conn:
            pg_conn.rollback()
        sys.exit(1)
    except sqlite3.Error as e:
        print(f"\n❌ SQLite error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Always close connections
        if sqlite_conn:
            sqlite_conn.close()
            print("\n✓ SQLite connection closed")
        if pg_conn:
            pg_conn.close()
            print("✓ Postgres connection closed")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Migrate migration data from SQLite to Postgres',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Safe mode - skip duplicates
  python3 migrate_sqlite_to_postgres.py

  # Delete existing data first (dangerous!)
  python3 migrate_sqlite_to_postgres.py --force

  # Preview what would happen
  python3 migrate_sqlite_to_postgres.py --dry-run
        """
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Delete all existing Postgres data before migration (DANGEROUS!)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making any changes'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("SQLite to Postgres Migration Tool")
    print("=" * 60)

    migrate_data(force_delete=args.force, dry_run=args.dry_run)
