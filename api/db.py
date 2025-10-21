"""
Database module for Vercel Postgres
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

def get_db_connection():
    """Get database connection"""
    database_url = os.environ.get('POSTGRES_URL')
    if not database_url:
        raise Exception("POSTGRES_URL environment variable not set")

    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

def init_database():
    """Initialize database schema"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Migrations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id SERIAL PRIMARY KEY,
            tx_hash TEXT UNIQUE NOT NULL,
            from_address TEXT NOT NULL,
            to_address TEXT NOT NULL,
            amount_pal NUMERIC NOT NULL,
            block_number INTEGER NOT NULL,
            block_timestamp INTEGER,
            timestamp TIMESTAMP,
            log_index INTEGER,
            source TEXT DEFAULT 'unknown',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_from_address ON migrations(from_address);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON migrations(timestamp);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_block_number ON migrations(block_number);
    """)

    # Sync metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_metadata (
            id SERIAL PRIMARY KEY,
            last_synced_block INTEGER NOT NULL,
            last_sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

def get_statistics():
    """Get summary statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total_migrations,
            COUNT(DISTINCT from_address) as unique_addresses,
            SUM(amount_pal) as total_pal_migrated,
            AVG(amount_pal) as average_migration,
            MIN(timestamp) as first_migration,
            MAX(timestamp) as last_migration
        FROM migrations
    """)

    stats = cursor.fetchone()

    # Get median
    cursor.execute("""
        SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount_pal) as median
        FROM migrations
    """)
    median_result = cursor.fetchone()

    # Get top migrations
    cursor.execute("""
        SELECT tx_hash, from_address, amount_pal, timestamp, block_number, source
        FROM migrations
        ORDER BY amount_pal DESC
        LIMIT 10
    """)
    top_migrations = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "total_migrations": stats['total_migrations'] or 0,
        "unique_addresses": stats['unique_addresses'] or 0,
        "total_pal_migrated": float(stats['total_pal_migrated'] or 0),
        "average_migration": float(stats['average_migration'] or 0),
        "median_migration": float(median_result['median'] or 0) if median_result else 0,
        "first_migration": stats['first_migration'].isoformat() if stats['first_migration'] else None,
        "last_migration": stats['last_migration'].isoformat() if stats['last_migration'] else None,
        "top_migrations": [dict(m) for m in top_migrations]
    }

def get_daily_stats():
    """Get daily migration statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            DATE(timestamp) as date,
            COUNT(*) as count,
            SUM(amount_pal) as amount
        FROM migrations
        GROUP BY DATE(timestamp)
        ORDER BY date
    """)

    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return [{"date": r['date'].isoformat(), "count": r['count'], "amount": float(r['amount'])} for r in results]

def get_timeline(limit=50):
    """Get migration timeline"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tx_hash, from_address, amount_pal, timestamp, block_number, source
        FROM migrations
        ORDER BY timestamp DESC
        LIMIT %s
    """, (limit,))

    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return [{
        **dict(m),
        'timestamp': m['timestamp'].isoformat() if m['timestamp'] else None
    } for m in results]

def lookup_address(address):
    """Look up migrations for address"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tx_hash, from_address, amount_pal, timestamp, block_number, source
        FROM migrations
        WHERE LOWER(from_address) = LOWER(%s)
        ORDER BY timestamp DESC
    """, (address,))

    results = cursor.fetchall()

    total = sum(float(m['amount_pal']) for m in results)

    cursor.close()
    conn.close()

    return {
        "address": address,
        "migrations": [{
            **dict(m),
            'timestamp': m['timestamp'].isoformat() if m['timestamp'] else None
        } for m in results],
        "total_amount": total,
        "count": len(results)
    }

def get_large_migrations(threshold):
    """Get migrations above threshold"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tx_hash, from_address, amount_pal, timestamp, block_number, source
        FROM migrations
        WHERE amount_pal > %s
        ORDER BY amount_pal DESC
    """, (threshold,))

    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return [{
        **dict(m),
        'timestamp': m['timestamp'].isoformat() if m['timestamp'] else None
    } for m in results]

def get_last_synced_block():
    """Get last synced block number"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT last_synced_block
        FROM sync_metadata
        ORDER BY id DESC
        LIMIT 1
    """)

    result = cursor.fetchone()
    cursor.close()
    conn.close()

    return result['last_synced_block'] if result else 0

def insert_migrations(migrations):
    """Insert migrations into database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    inserted = 0
    for m in migrations:
        try:
            cursor.execute("""
                INSERT INTO migrations
                (tx_hash, from_address, to_address, amount_pal, block_number, block_timestamp, timestamp, log_index, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tx_hash) DO NOTHING
            """, (
                m['tx_hash'],
                m['from_address'],
                m['to_address'],
                m['amount_pal'],
                m['block_number'],
                m.get('block_timestamp'),
                m.get('timestamp'),
                m.get('log_index'),
                m.get('source', 'unknown')
            ))
            if cursor.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"Error inserting migration {m['tx_hash']}: {e}")
            continue

    conn.commit()
    cursor.close()
    conn.close()

    return inserted

def update_sync_metadata(block_number):
    """Update sync metadata"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO sync_metadata (last_synced_block)
        VALUES (%s)
    """, (block_number,))

    conn.commit()
    cursor.close()
    conn.close()
