#!/bin/bash

# Digital Store Bot v2 Deployment Script
set -e

echo "🚀 Deploying Digital Store Bot v2..."

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
poetry install --no-dev

# Set up configuration
echo "⚙️ Setting up configuration..."
if [ ! -f "config/settings.yml" ]; then
    if [ -f "config/settings.example.yml" ]; then
        cp config/settings.example.yml config/settings.yml
        echo "✅ Created config/settings.yml from example"
        echo "⚠️  Please edit config/settings.yml with your production settings"
    else
        echo "❌ Error: No configuration template found"
        exit 1
    fi
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs

# Database setup
echo "🗄️ Setting up database..."
if [ -d "alembic" ]; then
    poetry run alembic upgrade head
    echo "✅ Database migrations applied"
else
    echo "⚠️  No migrations found - database will be created on first run"
fi

# Check configuration
echo "🔧 Checking configuration..."
poetry run python -c "
from src.infrastructure.configuration import get_settings
try:
    settings = get_settings()
    print('✅ Configuration loaded successfully')
except Exception as e:
    print(f'❌ Configuration error: {e}')
    exit(1)
"

# Create systemd service (optional)
if [ "$1" = "--systemd" ]; then
    echo "🔧 Creating systemd service..."
    cat > /tmp/digital-store-bot.service << EOF
[Unit]
Description=Digital Store Bot v2
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/.venv/bin
ExecStart=$(which poetry) run python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    echo "📄 Systemd service file created at /tmp/digital-store-bot.service"
    echo "💡 To install: sudo cp /tmp/digital-store-bot.service /etc/systemd/system/"
    echo "💡 To enable: sudo systemctl enable digital-store-bot.service"
    echo "💡 To start: sudo systemctl start digital-store-bot.service"
fi

echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit config/settings.yml with your production settings"
echo "2. Set up your bot token and payment gateway credentials"
echo "3. Configure webhook URL if using webhook mode"
echo "4. Run 'poetry run python -m src.main' to start the bot"
echo ""
echo "📚 For more information, see the documentation in CLAUDE.md"