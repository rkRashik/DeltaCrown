#!/usr/bin/env bash
# Build script for Render deployment
# This script installs dependencies and builds CSS assets

set -o errexit  # exit on error

echo "🔧 Installing Node.js dependencies..."
npm install --include=dev

echo "🎨 Building Tailwind CSS..."
npm run build-css

echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt

echo "📦 Collecting Django static files..."
python manage.py collectstatic --noinput

echo "🔄 Running Django migrations..."
python manage.py migrate

echo "✅ Build completed successfully!"