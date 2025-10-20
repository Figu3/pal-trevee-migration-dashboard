"""
Migration Tracker - Fetches and processes PAL to TREVEE migration data
"""

import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from rpc_client import SonicRPCClient
from config import (
    MIGRATION_CONTRACT_ADDRESS,
    PAL_TOKEN_ADDRESS,
    START_BLOCK,
    BATCH_SIZE
)


class MigrationTracker:
    """Tracks PAL to TREVEE migrations on Sonic blockchain"""

    # ERC20 Transfer event signature
    TRANSFER_EVENT_SIGNATURE = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

    def __init__(self):
        self.rpc = SonicRPCClient()

    def get_migration_events(self, from_block: int, to_block: Optional[int] = None) -> List[Dict]:
        """
        Fetch all PAL token transfers to the migration contract

        Args:
            from_block: Starting block number
            to_block: Ending block number (None = latest)

        Returns:
            List of migration events with parsed data
        """
        if to_block is None:
            to_block = self.rpc.get_block_number()

        print(f"Scanning blocks {from_block} to {to_block}...")

        all_events = []
        current_block = from_block

        while current_block <= to_block:
            batch_end = min(current_block + BATCH_SIZE - 1, to_block)

            print(f"Fetching logs from block {current_block} to {batch_end}...")

            try:
                # Get Transfer events where 'to' address is the migration contract
                # Topics: [0] = Transfer signature, [1] = from address, [2] = to address
                logs = self.rpc.get_logs(
                    from_block=current_block,
                    to_block=batch_end,
                    address=PAL_TOKEN_ADDRESS,
                    topics=[
                        self.TRANSFER_EVENT_SIGNATURE,
                        None,  # Any sender
                        self._address_to_topic(MIGRATION_CONTRACT_ADDRESS)  # To migration contract
                    ]
                )

                print(f"Found {len(logs)} transfer events in this batch")

                # Process each log
                for log in logs:
                    event = self._parse_transfer_event(log)
                    if event:
                        all_events.append(event)

            except Exception as e:
                print(f"Error fetching logs for blocks {current_block}-{batch_end}: {e}")

            current_block = batch_end + 1
            time.sleep(0.1)  # Rate limiting

        return all_events

    def _address_to_topic(self, address: str) -> str:
        """Convert address to indexed topic format (32 bytes padded)"""
        # Remove 0x prefix if present, convert to lowercase
        addr = address.lower().replace("0x", "")
        # Pad to 64 characters (32 bytes)
        return "0x" + addr.zfill(64)

    def _parse_transfer_event(self, log: Dict) -> Optional[Dict]:
        """Parse a Transfer event log into structured data"""
        try:
            topics = log.get("topics", [])
            data = log.get("data", "0x0")

            # Extract from address (topic[1])
            from_address = "0x" + topics[1][-40:] if len(topics) > 1 else None

            # Extract to address (topic[2])
            to_address = "0x" + topics[2][-40:] if len(topics) > 2 else None

            # Extract amount from data (in wei/smallest unit)
            amount_hex = data if data != "0x" else "0x0"
            amount = int(amount_hex, 16) if amount_hex else 0

            # Convert to PAL (assuming 18 decimals - verify this)
            amount_pal = amount / 10**18

            # Get block and transaction info
            block_number = int(log.get("blockNumber", "0x0"), 16)
            tx_hash = log.get("transactionHash", "")

            # Get block timestamp
            block_timestamp = None
            try:
                block = self.rpc.get_block_by_number(block_number, False)
                if block:
                    block_timestamp = int(block.get("timestamp", "0x0"), 16)
            except Exception as e:
                print(f"Could not fetch block timestamp: {e}")

            return {
                "from_address": from_address.lower() if from_address else None,
                "to_address": to_address.lower() if to_address else None,
                "amount": amount,
                "amount_pal": amount_pal,
                "block_number": block_number,
                "block_timestamp": block_timestamp,
                "timestamp": datetime.fromtimestamp(block_timestamp) if block_timestamp else None,
                "tx_hash": tx_hash,
                "log_index": int(log.get("logIndex", "0x0"), 16)
            }

        except Exception as e:
            print(f"Error parsing transfer event: {e}")
            return None

    def get_contract_deployment_block(self) -> int:
        """
        Try to find the block where the migration contract was deployed
        Uses binary search to find first block with contract code
        """
        print("Searching for migration contract deployment block...")

        latest_block = self.rpc.get_block_number()

        # Binary search for deployment block
        left, right = 0, latest_block
        deployment_block = 0

        while left <= right:
            mid = (left + right) // 2

            try:
                code = self.rpc.get_code(MIGRATION_CONTRACT_ADDRESS, hex(mid))

                if code and code != "0x":
                    # Contract exists at this block, search earlier
                    deployment_block = mid
                    right = mid - 1
                else:
                    # Contract doesn't exist, search later
                    left = mid + 1
            except Exception as e:
                print(f"Error checking block {mid}: {e}")
                break

        print(f"Migration contract deployed at block: {deployment_block}")
        return deployment_block

    def check_migration_deadline(self) -> Optional[Dict]:
        """
        Try to read migration deadline from contract
        This requires knowing the contract ABI - we'll attempt common function signatures
        """
        # Common deadline function selectors
        function_selectors = [
            "0x6c7d5d26",  # deadline()
            "0x29dcb0cf",  # endTime()
            "0xf5f5ba72",  # migrationEnd()
        ]

        for selector in function_selectors:
            try:
                result = self.rpc.call_contract(MIGRATION_CONTRACT_ADDRESS, selector)

                if result and result != "0x":
                    timestamp = int(result, 16)
                    if timestamp > 0 and timestamp < 2**32:  # Reasonable timestamp
                        return {
                            "deadline_timestamp": timestamp,
                            "deadline_datetime": datetime.fromtimestamp(timestamp),
                            "time_remaining": timestamp - int(time.time())
                        }
            except Exception as e:
                continue

        return None

    def analyze_transaction_source(self, tx_hash: str) -> str:
        """
        Analyze if a migration came from Sonic native or Ethereum bridge
        Returns: "sonic" or "ethereum" or "unknown"
        """
        try:
            tx = self.rpc.get_transaction_by_hash(tx_hash)
            receipt = self.rpc.get_transaction_receipt(tx_hash)

            if not tx or not receipt:
                return "unknown"

            # Check transaction logs for bridge-related events
            logs = receipt.get("logs", [])

            # Look for bridge-related event signatures
            bridge_signatures = [
                "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925",  # Approval
                "0x2849b43074093a05396b6f2a937dee8565e4a0d1a0033ea7a8a6c568b5da1a30",  # Bridge event
            ]

            for log in logs:
                topics = log.get("topics", [])
                if topics and topics[0] in bridge_signatures:
                    return "ethereum"

            # If no bridge signatures found, likely Sonic native
            return "sonic"

        except Exception as e:
            print(f"Error analyzing transaction source: {e}")
            return "unknown"
