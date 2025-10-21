#!/usr/bin/env python3
"""
Blockchain sync script for fetching real migration data
"""
import os
from web3 import Web3
from datetime import datetime
from db import insert_migrations, update_sync_metadata, get_last_synced_block

# Load environment variables from .env.local if available
try:
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    load_dotenv()  # Also try regular .env
except ImportError:
    pass  # python-dotenv not installed, rely on environment variables

# Configuration
SONIC_RPC_URL = os.environ.get('SONIC_RPC_URL', 'https://rpc.soniclabs.com')
PAL_TOKEN_ADDRESS = Web3.to_checksum_address(os.environ.get('PAL_TOKEN_ADDRESS', '0xe90FE2DE4A415aD48B6DcEc08bA6ae98231948Ac'))
MIGRATION_CONTRACT = Web3.to_checksum_address(os.environ.get('MIGRATION_CONTRACT_ADDRESS', '0x99fe40e501151e92f10ac13ea1c06083ee170363'))

# Migration contract was deployed around block 51300000
# Start from here by default to avoid scanning millions of empty blocks
DEFAULT_START_BLOCK = 51300000

# Migration event signatures (from analyzing actual transactions)
MIGRATION_EVENT_1 = '0xc38977ae45aaee7a70eedc8ae085f4931e040352f48f62a1bb9d1712abad1c24'
MIGRATION_EVENT_2 = '0x877c1d3e63eecac7ca6a72be1dc0076327918516b7be8192d2da3cb32f201670'

def sync_migrations(start_block=None, end_block=None):
    """Sync migration data from blockchain"""
    print("Connecting to Sonic RPC...")
    w3 = Web3(Web3.HTTPProvider(SONIC_RPC_URL))

    try:
        # Test connection
        w3.eth.block_number
        print("Connected successfully!")
    except Exception as e:
        raise Exception(f"Failed to connect to Sonic RPC: {e}")

    print(f"Connected! Chain ID: {w3.eth.chain_id}")

    # Get current block
    current_block = w3.eth.block_number
    print(f"Current block: {current_block}")

    # Determine start block
    if start_block is None:
        try:
            last_synced = get_last_synced_block()
            start_block = last_synced + 1 if last_synced > 0 else DEFAULT_START_BLOCK
        except:
            start_block = DEFAULT_START_BLOCK

    if end_block is None:
        end_block = current_block

    print(f"Syncing from block {start_block} to {end_block}")

    # Fetch transfer events to migration contract
    batch_size = 10000
    all_migrations = []

    for batch_start in range(start_block, end_block + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end_block)

        print(f"Fetching blocks {batch_start} to {batch_end}...")

        try:
            # Get migration events from the migration contract
            filter_params = {
                'fromBlock': batch_start,
                'toBlock': batch_end,
                'address': MIGRATION_CONTRACT,
                'topics': [[MIGRATION_EVENT_1, MIGRATION_EVENT_2]]  # Either event type
            }

            logs = w3.eth.get_logs(filter_params)
            print(f"Found {len(logs)} migration events")

            for log in logs:
                # Decode event - topics[1] is the migrator address
                from_address = '0x' + log['topics'][1].hex()[26:]

                # Amount is in the data field (first 32 bytes)
                amount_wei = int(log['data'].hex()[:66], 16)
                amount_pal = amount_wei / 10**18

                # Get block timestamp
                block = w3.eth.get_block(log['blockNumber'])
                timestamp = datetime.fromtimestamp(block['timestamp'])

                migration = {
                    'tx_hash': log['transactionHash'].hex(),
                    'from_address': from_address,
                    'to_address': MIGRATION_CONTRACT,
                    'amount_pal': amount_pal,
                    'block_number': log['blockNumber'],
                    'block_timestamp': block['timestamp'],
                    'timestamp': timestamp,
                    'log_index': log['logIndex'],
                    'source': 'sonic'
                }

                all_migrations.append(migration)

        except Exception as e:
            print(f"Error fetching batch {batch_start}-{batch_end}: {e}")
            continue

    # Insert into database
    if all_migrations:
        print(f"\nInserting {len(all_migrations)} migrations into database...")
        inserted = insert_migrations(all_migrations)
        print(f"Inserted {inserted} new migrations")

        # Update sync metadata
        update_sync_metadata(end_block)
        print(f"Updated sync metadata to block {end_block}")
    else:
        print("No migrations found in this range")

    return len(all_migrations)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Sync migration data from Sonic blockchain')
    parser.add_argument('--start', type=int, help='Start block number')
    parser.add_argument('--end', type=int, help='End block number')
    parser.add_argument('--full', action='store_true', help='Full sync from genesis')

    args = parser.parse_args()

    start = 0 if args.full else args.start
    end = args.end

    count = sync_migrations(start, end)
    print(f"\n✅ Sync complete! Processed {count} migrations")
