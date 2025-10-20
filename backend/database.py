"""
Database module for caching migration data
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from config import DB_PATH


class MigrationDatabase:
    """SQLite database for storing migration data"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        return conn

    def init_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Migrations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_hash TEXT UNIQUE NOT NULL,
                from_address TEXT NOT NULL,
                to_address TEXT NOT NULL,
                amount INTEGER NOT NULL,
                amount_pal REAL NOT NULL,
                block_number INTEGER NOT NULL,
                block_timestamp INTEGER,
                timestamp TEXT,
                log_index INTEGER,
                source TEXT DEFAULT 'unknown',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_from_address
            ON migrations(from_address)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_block_number
            ON migrations(block_number)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON migrations(block_timestamp)
        """)

        # Metadata table for tracking sync status
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_metadata (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_synced_block INTEGER,
                last_sync_time TEXT,
                total_migrations INTEGER DEFAULT 0,
                total_pal_migrated REAL DEFAULT 0
            )
        """)

        # Insert default metadata if not exists
        cursor.execute("""
            INSERT OR IGNORE INTO sync_metadata (id, last_synced_block, last_sync_time)
            VALUES (1, 0, NULL)
        """)

        # Snapshots table for historical tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT UNIQUE NOT NULL,
                total_migrations INTEGER,
                total_pal_migrated REAL,
                unique_addresses INTEGER,
                average_migration_size REAL,
                median_migration_size REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def insert_migration(self, migration: Dict) -> bool:
        """Insert a migration record"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO migrations
                (tx_hash, from_address, to_address, amount, amount_pal,
                 block_number, block_timestamp, timestamp, log_index, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                migration.get("tx_hash"),
                migration.get("from_address"),
                migration.get("to_address"),
                migration.get("amount"),
                migration.get("amount_pal"),
                migration.get("block_number"),
                migration.get("block_timestamp"),
                migration.get("timestamp").isoformat() if migration.get("timestamp") else None,
                migration.get("log_index"),
                migration.get("source", "unknown")
            ))

            conn.commit()
            return True

        except Exception as e:
            print(f"Error inserting migration: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    def insert_migrations_batch(self, migrations: List[Dict]) -> int:
        """Insert multiple migrations in batch"""
        conn = self.get_connection()
        cursor = conn.cursor()
        inserted = 0

        try:
            for migration in migrations:
                cursor.execute("""
                    INSERT OR REPLACE INTO migrations
                    (tx_hash, from_address, to_address, amount, amount_pal,
                     block_number, block_timestamp, timestamp, log_index, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    migration.get("tx_hash"),
                    migration.get("from_address"),
                    migration.get("to_address"),
                    migration.get("amount"),
                    migration.get("amount_pal"),
                    migration.get("block_number"),
                    migration.get("block_timestamp"),
                    migration.get("timestamp").isoformat() if migration.get("timestamp") else None,
                    migration.get("log_index"),
                    migration.get("source", "unknown")
                ))
                inserted += 1

            conn.commit()
            return inserted

        except Exception as e:
            print(f"Error inserting migrations batch: {e}")
            conn.rollback()
            return 0

        finally:
            conn.close()

    def get_all_migrations(self) -> List[Dict]:
        """Get all migrations"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM migrations
            ORDER BY block_number ASC, log_index ASC
        """)

        migrations = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return migrations

    def get_migrations_by_address(self, address: str) -> List[Dict]:
        """Get migrations for a specific address"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM migrations
            WHERE from_address = ?
            ORDER BY block_number ASC
        """, (address.lower(),))

        migrations = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return migrations

    def get_last_synced_block(self) -> int:
        """Get the last synced block number"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT last_synced_block FROM sync_metadata WHERE id = 1")
        result = cursor.fetchone()
        conn.close()

        return result["last_synced_block"] if result else 0

    def update_sync_metadata(self, last_block: int):
        """Update sync metadata"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE sync_metadata
            SET last_synced_block = ?,
                last_sync_time = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (last_block,))

        conn.commit()
        conn.close()

    def get_statistics(self) -> Dict:
        """Get migration statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Total migrations
        cursor.execute("SELECT COUNT(*) as total FROM migrations")
        total_migrations = cursor.fetchone()["total"]

        # Total PAL migrated
        cursor.execute("SELECT SUM(amount_pal) as total FROM migrations")
        total_pal = cursor.fetchone()["total"] or 0

        # Unique addresses
        cursor.execute("SELECT COUNT(DISTINCT from_address) as total FROM migrations")
        unique_addresses = cursor.fetchone()["total"]

        # Average migration size
        cursor.execute("SELECT AVG(amount_pal) as avg FROM migrations")
        avg_migration = cursor.fetchone()["avg"] or 0

        # Median migration size (approximation)
        cursor.execute("""
            SELECT amount_pal FROM migrations
            ORDER BY amount_pal
            LIMIT 1 OFFSET (SELECT COUNT(*) FROM migrations) / 2
        """)
        median_result = cursor.fetchone()
        median_migration = median_result["amount_pal"] if median_result else 0

        # Top 10 migrations
        cursor.execute("""
            SELECT from_address, amount_pal, tx_hash, timestamp
            FROM migrations
            ORDER BY amount_pal DESC
            LIMIT 10
        """)
        top_migrations = [dict(row) for row in cursor.fetchall()]

        # Distribution by source
        cursor.execute("""
            SELECT source, COUNT(*) as count, SUM(amount_pal) as total_pal
            FROM migrations
            GROUP BY source
        """)
        source_distribution = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            "total_migrations": total_migrations,
            "total_pal_migrated": total_pal,
            "unique_addresses": unique_addresses,
            "average_migration_size": avg_migration,
            "median_migration_size": median_migration,
            "top_migrations": top_migrations,
            "source_distribution": source_distribution
        }

    def get_daily_stats(self) -> List[Dict]:
        """Get daily migration statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                DATE(timestamp) as date,
                COUNT(*) as migrations,
                SUM(amount_pal) as total_pal,
                COUNT(DISTINCT from_address) as unique_addresses
            FROM migrations
            WHERE timestamp IS NOT NULL
            GROUP BY DATE(timestamp)
            ORDER BY date ASC
        """)

        stats = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return stats

    def save_daily_snapshot(self):
        """Save a daily snapshot of current statistics"""
        stats = self.get_statistics()

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO daily_snapshots
            (snapshot_date, total_migrations, total_pal_migrated,
             unique_addresses, average_migration_size, median_migration_size)
            VALUES (DATE('now'), ?, ?, ?, ?, ?)
        """, (
            stats["total_migrations"],
            stats["total_pal_migrated"],
            stats["unique_addresses"],
            stats["average_migration_size"],
            stats["median_migration_size"]
        ))

        conn.commit()
        conn.close()

    def export_to_json(self, filepath: str):
        """Export all migrations to JSON file"""
        migrations = self.get_all_migrations()

        with open(filepath, 'w') as f:
            json.dump(migrations, f, indent=2, default=str)

    def export_to_csv(self, filepath: str):
        """Export all migrations to CSV file"""
        import csv

        migrations = self.get_all_migrations()

        if not migrations:
            return

        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=migrations[0].keys())
            writer.writeheader()
            writer.writerows(migrations)
