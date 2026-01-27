#!/usr/bin/env python3
"""
Kite Forecast Israel - Run Script
Starts the FastAPI server
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

if __name__ == "__main__":
    import uvicorn

    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    print(f"""
    ╔═══════════════════════════════════════════╗
    ║     Kite Forecast Israel                  ║
    ║     תחזית קייטסרפינג ישראל               ║
    ╠═══════════════════════════════════════════╣
    ║  Starting server at http://{host}:{port}      ║
    ╚═══════════════════════════════════════════╝
    """)

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
