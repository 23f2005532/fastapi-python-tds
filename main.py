# api/check_latency.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import json
import math
import os

app = FastAPI()

# Enable CORS for POST requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # allow any origin
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Request model
class Query(BaseModel):
    regions: List[str]
    threshold_ms: float

# Helper: compute percentile (pure python)
def percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    # Using the "nearest-rank" method: index = ceil(p * n) - 1
    rank = math.ceil(p * n) - 1
    rank = max(0, min(rank, n - 1))
    return float(sorted_vals[rank])

# Load telemetry from telemetry.json if present, otherwise use embedded sample
def load_telemetry():
    path = os.path.join(os.path.dirname(__file__), "..", "telemetry.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Expecting list of objects with keys: region, service, latency_ms, uptime_pct, timestamp
            return data
    except Exception:
        # fallback sample bundle (small), used if telemetry.json is not present
        return [
            {"region": "apac", "service": "support", "latency_ms": 129.73, "uptime_pct": 98.345, "timestamp": 20250301},
            {"region": "apac", "service": "payments", "latency_ms": 147.85, "uptime_pct": 98.423, "timestamp": 20250301},
            {"region": "apac", "service": "catalog", "latency_ms": 160.1, "uptime_pct": 99.0, "timestamp": 20250302},
            {"region": "emea", "service": "support", "latency_ms": 170.5, "uptime_pct": 97.9, "timestamp": 20250301},
            {"region": "emea", "service": "payments", "latency_ms": 180.2, "uptime_pct": 99.2, "timestamp": 20250302},
            {"region": "emea", "service": "catalog", "latency_ms": 200.0, "uptime_pct": 96.5, "timestamp": 20250303},
        ]

TELEMETRY = load_telemetry()

@app.post("/check-latency")
async def check_latency(q: Query) -> Dict[str, Any]:
    if not isinstance(q.regions, list) or len(q.regions) == 0:
        raise HTTPException(status_code=400, detail="regions must be a non-empty list")

    # normalize region matching (case-insensitive)
    region_map: Dict[str, List[Dict[str, Any]]] = {}
    for r in q.regions:
        region_map[r] = []

    for rec in TELEMETRY:
        rec_region = str(rec.get("region", "")).lower()
        # find matching requested region(s) case-insensitively
        for requested in q.regions:
            if rec_region == requested.lower():
                region_map[requested].append(rec)

    result: Dict[str, Any] = {}
    for region, records in region_map.items():
        latencies = [float(r["latency_ms"]) for r in records if "latency_ms" in r]
        uptimes = [float(r["uptime_pct"]) for r in records if "uptime_pct" in r]

        avg_latency = float(sum(latencies) / len(latencies)) if latencies else None
        p95_latency = percentile(latencies, 0.95)
        avg_uptime = float(sum(uptimes) / len(uptimes)) if uptimes else None
        breaches = sum(1 for v in latencies if v > float(q.threshold_ms))

        # Format floats to reasonable precision (or keep None)
        def fmt(x):
            return None if x is None else round(x, 3)

        result[region] = {
            "avg_latency": fmt(avg_latency),
            "p95_latency": fmt(p95_latency),
            "avg_uptime": fmt(avg_uptime),
            "breaches": breaches,
            "samples": len(records),
        }

    return {"regions": result}
