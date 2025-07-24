"""Entry point when running background tasks module directly."""

import sys
from pathlib import Path

# Add the src directory to the path if needed
src_dir = Path(__file__).parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Check which service to run based on the module name
if __name__ == "__main__":
    import asyncio
    from .scheduler_main import main
    
    # Run the scheduler main function
    asyncio.run(main())