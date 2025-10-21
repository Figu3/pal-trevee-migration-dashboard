# Vercel Postgres Setup Guide

This guide will help you set up Vercel Postgres and sync real migration data from the Sonic blockchain.

## Step 1: Create Vercel Postgres Database

1. Go to your Vercel dashboard: https://vercel.com/dashboard
2. Navigate to your project: `pal-trevee-migration-dashboard`
3. Go to the **Storage** tab
4. Click **Create Database**
5. Select **Postgres**
6. Choose a name (e.g., `pal-trevee-db`)
7. Select a region (choose closest to your users)
8. Click **Create**

Vercel will automatically add these environment variables to your project:
- `POSTGRES_URL`
- `POSTGRES_PRISMA_URL`
- `POSTGRES_URL_NON_POOLING`
- `POSTGRES_USER`
- `POSTGRES_HOST`
- `POSTGRES_PASSWORD`
- `POSTGRES_DATABASE`

## Step 2: Initialize Database Schema

After creating the database, you need to initialize the schema. You can do this locally:

```bash
# Install dependencies
pip install psycopg2-binary python-dotenv

# Set your POSTGRES_URL from Vercel dashboard
export POSTGRES_URL="postgres://..."

# Initialize the database
python3 -c "from api.db import init_database; init_database()"
```

Or create a one-time Vercel function to initialize it (safer):

```bash
# The database will auto-initialize on first API call
# Just visit: https://your-deployment.vercel.app/api/health
```

## Step 3: Sync Real Blockchain Data

Run the sync script locally to fetch real migration data:

```bash
# Install web3
pip install web3

# Set environment variables
export POSTGRES_URL="postgres://..."  # From Vercel dashboard
export SONIC_RPC_URL="https://rpc.soniclabs.com"
export PAL_TOKEN_ADDRESS="0xe90FE2DE4A415aD48B6DcEc08bA6ae98231948Ac"
export MIGRATION_CONTRACT_ADDRESS="0x99fe40e501151e92f10ac13ea1c06083ee170363"

# Run sync
cd api
python3 blockchain_sync.py --full
```

Options:
- `--full` - Sync from genesis (first time)
- `--start 12345` - Start from specific block
- `--end 67890` - End at specific block

## Step 4: Set Up Automated Sync (Optional)

### Option A: Vercel Cron Jobs

Create `vercel.json` cron configuration:

```json
{
  "crons": [
    {
      "path": "/api/cron/sync",
      "schedule": "*/15 * * * *"
    }
  ]
}
```

Then create `api/cron/sync.py` endpoint that runs the sync.

### Option B: GitHub Actions

Create `.github/workflows/sync.yml`:

```yaml
name: Sync Migration Data
on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes
  workflow_dispatch:  # Manual trigger

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install web3 psycopg2-binary
      - run: python3 api/blockchain_sync.py
        env:
          POSTGRES_URL: ${{ secrets.POSTGRES_URL }}
          SONIC_RPC_URL: https://rpc.soniclabs.com
          PAL_TOKEN_ADDRESS: "0xe90FE2DE4A415aD48B6DcEc08bA6ae98231948Ac"
          MIGRATION_CONTRACT_ADDRESS: "0x99fe40e501151e92f10ac13ea1c06083ee170363"
```

Add `POSTGRES_URL` to GitHub Secrets.

### Option C: Local Cron

Run sync every 15 minutes from your computer:

```bash
# Add to crontab (crontab -e)
*/15 * * * * cd /path/to/project/api && python3 blockchain_sync.py >> /tmp/sync.log 2>&1
```

## Step 5: Verify

1. Visit your dashboard: `https://your-deployment.vercel.app`
2. Check `/api/health` - should show `"database": "postgres"`
3. Check `/api/sync-status` - should show last synced block
4. Check `/api/metrics` - should show real migration data

## Troubleshooting

### Database connection errors

- Verify `POSTGRES_URL` is set in Vercel environment variables
- Check that database was created successfully
- Try redeploying the project

### No migrations found

- Verify contract addresses are correct
- Check that Sonic RPC is accessible
- Ensure sync script has correct start block

### Sync is slow

- The first full sync may take 10-30 minutes depending on blockchain size
- Subsequent syncs are incremental and fast
- Consider reducing batch size if hitting rate limits

## Data Retention

Vercel Postgres has different retention based on plan:
- **Hobby**: 60 days, 256 MB
- **Pro**: No limit, 512 MB
- **Enterprise**: Custom

For long-term storage, consider backing up to S3 or other storage.

## Cost Estimation

- **Database**: Hobby plan is free (256 MB should be enough for ~100K migrations)
- **Functions**: Free tier includes 100GB-hrs per month
- **Bandwidth**: Free tier includes 100 GB per month

## Next Steps

1. Set up automated sync (GitHub Actions recommended)
2. Add monitoring/alerts for failed syncs
3. Create database backup strategy
4. Consider adding analytics and advanced filtering
