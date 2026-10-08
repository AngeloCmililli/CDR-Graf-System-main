import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

from app.cdr_service import CSV_PATH, get_dashboard_metrics

app = FastAPI(title="API Graficas CDR")
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@app.get("/", response_class=HTMLResponse)
def serve_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/metrics")
def get_metrics():
    return get_dashboard_metrics()


@app.get("/api/stream-metrics")
async def stream_metrics():
    async def event_generator():
        last_modified = None
        while True:
            try:
                current_modified = CSV_PATH.stat().st_mtime if CSV_PATH.exists() else None
            except OSError:
                current_modified = None

            if current_modified != last_modified:
                last_modified = current_modified
                yield {
                    "event": "update",
                    "data": json.dumps(get_dashboard_metrics(), ensure_ascii=False),
                }

            await asyncio.sleep(5)

    return EventSourceResponse(event_generator())