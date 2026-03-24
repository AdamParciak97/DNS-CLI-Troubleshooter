from __future__ import annotations
import sys
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from cli_troubleshooter.dashboard.routers import diagnostics, history, alerts_router, ws
from cli_troubleshooter.dashboard.routers import auth_router, export_router

app = FastAPI(title="CLI Troubleshooter Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api")
app.include_router(diagnostics.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(alerts_router.router, prefix="/api")
app.include_router(export_router.router, prefix="/api")
app.include_router(ws.router)

STATIC_DIR = pathlib.Path(__file__).parent / "static"

@app.get("/", response_class=HTMLResponse)
async def index():
    html_file = STATIC_DIR / "index.html"
    if not html_file.exists():
        return HTMLResponse("<h1>index.html not found</h1>", status_code=500)
    return HTMLResponse(html_file.read_text(encoding="utf-8"))
