"""
Trevee Multi-Chain Metrics Tracker
Fetches TVL, holder count, and staking data across multiple chains
"""

import requests
from typing import Dict, List, Optional
from config import TREVEE_CHAINS, TREVEE_TOTAL_SUPPLY


class TreveeMetricsTracker:
    """Track Trevee metrics across multiple chains"""

    # ERC20 ABI function selectors
    TOTAL_SUPPLY_SELECTOR = "0x18160ddd"  # totalSupply()
    BALANCE_OF_SELECTOR = "0x70a08231"    # balanceOf(address)
    DECIMALS_SELECTOR = "0x313ce567"       # decimals()

    def __init__(self):
        self.chains = {k: v for k, v in TREVEE_CHAINS.items() if v.get("enabled", False)}

    def _make_rpc_call(self, rpc_url: str, method: str, params: List) -> Optional[Dict]:
        """Make JSON-RPC call to blockchain"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": 1
            }
            response = requests.post(rpc_url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            return result.get("result")
        except Exception as e:
            print(f"RPC call failed for {rpc_url}: {e}")
            return None

    def get_token_total_supply(self, chain_key: str) -> Optional[float]:
        """Get total supply of Trevee token on a chain"""
        chain_config = self.chains.get(chain_key)
        if not chain_config:
            return None

        token_address = chain_config["trevee_token"]
        if token_address == "0x0000000000000000000000000000000000000000":
            print(f"Warning: Trevee token address not configured for {chain_key}")
            return None

        # Call totalSupply()
        result = self._make_rpc_call(
            chain_config["rpc_url"],
            "eth_call",
            [{"to": token_address, "data": self.TOTAL_SUPPLY_SELECTOR}, "latest"]
        )

        if result:
            try:
                supply_wei = int(result, 16)
                # Assume 18 decimals (standard for most tokens)
                return supply_wei / 10**18
            except Exception as e:
                print(f"Error parsing total supply: {e}")

        return None

    def get_staked_amount(self, chain_key: str) -> Optional[float]:
        """Get amount of Trevee staked on a chain"""
        chain_config = self.chains.get(chain_key)
        if not chain_config:
            return None

        token_address = chain_config["trevee_token"]
        staking_contract = chain_config["staking_contract"]

        if staking_contract == "0x0000000000000000000000000000000000000000":
            print(f"Warning: Staking contract not configured for {chain_key}")
            return None

        # Call balanceOf(stakingContract) on token contract
        # Pad address to 32 bytes (64 hex chars)
        padded_address = staking_contract[2:].zfill(64)
        data = self.BALANCE_OF_SELECTOR + padded_address

        result = self._make_rpc_call(
            chain_config["rpc_url"],
            "eth_call",
            [{"to": token_address, "data": data}, "latest"]
        )

        if result:
            try:
                staked_wei = int(result, 16)
                return staked_wei / 10**18
            except Exception as e:
                print(f"Error parsing staked amount: {e}")

        return None

    def get_holder_count_estimate(self, chain_key: str) -> Optional[int]:
        """
        Estimate holder count for a token on a chain
        Note: This requires scanning Transfer events or using an API
        For now, returns None - implement with indexer/API
        """
        # TODO: Implement using:
        # 1. Blockchain indexer API (like Covalent, Moralis)
        # 2. Block explorer API
        # 3. Custom event scanning (slow)

        chain_config = self.chains.get(chain_key)
        if not chain_config:
            return None

        print(f"Note: Holder count not yet implemented for {chain_key}")
        return None

    def get_tvl_by_chain(self) -> Dict[str, Dict]:
        """
        Get TVL breakdown by chain

        Returns:
            Dict with chain data including supply (as proxy for TVL)
        """
        tvl_data = {}

        for chain_key, chain_config in self.chains.items():
            supply = self.get_token_total_supply(chain_key)
            staked = self.get_staked_amount(chain_key)
            holders = self.get_holder_count_estimate(chain_key)

            tvl_data[chain_key] = {
                "name": chain_config["name"],
                "chain_id": chain_config["chain_id"],
                "total_supply": supply,
                "staked_amount": staked,
                "holder_count": holders,
                "explorer": chain_config["explorer"]
            }

        return tvl_data

    def get_total_staking_percentage(self) -> Dict:
        """
        Calculate total staking percentage across all chains

        Returns:
            Dict with total staked amount and percentage
        """
        total_staked = 0
        staking_by_chain = {}

        for chain_key in self.chains.keys():
            staked = self.get_staked_amount(chain_key)
            if staked:
                total_staked += staked
                staking_by_chain[chain_key] = staked

        staking_percentage = (total_staked / TREVEE_TOTAL_SUPPLY * 100) if TREVEE_TOTAL_SUPPLY > 0 else 0

        return {
            "total_staked": total_staked,
            "total_supply": TREVEE_TOTAL_SUPPLY,
            "staking_percentage": staking_percentage,
            "by_chain": staking_by_chain
        }

    def get_all_metrics(self) -> Dict:
        """Get all Trevee metrics in one call"""
        return {
            "tvl_by_chain": self.get_tvl_by_chain(),
            "staking_stats": self.get_total_staking_percentage(),
            "enabled_chains": list(self.chains.keys())
        }


def main():
    """Test the metrics tracker"""
    tracker = TreveeMetricsTracker()

    print("=" * 60)
    print("TREVEE MULTI-CHAIN METRICS")
    print("=" * 60)

    metrics = tracker.get_all_metrics()

    print("\nTVL by Chain:")
    for chain_key, data in metrics["tvl_by_chain"].items():
        print(f"\n{data['name']} (Chain ID: {data['chain_id']})")
        print(f"  Total Supply: {data['total_supply'] if data['total_supply'] else 'Not configured'}")
        print(f"  Staked Amount: {data['staked_amount'] if data['staked_amount'] else 'Not configured'}")
        print(f"  Holders: {data['holder_count'] if data['holder_count'] else 'Not implemented'}")

    print("\n" + "=" * 60)
    print("STAKING STATISTICS")
    print("=" * 60)
    stats = metrics["staking_stats"]
    print(f"Total Staked: {stats['total_staked']:,.2f} TREVEE")
    print(f"Total Supply: {stats['total_supply']:,.2f} TREVEE")
    print(f"Staking Percentage: {stats['staking_percentage']:.2f}%")

    print("\nStaking by Chain:")
    for chain, amount in stats["by_chain"].items():
        print(f"  {chain}: {amount:,.2f} TREVEE")


if __name__ == "__main__":
    main()
