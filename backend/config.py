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
START_BLOCK = 0  # Set to 0 to scan from genesis, or specific block to start from
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
