import os
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
import json

router = APIRouter(prefix="/logs", tags=["logs"])

LOG_FILE = os.getenv("LOG_FILE", "app.log")

@router.get("/tail", response_class=JSONResponse)
async def tail_logs(n: int = Query(100, ge=1, le=1000)):
    """
    Return the last N log lines as JSON objects (for Tabulator or admin UI).
    """
    if not os.path.exists(LOG_FILE):
        raise HTTPException(status_code=404, detail="Log file not found")
    lines = []
    with open(LOG_FILE, "r") as f:
        for line in f.readlines()[-n:]:
            try:
                lines.append(json.loads(line))
            except Exception:
                continue  # skip malformed lines
    return {"data": lines}
