"""
RPC Client for interacting with Sonic blockchain
"""

import requests
import time
from typing import Dict, List, Optional, Any
from config import SONIC_RPC_URL, MAX_RETRIES, RETRY_DELAY


class SonicRPCClient:
    """Client for interacting with Sonic blockchain via JSON-RPC"""

    def __init__(self, rpc_url: str = SONIC_RPC_URL):
        self.rpc_url = rpc_url
        self.session = requests.Session()

    def _make_request(self, method: str, params: List[Any]) -> Dict:
        """Make a JSON-RPC request with retry logic"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }

        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.post(
                    self.rpc_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()

                if "error" in result:
                    raise Exception(f"RPC Error: {result['error']}")

                return result.get("result")

            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                print(f"Request failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                time.sleep(RETRY_DELAY)

    def get_block_number(self) -> int:
        """Get the latest block number"""
        result = self._make_request("eth_blockNumber", [])
        return int(result, 16)

    def get_block_by_number(self, block_number: int, full_transactions: bool = True) -> Dict:
        """Get block by number"""
        block_hex = hex(block_number)
        return self._make_request("eth_getBlockByNumber", [block_hex, full_transactions])

    def get_transaction_receipt(self, tx_hash: str) -> Dict:
        """Get transaction receipt"""
        return self._make_request("eth_getTransactionReceipt", [tx_hash])

    def get_logs(self, from_block: int, to_block: int, address: Optional[str] = None,
                 topics: Optional[List[str]] = None) -> List[Dict]:
        """Get logs/events for a specific address and topics"""
        params = {
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block)
        }

        if address:
            params["address"] = address

        if topics:
            params["topics"] = topics

        return self._make_request("eth_getLogs", [params])

    def call_contract(self, to_address: str, data: str, block: str = "latest") -> str:
        """Call a contract method (read-only)"""
        params = {
            "to": to_address,
            "data": data
        }
        return self._make_request("eth_call", [params, block])

    def get_balance(self, address: str, block: str = "latest") -> int:
        """Get account balance"""
        result = self._make_request("eth_getBalance", [address, block])
        return int(result, 16)

    def get_transaction_by_hash(self, tx_hash: str) -> Dict:
        """Get transaction details by hash"""
        return self._make_request("eth_getTransactionByHash", [tx_hash])

    def get_code(self, address: str, block: str = "latest") -> str:
        """Get contract code at address"""
        return self._make_request("eth_getCode", [address, block])
