#!/usr/bin/env python3
"""
Main synchronization script for PAL to TREVEE migration tracker
Fetches new migration data and updates the database
"""

import sys
import time
from datetime import datetime
from migration_tracker import MigrationTracker
from database import MigrationDatabase
from config import START_BLOCK


def sync_migrations(full_sync: bool = False):
    """
    Sync migration data from blockchain

    Args:
        full_sync: If True, sync from START_BLOCK. If False, sync from last synced block.
    """
    print("=" * 60)
    print("PAL to TREVEE Migration Synchronization")
    print("=" * 60)

    # Initialize tracker and database
    tracker = MigrationTracker()
    db = MigrationDatabase()

    # Determine starting block
    if full_sync:
        print("\nPerforming FULL sync from genesis...")
        from_block = START_BLOCK

        # Try to find contract deployment block for efficiency
        try:
            deployment_block = tracker.get_contract_deployment_block()
            if deployment_block > from_block:
                from_block = deployment_block
                print(f"Starting from contract deployment block: {deployment_block}")
        except Exception as e:
            print(f"Could not determine deployment block: {e}")

    else:
        last_synced = db.get_last_synced_block()
        from_block = last_synced + 1 if last_synced > 0 else START_BLOCK
        print(f"\nPerforming incremental sync from block {from_block}...")

    # Get current block
    try:
        current_block = tracker.rpc.get_block_number()
        print(f"Current blockchain height: {current_block}")
    except Exception as e:
        print(f"Error getting current block: {e}")
        return False

    if from_block > current_block:
        print("Already up to date!")
        return True

    print(f"\nScanning {current_block - from_block + 1} blocks for migrations...")

    # Fetch migration events
    try:
        start_time = time.time()
        events = tracker.get_migration_events(from_block, current_block)
        elapsed = time.time() - start_time

        print(f"\nFound {len(events)} migration events in {elapsed:.2f} seconds")

        if not events:
            print("No new migrations found.")
            db.update_sync_metadata(current_block)
            return True

        # Analyze transaction sources (sample some to avoid too many RPC calls)
        print("\nAnalyzing transaction sources...")
        sample_size = min(len(events), 50)  # Analyze first 50 transactions
        for i, event in enumerate(events[:sample_size]):
            if i % 10 == 0:
                print(f"  Analyzed {i}/{sample_size} transactions...")

            source = tracker.analyze_transaction_source(event["tx_hash"])
            event["source"] = source
            time.sleep(0.1)  # Rate limiting

        print(f"  Analyzed {sample_size}/{len(events)} transactions")

        # Insert into database
        print("\nInserting migrations into database...")
        inserted = db.insert_migrations_batch(events)
        print(f"Successfully inserted {inserted} migrations")

        # Update sync metadata
        db.update_sync_metadata(current_block)

        # Save daily snapshot
        print("Saving daily snapshot...")
        db.save_daily_snapshot()

        # Print summary
        stats = db.get_statistics()
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Total Unique Addresses: {stats['unique_addresses']:,}")
        print(f"Total Migrations: {stats['total_migrations']:,}")
        print(f"Total PAL Migrated: {stats['total_pal_migrated']:,.2f}")
        print(f"Average Migration Size: {stats['average_migration_size']:,.2f} PAL")
        print(f"Median Migration Size: {stats['median_migration_size']:,.2f} PAL")
        print("=" * 60)

        # Show top 5 migrations
        if stats['top_migrations']:
            print("\nTop 5 Largest Migrations:")
            for i, migration in enumerate(stats['top_migrations'][:5], 1):
                print(f"  {i}. {migration['amount_pal']:,.2f} PAL from {migration['from_address'][:10]}...")

        return True

    except Exception as e:
        print(f"\nError during synchronization: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_migration_deadline():
    """Check if there's a migration deadline"""
    print("\nChecking for migration deadline...")

    tracker = MigrationTracker()

    deadline_info = tracker.check_migration_deadline()

    if deadline_info:
        print(f"Migration Deadline Found:")
        print(f"  Date: {deadline_info['deadline_datetime']}")
        print(f"  Time Remaining: {deadline_info['time_remaining'] / 86400:.1f} days")
    else:
        print("  No deadline found in contract (or contract does not expose this information)")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Sync PAL to TREVEE migration data")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Perform full sync from genesis"
    )
    parser.add_argument(
        "--check-deadline",
        action="store_true",
        help="Check migration deadline"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuous sync (every 5 minutes)"
    )

    args = parser.parse_args()

    if args.check_deadline:
        check_migration_deadline()
        return

    if args.continuous:
        print("Starting continuous sync mode (Ctrl+C to stop)...")
        while True:
            try:
                sync_migrations(full_sync=False)
                print(f"\nNext sync in 5 minutes... (Press Ctrl+C to stop)")
                time.sleep(300)  # 5 minutes
            except KeyboardInterrupt:
                print("\nStopping continuous sync...")
                break
    else:
        sync_migrations(full_sync=args.full)


if __name__ == "__main__":
    main()
