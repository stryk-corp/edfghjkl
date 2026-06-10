#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "=== UniClear — University Clearance System ==="
echo ""

# Create venv if needed
if [ ! -d "venv" ]; then
  echo "Creating virtual environment…"
  python3 -m venv venv
fi

# Activate
source venv/bin/activate

# Install deps
echo "Installing dependencies…"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Create directories
mkdir -p uploads certificates

# Copy .env if not present
[ ! -f .env ] && cp .env.example .env && echo "Created .env from template"

echo ""
echo "Starting server…"
echo "  → Student Portal : http://127.0.0.1:6001/frontend/student.html"
echo "  → Officer Portal  : http://127.0.0.1:6001/frontend/officer.html"
echo "  → Admin Dashboard : http://127.0.0.1:6001/frontend/admin.html"
echo "  → Verify Cert     : http://127.0.0.1:6001/frontend/verify.html"
echo "  → API Docs        : http://127.0.0.1:6001/docs"
echo ""
echo "Demo accounts:"
echo "  Student : student@university.edu / student123"
echo "  Officer : library@university.edu / officer123"
echo "  Admin   : admin@university.edu   / admin123"
echo ""

uvicorn backend.main:app --host 127.0.0.1 --port 6001
