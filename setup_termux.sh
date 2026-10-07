#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "===================================================="
echo "    Early Crypto Hunter Termux Auto-Setup Script"
echo "===================================================="
echo "[*] Updating package repositories..."
pkg update -y || echo "Warning: pkg update failed, continuing anyway..."

echo "[*] Installing required system dependencies..."
pkg install -y python git build-essential clang || echo "Warning: Package installations failed, continuing..."

echo "[*] Creating a clean Python virtual environment (venv)..."
if [ -d "venv" ]; then
    echo "[!] Existing 'venv' directory found, reusing it."
else
    python -m venv venv
fi

echo "[*] Activating virtual environment..."
source venv/bin/activate

echo "[*] Upgrading pip..."
pip install --upgrade pip

echo "[*] Installing Early Crypto Hunter dependencies..."
pip install -r requirements.txt

echo "[*] Running verification tests..."
PYTHONPATH=. python -m pytest

echo ""
echo "===================================================="
echo "          Setup Completed Successfully!"
echo "===================================================="
echo "To start using Early Crypto Hunter in Termux:"
echo "1. Activate the environment:   source venv/bin/activate"
echo "2. Run the Dashboard:          python -m early_crypto_hunter.dashboard"
echo "3. Run the CLI tool:           python -m early_crypto_hunter.cli scan"
echo "===================================================="
