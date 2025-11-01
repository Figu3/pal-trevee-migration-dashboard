"""
Configuration file for PAL to TREVEE Migration Dashboard
"""

# Sonic Blockchain Configuration
SONIC_RPC_URL = "https://rpc.soniclabs.com"
SONIC_CHAIN_ID = 146
SONICSCAN_API_URL = "https://api.sonicscan.org/api"
SONICSCAN_API_KEY = ""  # Optional: Set your Sonicscan API key here for higher rate limits

# Contract Addresses
PAL_TOKEN_ADDRESS = "0xe90FE2DE4A415aD48B6DcEc08bA6ae98231948Ac"
MIGRATION_CONTRACT_ADDRESS = "0x99fe40e501151e92f10ac13ea1c06083ee170363"

# Database Configuration
DB_PATH = "../data/migrations.db"

# Dashboard Configuration
REFRESH_INTERVAL = 300  # seconds (5 minutes)
LARGE_MIGRATION_THRESHOLD = 100000  # PAL tokens (for alerts)

# Data Collection Settings
START_BLOCK = 52609535  # Migration contract deployment block (Oct 10, 2025)
BATCH_SIZE = 10000  # Number of blocks to query at once
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Migration Deadline (set to None if not applicable)
MIGRATION_DEADLINE = None  # Format: "2025-12-31 23:59:59" or None

# Export Settings
EXPORT_FORMATS = ["csv", "json"]

# Alert Settings (optional)
ENABLE_ALERTS = False
ALERT_EMAIL = ""
ALERT_DISCORD_WEBHOOK = ""

# Known Addresses (for labeling)
KNOWN_ADDRESSES = {
    # Add known addresses here for display purposes
    # "0x1234...": "Paladin Treasury",
}

# ============================================================================
# TREVEE MULTI-CHAIN CONFIGURATION
# ============================================================================

# Trevee Token Addresses by Chain
TREVEE_CHAINS = {
    "sonic": {
        "name": "Sonic",
        "chain_id": 146,
        "rpc_url": "https://rpc.soniclabs.com",
        "explorer": "https://sonicscan.org",
        "trevee_token": "0xe90fe2de4a415ad48b6dcec08ba6ae98231948ac",  # TREVEE token address on Sonic
        "staking_contract": "0x3ba32287b008ddf3c5a38df272369931e3030152",  # stkTRE staking contract
        "enabled": True
    },
    "plasma": {
        "name": "Plasma",
        "chain_id": 9745,
        "rpc_url": "https://rpc.plasma.to",  # Official Plasma RPC (rate limited)
        "explorer": "https://plasmascan.to",
        "trevee_token": "0xe90FE2DE4A415aD48B6DcEc08bA6ae98231948Ac",  # TREVEE token on Plasma
        "staking_contract": "0x0000000000000000000000000000000000000000",  # stkTREVEE not deployed yet
        "enabled": True
    },
    "ethereum": {
        "name": "Ethereum",
        "chain_id": 1,
        "rpc_url": "https://eth-mainnet.g.alchemy.com/v2/ph0FUrSi6-8SvDzvJYtc1",  # Alchemy RPC for better limits
        "explorer": "https://etherscan.io",
        "pal_token": "0xAB846Fb6C81370327e784Ae7CbB6d6a6af6Ff4BF",  # PAL on Ethereum (for migration tracking)
        "migration_contract": "0x3bA32287B008DdF3c5a38dF272369931E3030152",  # Ethereum migration contract
        "trevee_token": "0xe90FE2DE4A415aD48B6DcEc08bA6ae98231948Ac",  # TREVEE token on Ethereum
        "staking_contract": "0x0000000000000000000000000000000000000000",  # No staking yet
        "enabled": True  # Track ETH→Sonic migrations + TREVEE supply
    }
}

# Trevee Total Supply (for staking percentage calculation)
TREVEE_TOTAL_SUPPLY = 50000000  # 50 million TREVEE total supply on Sonic

# Update intervals for Trevee metrics
TREVEE_METRICS_REFRESH_INTERVAL = 300  # seconds (5 minutes)
