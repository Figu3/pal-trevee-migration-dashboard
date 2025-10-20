#!/usr/bin/env python3
"""
Demo Data Generator for Testing the Dashboard
Creates sample migration data to test the dashboard without waiting for real migrations
"""

import random
from datetime import datetime, timedelta
from database import MigrationDatabase


def generate_demo_data(num_migrations=200, num_addresses=50):
    """
    Generate demo migration data

    Args:
        num_migrations: Number of migrations to generate
        num_addresses: Number of unique addresses to use
    """
    print(f"Generating {num_migrations} demo migrations from {num_addresses} unique addresses...")

    db = MigrationDatabase()

    # Generate random addresses
    addresses = [
        f"0x{''.join(random.choices('0123456789abcdef', k=40))}"
        for _ in range(num_addresses)
    ]

    # Base timestamp (30 days ago)
    base_time = datetime.now() - timedelta(days=30)

    migrations = []

    for i in range(num_migrations):
        # Random address (some addresses migrate multiple times)
        from_address = random.choice(addresses)

        # Random amount (log-normal distribution for realistic migration sizes)
        amount_pal = random.lognormvariate(8, 2)  # Mean ~3000 PAL, varied distribution

        # Random timestamp (spread over 30 days)
        timestamp = base_time + timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

        # Random block number
        block_number = 49997769 + i * random.randint(1, 100)

        # Random source
        source = random.choices(
            ['sonic', 'ethereum', 'unknown'],
            weights=[0.6, 0.3, 0.1]  # 60% Sonic, 30% Ethereum, 10% Unknown
        )[0]

        # Cap amount to avoid SQLite integer overflow (max safe: 2^63-1)
        amount_wei = min(int(amount_pal * 10**18), 2**63 - 1)

        migration = {
            "tx_hash": f"0x{''.join(random.choices('0123456789abcdef', k=64))}",
            "from_address": from_address,
            "to_address": "0x99fe40e501151e92f10ac13ea1c06083ee170363",
            "amount": amount_wei,
            "amount_pal": amount_pal,
            "block_number": block_number,
            "block_timestamp": int(timestamp.timestamp()),
            "timestamp": timestamp,
            "log_index": i,
            "source": source
        }

        migrations.append(migration)

    # Sort by timestamp
    migrations.sort(key=lambda x: x["timestamp"])

    # Insert into database
    print("Inserting demo data into database...")
    inserted = db.insert_migrations_batch(migrations)
    print(f"Successfully inserted {inserted} demo migrations")

    # Update sync metadata
    db.update_sync_metadata(migrations[-1]["block_number"])

    # Save snapshot
    db.save_daily_snapshot()

    # Print statistics
    stats = db.get_statistics()
    print("\n" + "=" * 60)
    print("DEMO DATA SUMMARY")
    print("=" * 60)
    print(f"Total Unique Addresses: {stats['unique_addresses']}")
    print(f"Total Migrations: {stats['total_migrations']}")
    print(f"Total PAL Migrated: {stats['total_pal_migrated']:,.2f}")
    print(f"Average Migration Size: {stats['average_migration_size']:,.2f} PAL")
    print(f"Median Migration Size: {stats['median_migration_size']:,.2f} PAL")
    print("=" * 60)

    print("\nTop 5 Largest Migrations:")
    for i, migration in enumerate(stats['top_migrations'][:5], 1):
        print(f"  {i}. {migration['amount_pal']:,.2f} PAL from {migration['from_address'][:10]}...")

    print("\nDemo data generation complete!")
    print("You can now start the API server and view the dashboard.")


def clear_database():
    """Clear all data from the database"""
    import os
    from config import DB_PATH

    db_file = DB_PATH
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"Deleted database: {db_file}")
    else:
        print(f"Database file not found: {db_file}")

    # Reinitialize
    db = MigrationDatabase()
    print("Database reinitialized")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate demo migration data")
    parser.add_argument(
        "--migrations",
        type=int,
        default=200,
        help="Number of migrations to generate (default: 200)"
    )
    parser.add_argument(
        "--addresses",
        type=int,
        default=50,
        help="Number of unique addresses (default: 50)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing database before generating"
    )

    args = parser.parse_args()

    if args.clear:
        clear_database()

    generate_demo_data(args.migrations, args.addresses)
