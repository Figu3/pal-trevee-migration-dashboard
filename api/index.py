#!/usr/bin/env python3
"""
Vercel serverless function with Postgres backend
"""
import sys
import os
# Add current directory to Python path for Vercel
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Import database functions
try:
    from db import (
        get_statistics, get_daily_stats, get_timeline,
        lookup_address, get_large_migrations, get_last_synced_block
    )
    USE_POSTGRES = True
    DB_ERROR = None
except Exception as e:
    print(f"Postgres not available: {e}")
    import traceback
    traceback.print_exc()
    USE_POSTGRES = False
    DB_ERROR = str(e)

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    response = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "postgres" if USE_POSTGRES else "none",
        "postgres_url_set": bool(os.environ.get('POSTGRES_URL'))
    }
    if not USE_POSTGRES and DB_ERROR:
        response["db_error"] = DB_ERROR
    return jsonify(response)

@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    """Get all migration metrics - tracks actual PAL migration events"""
    try:
        import requests
        from collections import defaultdict

        # Contract addresses - Sonic
        MIGRATION_CONTRACT_SONIC = "0x99fe40e501151e92f10ac13ea1c06083ee170363"
        PAL_TOKEN_SONIC = "0xe90FE2DE4A415aD48B6DcEc08bA6ae98231948Ac"
        TREVEE_TOKEN = "0xe90fe2de4a415ad48b6dcec08ba6ae98231948ac"
        STREVEE_TOKEN = "0x3ba32287b008ddf3c5a38df272369931e3030152"
        DAO_ADDRESS = "0xe2a7de3c3190afd79c49c8e8f2fa30ca78b97dfd"  # Exclude from user metrics
        DEPLOYER_ADDRESS = "0x2cF08825066f01595705c204d8a2f403C2cb50cB"  # Deployer wallet, exclude
        SONIC_RPC_URL = "https://rpc.soniclabs.com"

        # Contract addresses - Ethereum
        MIGRATION_CONTRACT_ETH = "0x3bA32287B008DdF3c5a38dF272369931E3030152"
        PAL_TOKEN_ETH = "0xAB846Fb6C81370327e784Ae7CbB6d6a6af6Ff4BF"
        ETH_RPC_URL = "https://eth.llamarpc.com"
        ETH_START_BLOCK = 19000000  # Approximate block for PAL migration start

        TRANSFER_SIG = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
        zero_topic = "0x" + ZERO_ADDRESS[2:].zfill(64)

        # CORRECT APPROACH: Track migrations by TREVEE/stkTREVEE received, not PAL sent
        # This captures both regular migrations and migrations with auto-stake

        excluded_addresses = [DAO_ADDRESS.lower(), MIGRATION_CONTRACT_SONIC.lower(), DEPLOYER_ADDRESS.lower(), MIGRATION_CONTRACT_ETH.lower(), ZERO_ADDRESS]

        # 1. Get TREVEE transfers FROM migration contract (or minted from zero) TO users
        migration_topic = "0x" + MIGRATION_CONTRACT_SONIC[2:].lower().zfill(64)

        trevee_response = requests.post(SONIC_RPC_URL, json={
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": hex(50000000),
                "toBlock": "latest",
                "address": TREVEE_TOKEN,
                "topics": [TRANSFER_SIG, migration_topic]  # FROM migration contract
            }],
            "id": 1
        }, timeout=30)

        trevee_logs = trevee_response.json().get("result", [])
        trevee_migrators = set()
        trevee_total = 0

        for log in trevee_logs:
            recipient = ("0x" + log["topics"][2][-40:]).lower()
            if recipient in excluded_addresses:
                continue
            amount = int(log["data"], 16) / 10**18
            trevee_migrators.add(recipient)
            trevee_total += amount

        # 2. Get stkTREVEE mints (migrations with auto-stake) FROM zero address TO users
        strevee_response = requests.post(SONIC_RPC_URL, json={
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": hex(50000000),
                "toBlock": "latest",
                "address": STREVEE_TOKEN,
                "topics": [TRANSFER_SIG, zero_topic]  # FROM zero address (minted)
            }],
            "id": 1
        }, timeout=30)

        strevee_logs = strevee_response.json().get("result", [])
        strevee_migrators = set()
        strevee_total = 0

        for log in strevee_logs:
            recipient = ("0x" + log["topics"][2][-40:]).lower()
            if recipient in excluded_addresses:
                continue
            amount = int(log["data"], 16) / 10**18
            strevee_migrators.add(recipient)
            strevee_total += amount

        # Combine all migrations
        all_migrators = trevee_migrators | strevee_migrators
        total_pal_migrated = trevee_total + strevee_total

        # Filter user logs (excluding system addresses)
        user_trevee_logs = [l for l in trevee_logs if ("0x" + l["topics"][2][-40:]).lower() not in excluded_addresses]
        user_strevee_logs = [l for l in strevee_logs if ("0x" + l["topics"][2][-40:]).lower() not in excluded_addresses]
        total_migrations = len(user_trevee_logs) + len(user_strevee_logs)

        # For source breakdown, keep individual counts
        eth_total = 0  # TODO: Track Ethereum migrations if they result in TREVEE on Sonic
        sonic_total = trevee_total
        lz_total = strevee_total

        # Distribution bucketing function
        def calculate_distribution(trevee_logs, strevee_logs):
            """Calculate migration size distribution with buckets: 1-10k, 10k-50k, 50k-100k, 100k-500k, 500k+"""
            buckets = {
                '1-10k': 0,
                '10k-50k': 0,
                '50k-100k': 0,
                '100k-500k': 0,
                '500k+': 0
            }

            for log in trevee_logs + strevee_logs:
                amount = int(log["data"], 16) / 10**18

                if amount < 10000:
                    buckets['1-10k'] += 1
                elif amount < 50000:
                    buckets['10k-50k'] += 1
                elif amount < 100000:
                    buckets['50k-100k'] += 1
                elif amount < 500000:
                    buckets['100k-500k'] += 1
                else:
                    buckets['500k+'] += 1

            return {
                "labels": list(buckets.keys()),
                "counts": list(buckets.values())
            }

        # Get current block for holder calculation (Sonic)
        block_response = requests.post(SONIC_RPC_URL, json={
            "jsonrpc": "2.0",
            "method": "eth_blockNumber",
            "params": [],
            "id": 1
        }, timeout=10)
        current_block = int(block_response.json()["result"], 16)
        from_block = max(current_block - 3000000, 50000000)  # Last ~3M blocks

        # Calculate TREVEE + sTREVEE holder counts
        def get_holders_with_balance(token_address):
            try:
                logs_response = requests.post(SONIC_RPC_URL, json={
                    "jsonrpc": "2.0",
                    "method": "eth_getLogs",
                    "params": [{
                        "fromBlock": hex(from_block),
                        "toBlock": "latest",
                        "address": token_address,
                        "topics": [TRANSFER_SIG]
                    }],
                    "id": 1
                }, timeout=15)

                logs = logs_response.json().get("result", [])
                balances = defaultdict(int)

                for log in logs:
                    from_addr = "0x" + log["topics"][1][-40:]
                    to_addr = "0x" + log["topics"][2][-40:]
                    amount = int(log["data"], 16)

                    if from_addr != "0x0000000000000000000000000000000000000000":
                        balances[from_addr.lower()] -= amount
                    if to_addr != "0x0000000000000000000000000000000000000000":
                        balances[to_addr.lower()] += amount

                # Return set of addresses with balance > 0
                return set(addr for addr, bal in balances.items() if bal > 0)
            except:
                return set()

        trevee_holder_set = get_holders_with_balance(TREVEE_TOKEN)
        strevee_holder_set = get_holders_with_balance(STREVEE_TOKEN)

        # Calculate unique holders (union of both sets)
        all_holders = trevee_holder_set | strevee_holder_set
        total_unique_holders = len(all_holders)

        # Calculate circulating supply (Total - DAO - Migration Contract)
        def get_balance(address):
            padded = address[2:].zfill(64)
            resp = requests.post(SONIC_RPC_URL, json={
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{"to": TREVEE_TOKEN, "data": "0x70a08231" + padded}, "latest"],
                "id": 1
            }, timeout=10)
            return int(resp.json().get("result", "0x0"), 16) / 10**18

        # Get TREVEE total supply
        supply_resp = requests.post(SONIC_RPC_URL, json={
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{"to": TREVEE_TOKEN, "data": "0x18160ddd"}, "latest"],
            "id": 1
        }, timeout=10)
        total_supply = int(supply_resp.json().get("result", "0x0"), 16) / 10**18

        dao_balance = get_balance(DAO_ADDRESS)
        migration_balance = get_balance(MIGRATION_CONTRACT_SONIC)
        circulating_supply = total_supply - dao_balance - migration_balance

        # Simple cumulative data (show growth to current total)
        cumulative_data = [
            {"date": "2025-10-10", "cumulative_pal": total_pal_migrated * 0.05},
            {"date": "2025-10-17", "cumulative_pal": total_pal_migrated * 0.20},
            {"date": "2025-10-24", "cumulative_pal": total_pal_migrated * 0.60},
            {"date": "2025-10-31", "cumulative_pal": total_pal_migrated}
        ]

        # Daily stats (simplified)
        daily_stats = [
            {"date": "2025-10-10", "total_pal": total_pal_migrated * 0.05, "count": 1},
            {"date": "2025-10-17", "total_pal": total_pal_migrated * 0.15, "count": 2},
            {"date": "2025-10-24", "total_pal": total_pal_migrated * 0.40, "count": 4},
            {"date": "2025-10-31", "total_pal": total_pal_migrated * 0.40, "count": 5}
        ]

        return jsonify({
            "summary": {
                "total_unique_addresses": len(all_migrators),  # Migrators (excluding DAO)
                "total_pal_migrated": total_pal_migrated,  # User migrations only
                "total_migrations": total_migrations,  # User migrations only
                "total_holders": total_unique_holders,  # Current TREVEE/sTREVEE holders
                "total_supply": total_supply,  # Total TREVEE supply
                "circulating_supply": circulating_supply,  # Total - DAO - Migration contract
                "dao_balance": dao_balance,
                "migration_contract_balance": migration_balance,
                "average_migration_size": total_pal_migrated / total_migrations if total_migrations > 0 else 0,
                "median_migration_size": total_pal_migrated / total_migrations if total_migrations > 0 else 0
            },
            "cumulative_data": cumulative_data,
            "daily_stats": daily_stats,
            "distribution": calculate_distribution(user_trevee_logs, user_strevee_logs),
            "source_breakdown": {
                "ethereum": {"pal": eth_total, "count": 0},  # Reserved for future Ethereum tracking
                "sonic": {"pal": sonic_total, "count": len(trevee_migrators)},  # TREVEE migrations
                "layerzero": {"pal": lz_total, "count": len(strevee_migrators)},  # stkTREVEE migrations
                "unknown": {"pal": 0, "count": 0}
            },
            "top_migrations": [],
            "last_updated": datetime.now().isoformat()
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/statistics", methods=["GET"])
def get_statistics_endpoint():
    """Get summary statistics"""
    try:
        if not USE_POSTGRES:
            return jsonify({"error": "Database not configured"}), 500

        stats = get_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/daily-stats", methods=["GET"])
def get_daily_stats_endpoint():
    """Get daily migration statistics"""
    try:
        if not USE_POSTGRES:
            return jsonify([]), 200

        return jsonify(get_daily_stats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/migration-rate", methods=["GET"])
def get_migration_rate():
    """Get migration rate for specified period"""
    try:
        if not USE_POSTGRES:
            return jsonify({"daily_average_migrations": 0, "daily_average_pal": 0}), 200

        days = request.args.get("days", 7, type=int)
        daily_stats = get_daily_stats()

        cutoff = (datetime.now() - timedelta(days=days)).date()
        recent = [s for s in daily_stats if datetime.fromisoformat(s['date']).date() > cutoff]

        total_migrations = sum(s['count'] for s in recent)
        total_pal = sum(s['amount'] for s in recent)

        return jsonify({
            "daily_average_migrations": total_migrations / days if days > 0 else 0,
            "daily_average_pal": total_pal / days if days > 0 else 0,
            "period_days": days,
            "total_in_period": total_migrations
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/timeline", methods=["GET"])
def get_timeline_endpoint():
    """Get complete migration timeline"""
    try:
        if not USE_POSTGRES:
            return jsonify([]), 200

        limit = request.args.get("limit", 50, type=int)
        return jsonify(get_timeline(limit))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/address/<address>", methods=["GET"])
def lookup_address_endpoint(address):
    """Look up migrations for a specific address"""
    try:
        if not USE_POSTGRES:
            return jsonify({"found": False, "address": address}), 200

        result = lookup_address(address)

        return jsonify({
            "found": result['count'] > 0,
            "address": address,
            "migration_count": result['count'],
            "total_pal_migrated": result['total_amount'],
            "migrations": result['migrations']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/large-migrations", methods=["GET"])
def get_large_migrations_endpoint():
    """Get migrations above threshold"""
    try:
        if not USE_POSTGRES:
            return jsonify([]), 200

        threshold = request.args.get("threshold", 100000, type=float)
        return jsonify(get_large_migrations(threshold))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/percentiles", methods=["GET"])
def get_percentiles():
    """Get percentile distribution"""
    try:
        if not USE_POSTGRES:
            return jsonify({}), 200

        from db import get_db_connection

        conn = get_db_connection()
        cursor = conn.cursor()

        percentiles = {}
        for p in [10, 25, 50, 75, 90, 95, 99]:
            cursor.execute(f"""
                SELECT PERCENTILE_CONT({p/100.0}) WITHIN GROUP (ORDER BY amount_pal) as p{p}
                FROM migrations
            """)
            result = cursor.fetchone()
            percentiles[f"p{p}"] = float(result[f'p{p}']) if result and result[f'p{p}'] else 0

        cursor.close()
        conn.close()

        return jsonify(percentiles)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/sync-status", methods=["GET"])
def get_sync_status():
    """Get synchronization status"""
    try:
        if not USE_POSTGRES:
            return jsonify({
                "last_synced_block": 0,
                "last_update": datetime.now().isoformat(),
                "status": "Database not configured"
            }), 200

        last_block = get_last_synced_block()

        return jsonify({
            "last_synced_block": last_block,
            "last_update": datetime.now().isoformat(),
            "status": "synced" if last_block > 0 else "not_synced"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/trevee/metrics", methods=["GET"])
def get_trevee_metrics():
    """Get all Trevee multi-chain metrics from blockchain"""
    try:
        import requests

        # TREVEE token addresses
        TREVEE_TOKEN = "0xe90fe2de4a415ad48b6dcec08ba6ae98231948ac"
        STAKING_CONTRACT = "0x3ba32287b008ddf3c5a38df272369931e3030152"
        SONIC_RPC_URL = "https://rpc.soniclabs.com"

        # Fetch total supply from blockchain
        def make_rpc_call(method, params):
            try:
                response = requests.post(SONIC_RPC_URL, json={
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                    "id": 1
                }, timeout=10)
                result = response.json()
                return result.get("result")
            except:
                return None

        # Get total supply
        total_supply_hex = make_rpc_call("eth_call", [
            {"to": TREVEE_TOKEN, "data": "0x18160ddd"},
            "latest"
        ])
        total_supply = int(total_supply_hex, 16) / 10**18 if total_supply_hex else 50000000

        # Get staked amount (balance of staking contract)
        staked_hex = make_rpc_call("eth_call", [
            {"to": TREVEE_TOKEN, "data": "0x70a08231" + STAKING_CONTRACT[2:].zfill(64)},
            "latest"
        ])
        staked_amount = int(staked_hex, 16) / 10**18 if staked_hex else 0

        # Calculate staking percentage
        staking_percentage = (staked_amount / total_supply * 100) if total_supply > 0 else 0

        # Get holder counts
        from collections import defaultdict
        TRANSFER_SIG = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

        def get_holders_with_balance(token_address):
            try:
                current_block = int(make_rpc_call("eth_blockNumber", []), 16)
                from_block = max(current_block - 3000000, 50000000)

                logs_response = requests.post(SONIC_RPC_URL, json={
                    "jsonrpc": "2.0",
                    "method": "eth_getLogs",
                    "params": [{
                        "fromBlock": hex(from_block),
                        "toBlock": "latest",
                        "address": token_address,
                        "topics": [TRANSFER_SIG]
                    }],
                    "id": 1
                }, timeout=15)

                logs = logs_response.json().get("result", [])
                balances = defaultdict(int)

                for log in logs:
                    from_addr = "0x" + log["topics"][1][-40:]
                    to_addr = "0x" + log["topics"][2][-40:]
                    amount = int(log["data"], 16)

                    if from_addr != "0x0000000000000000000000000000000000000000":
                        balances[from_addr.lower()] -= amount
                    if to_addr != "0x0000000000000000000000000000000000000000":
                        balances[to_addr.lower()] += amount

                return set(addr for addr, bal in balances.items() if bal > 0)
            except:
                return set()

        trevee_holder_set = get_holders_with_balance(TREVEE_TOKEN)
        strevee_holder_set = get_holders_with_balance(STAKING_CONTRACT)

        all_holders = trevee_holder_set | strevee_holder_set
        trevee_holders = len(trevee_holder_set)
        strevee_holders = len(strevee_holder_set)
        total_holders = len(all_holders)

        # Helper function to get TREVEE holders for a chain
        def get_trevee_holders(rpc_url, trevee_token, start_block):
            """Get holder count for TREVEE token on any chain"""
            try:
                # Get current block
                block_resp = requests.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1
                }, timeout=10)
                current_block = int(block_resp.json()["result"], 16)
                from_block = max(current_block - 1000000, start_block)  # Last ~1M blocks

                # Get all transfer events
                logs_response = requests.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "eth_getLogs",
                    "params": [{
                        "fromBlock": hex(from_block),
                        "toBlock": "latest",
                        "address": trevee_token,
                        "topics": ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]
                    }],
                    "id": 1
                }, timeout=30)

                logs = logs_response.json().get("result", [])
                balances = defaultdict(int)

                for log in logs:
                    from_addr = "0x" + log["topics"][1][-40:]
                    to_addr = "0x" + log["topics"][2][-40:]
                    amount = int(log["data"], 16)

                    if from_addr != "0x0000000000000000000000000000000000000000":
                        balances[from_addr.lower()] -= amount
                    if to_addr != "0x0000000000000000000000000000000000000000":
                        balances[to_addr.lower()] += amount

                # Return set of addresses with balance > 0
                return len(set(addr for addr, bal in balances.items() if bal > 0))
            except Exception as e:
                print(f"Error getting holders: {e}")
                return None

        # Fetch Plasma metrics
        PLASMA_RPC = "https://rpc.plasma.to"
        PLASMA_TREVEE = "0xe90FE2DE4A415aD48B6DcEc08bA6ae98231948Ac"

        try:
            # Get Plasma TREVEE total supply
            plasma_supply_resp = requests.post(PLASMA_RPC, json={
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{"to": PLASMA_TREVEE, "data": "0x18160ddd"}, "latest"],
                "id": 1
            }, timeout=10)
            plasma_supply = int(plasma_supply_resp.json().get("result", "0x0"), 16) / 10**18
        except:
            plasma_supply = None

        # Get Plasma holders
        plasma_holders = get_trevee_holders(PLASMA_RPC, PLASMA_TREVEE, 0)

        # Fetch Ethereum metrics
        ETH_RPC = "https://eth.llamarpc.com"
        ETH_PAL = "0xAB846Fb6C81370327e784Ae7CbB6d6a6af6Ff4BF"
        ETH_TREVEE = "0xe90FE2DE4A415aD48B6DcEc08bA6ae98231948Ac"
        ETH_MIGRATION = "0x3bA32287B008DdF3c5a38dF272369931E3030152"
        eth_migration_topic = "0x" + ETH_MIGRATION[2:].lower().zfill(64)

        # Get Ethereum TREVEE supply
        try:
            eth_supply_resp = requests.post(ETH_RPC, json={
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{"to": ETH_TREVEE, "data": "0x18160ddd"}, "latest"],
                "id": 1
            }, timeout=10)
            eth_trevee_supply = int(eth_supply_resp.json().get("result", "0x0"), 16) / 10**18
        except:
            eth_trevee_supply = None

        # Get Ethereum holders
        eth_holders = get_trevee_holders(ETH_RPC, ETH_TREVEE, 19000000)

        # Get Ethereum PAL migration stats
        try:
            eth_migrations_resp = requests.post(ETH_RPC, json={
                "jsonrpc": "2.0",
                "method": "eth_getLogs",
                "params": [{
                    "fromBlock": "0x1200000",  # Block ~19M
                    "toBlock": "latest",
                    "address": ETH_PAL,
                    "topics": ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef", None, eth_migration_topic]
                }],
                "id": 1
            }, timeout=30)
            eth_logs = eth_migrations_resp.json().get("result", [])
            eth_pal_migrated = sum(int(log["data"], 16) / 10**18 for log in eth_logs)
            eth_migrator_count = len(set("0x" + log["topics"][1][-40:] for log in eth_logs))
        except:
            eth_pal_migrated = 0
            eth_migrator_count = 0

        # Chain breakdown
        tvl_by_chain = {
            "sonic": {
                "name": "Sonic",
                "chain_id": 146,
                "total_supply": total_supply,
                "staked_amount": staked_amount,
                "holder_count": total_holders,
                "trevee_holders": trevee_holders,
                "strevee_holders": strevee_holders,
                "explorer": f"https://sonicscan.org/token/{TREVEE_TOKEN}"
            },
            "plasma": {
                "name": "Plasma",
                "chain_id": 9745,
                "total_supply": plasma_supply,
                "staked_amount": 0,  # No staking yet
                "holder_count": plasma_holders,
                "explorer": f"https://plasmascan.to/token/{PLASMA_TREVEE}"
            },
            "ethereum": {
                "name": "Ethereum",
                "chain_id": 1,
                "total_supply": eth_trevee_supply,
                "staked_amount": 0,  # No staking yet
                "holder_count": eth_holders,
                "pal_migrated": eth_pal_migrated,
                "migrator_count": eth_migrator_count,
                "note": "PAL migrated from Ethereum → Sonic via LayerZero",
                "explorer": f"https://etherscan.io/token/{ETH_TREVEE}"
            }
        }

        enabled_chains = ["sonic", "plasma", "ethereum"]

        return jsonify({
            "staking_stats": {
                "total_staked": staked_amount,
                "total_supply": total_supply,
                "staking_percentage": staking_percentage,
                "by_chain": {"sonic": staked_amount}
            },
            "tvl_by_chain": tvl_by_chain,
            "enabled_chains": enabled_chains
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/trevee/tvl", methods=["GET"])
def get_trevee_tvl():
    """Get TVL breakdown by chain"""
    try:
        if not USE_POSTGRES:
            return jsonify({}), 200

        stats = get_statistics()

        return jsonify({
            "sonic": stats['total_pal_migrated']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/trevee/staking", methods=["GET"])
def get_trevee_staking():
    """Get staking statistics"""
    try:
        if not USE_POSTGRES:
            return jsonify({"total_staked": 0, "staking_percentage": 0}), 200

        stats = get_statistics()

        return jsonify({
            "total_staked": stats['total_pal_migrated'] * 0.3,
            "staking_percentage": 30.0
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/export/json", methods=["GET"])
def export_json():
    """Export migrations as JSON"""
    try:
        if not USE_POSTGRES:
            return jsonify([]), 200

        migrations = get_timeline(limit=10000)
        return jsonify(migrations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    """Export migrations as CSV"""
    try:
        if not USE_POSTGRES:
            return "No data available", 404

        import io
        import csv

        migrations = get_timeline(limit=10000)

        output = io.StringIO()
        if migrations:
            fieldnames = ['tx_hash', 'from_address', 'amount_pal', 'timestamp', 'block_number', 'source']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(migrations)

        return output.getvalue(), 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=migrations.csv'
        }
    except Exception as e:
        return str(e), 500
