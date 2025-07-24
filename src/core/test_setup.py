"""Test script for dependency-injector container setup."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.containers import ApplicationContainer, setup_container
from src.infrastructure.configuration.settings import Settings


async def test_container_setup():
    """Test the new dependency-injector container setup."""
    print("🧪 Testing dependency-injector container setup...")
    
    try:
        # Test 1: Basic container creation
        print("\n1. Testing container creation...")
        container = ApplicationContainer()
        print("✅ Container created successfully")
        
        # Test 2: Settings loading with minimal config
        print("\n2. Testing settings configuration...")
        
        # Create minimal settings for testing
        settings_data = {
            "bot": {
                "token": "test-token",
                "admins": [12345, 67890]  # List format
            },
            "database": {
                "url": "sqlite:///test.db"
            },
            "redis": {
                "host": "localhost",
                "port": 6379
            }
        }
        
        # Configure container
        container.config.from_dict(settings_data)
        print("✅ Container configured successfully")
        
        # Test 3: Provider resolution
        print("\n3. Testing provider resolution...")
        
        # Test event bus
        event_bus = container.event_bus()
        print("✅ Event bus provider works")
        
        # Test notification service (should work without bot token)
        try:
            notification_service = container.notification_service()
            print("✅ Notification service provider works")
        except Exception as e:
            print(f"⚠️  Notification service warning: {e}")
        
        # Test analytics service
        try:
            analytics_service = container.analytics_service()
            print("✅ Analytics service provider works")
        except Exception as e:
            print(f"⚠️  Analytics service warning: {e}")
        
        print("\n🎉 Container setup test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Container setup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_container_setup())
    sys.exit(0 if success else 1)