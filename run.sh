#!/bin/bash

# PAL to TREVEE Migration Dashboard - Quick Start Script

set -e

echo "=================================="
echo "PAL Migration Dashboard - Quick Start"
echo "=================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

echo "✓ Python 3 found"

# Check if in correct directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "Error: Please run this script from the pal-trevee-dashboard directory"
    exit 1
fi

echo "✓ Project structure verified"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
cd backend
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Check if database exists
if [ ! -f "../data/migrations.db" ]; then
    echo ""
    echo "No database found. Choose an option:"
    echo "  1) Generate demo data (for testing)"
    echo "  2) Sync from blockchain (real data)"
    read -p "Enter choice (1 or 2): " choice

    if [ "$choice" = "1" ]; then
        echo ""
        echo "Generating demo data..."
        python3 demo_data.py --migrations 200 --addresses 50
    elif [ "$choice" = "2" ]; then
        echo ""
        echo "Syncing from blockchain (this may take a while)..."
        python3 sync.py --full
    else
        echo "Invalid choice"
        exit 1
    fi
else
    echo "✓ Database found"
fi

# Start API server
echo ""
echo "Starting API server..."
echo "(Press Ctrl+C to stop)"
echo ""
python3 api.py
