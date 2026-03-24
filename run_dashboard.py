"""Skrypt startowy dashboardu CLI Troubleshooter."""
from __future__ import annotations
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    print(f"Dashboard: http://{args.host}:{args.port}")
    uvicorn.run(
        "cli_troubleshooter.dashboard.app:app",
        host=args.host,
        port=args.port,
        log_level="info",
    )
