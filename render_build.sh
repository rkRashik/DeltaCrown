#!/usr/bin/env bash
# Build script for Render deployment
# Optimised for Render Free Tier (512 MB RAM)

set -o errexit  # exit on error

# ── 1. Node / Tailwind CSS build ────────────────────────────────────
# Cap Node heap to 256 MB so it doesn't crowd out Python later.
export NODE_OPTIONS="--max-old-space-size=256"

echo "🔧 Installing Node.js dev-dependencies (Tailwind build)…"
npm install                   # generates lockfile on first run; npm ci on subsequent deploys

echo "🎨 Building Tailwind CSS…"
npm run build-css

# Free every byte of Node overhead before Python starts
echo "🧹 Cleaning up Node artefacts…"
npm cache clean --force 2>/dev/null || true
rm -rf node_modules            # CSS is already compiled into static/dist/

# ── 2. Python ───────────────────────────────────────────────────────
echo "🐍 Installing Python dependencies (production only)…"
pip install --no-cache-dir -r requirements-prod.txt

echo "📦 Collecting Django static files…"
python manage.py collectstatic --noinput

echo "🔄 Running Django migrations…"
python manage.py migrate

echo "✅ Build completed successfully!"