#!/usr/bin/env python3
"""
Blockchain sync script for fetching real migration data
"""
import os
from web3 import Web3
from datetime import datetime
from db import insert_migrations, update_sync_metadata, get_last_synced_block

# Configuration
SONIC_RPC_URL = os.environ.get('SONIC_RPC_URL', 'https://rpc.soniclabs.com')
PAL_TOKEN_ADDRESS = os.environ.get('PAL_TOKEN_ADDRESS', '0xe90FE2DE4A415aD48B6DcEc08bA6ae98231948Ac')
MIGRATION_CONTRACT = os.environ.get('MIGRATION_CONTRACT_ADDRESS', '0x99fe40e501151e92f10ac13ea1c06083ee170363')

# ERC20 Transfer event signature
TRANSFER_EVENT_SIGNATURE = Web3.keccak(text='Transfer(address,address,uint256)').hex()

def sync_migrations(start_block=None, end_block=None):
    """Sync migration data from blockchain"""
    print("Connecting to Sonic RPC...")
    w3 = Web3(Web3.HTTPProvider(SONIC_RPC_URL))

    if not w3.is_connected():
        raise Exception("Failed to connect to Sonic RPC")

    print(f"Connected! Chain ID: {w3.eth.chain_id}")

    # Get current block
    current_block = w3.eth.block_number
    print(f"Current block: {current_block}")

    # Determine start block
    if start_block is None:
        try:
            start_block = get_last_synced_block() + 1
        except:
            start_block = 0

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
            # Get Transfer events where 'to' is the migration contract
            filter_params = {
                'fromBlock': batch_start,
                'toBlock': batch_end,
                'address': PAL_TOKEN_ADDRESS,
                'topics': [
                    TRANSFER_EVENT_SIGNATURE,
                    None,  # from (any address)
                    '0x' + MIGRATION_CONTRACT[2:].lower().zfill(64)  # to (migration contract)
                ]
            }

            logs = w3.eth.get_logs(filter_params)
            print(f"Found {len(logs)} migration events")

            for log in logs:
                # Decode event
                from_address = '0x' + log['topics'][1].hex()[26:]
                to_address = '0x' + log['topics'][2].hex()[26:]
                amount_wei = int(log['data'].hex(), 16)
                amount_pal = amount_wei / 10**18

                # Get block timestamp
                block = w3.eth.get_block(log['blockNumber'])
                timestamp = datetime.fromtimestamp(block['timestamp'])

                migration = {
                    'tx_hash': log['transactionHash'].hex(),
                    'from_address': from_address,
                    'to_address': to_address,
                    'amount_pal': amount_pal,
                    'block_number': log['blockNumber'],
                    'block_timestamp': block['timestamp'],
                    'timestamp': timestamp,
                    'log_index': log['logIndex'],
                    'source': 'sonic'  # Detect if bridged from Ethereum in future
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
