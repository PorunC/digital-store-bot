#!/bin/bash

# Digital Store Bot v2 Setup Script
set -e

echo "🚀 Setting up Digital Store Bot v2..."

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs config

# Install dependencies with Poetry
echo "📦 Installing dependencies..."
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Please install Poetry first: https://python-poetry.org/docs/#installation"
    exit 1
fi

poetry install

# Copy configuration files if they don't exist
echo "⚙️ Setting up configuration..."
if [ ! -f "config/settings.yml" ]; then
    cp config/settings.example.yml config/settings.yml
    echo "✅ Created config/settings.yml from example"
    echo "⚠️  Please edit config/settings.yml with your settings"
else
    echo "ℹ️  config/settings.yml already exists"
fi

# Set up pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
poetry run pre-commit install

# Run initial tests
echo "🧪 Running tests..."
poetry run pytest --no-cov

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit config/settings.yml with your bot token and settings"
echo "2. Run 'poetry run python -m src.main' to start the bot"
echo "3. Run 'poetry run pytest' to run tests"