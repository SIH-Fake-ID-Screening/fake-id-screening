"""
Launcher for the Tampering Detection Service.

Reads HOST and PORT from environment variables so the service can run on any
machine or deployment platform without code changes:

    HOST=0.0.0.0 PORT=8000 python run.py        (from modules/tampering/)
    HOST=0.0.0.0 PORT=8000 python modules/tampering/run.py   (from repo root)

Defaults: HOST=0.0.0.0, PORT=8000
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        log_level="info",
    )
