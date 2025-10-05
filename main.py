from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import math

# ---------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------
app = FastAPI(
    title="eShopCo Latency API",
    description="Serverless FastAPI endpoint deployed on Vercel for latency checks",
    version="1.0.0",
)

# Enable CORS (allow all origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------
class Query(BaseModel):
    regions: List[str]
    threshold_ms: float

# ---------------------------------------------------------------------
# Sample telemetry data (you can load from JSON file if needed)
# ---------------------------------------------------------------------
telemetry = [
    {"region": "apac", "service": "support", "latency_ms": 129.73, "uptime_pct": 98.345},
    {"region": "apac", "service": "payments", "latency_ms": 147.85, "uptime_pct": 98.423},
    {"region": "emea", "service": "support", "latency_ms": 192.12, "uptime_pct": 97.231},
    {"region": "emea", "service": "payments", "latency_ms": 177.54, "uptime_pct": 97.893},
    {"region": "americas", "service": "support", "latency_ms": 155.11, "uptime_pct": 98.911},
    {"region": "americas", "service": "payments", "latency_ms": 165.55, "uptime_pct": 99.022},
]

# ---------------------------------------------------------------------
# Helper function to compute percentile
# ---------------------------------------------------------------------
def percentile(values: List[float], p: float) -> float:
    if not values:
        return None
    values = sorted(values)
    k = math.ceil(p * len(values)) - 1
    return values[max(0, min(k, len(values) - 1))]

# ---------------------------------------------------------------------
# Main latency endpoint
# ---------------------------------------------------------------------
@app.post("/api/check-latency")
def check_latency(query: Query) -> Dict[str, Any]:
    regions_summary = {}

    for region in query.regions:
        region_data = [r for r in telemetry if r["region"] == region]
        if not region_data:
            continue

        latencies = [r["latency_ms"] for r in region_data]
        uptimes = [r["uptime_pct"] for r in region_data]
        breaches = sum(1 for l in latencies if l > query.threshold_ms)

        regions_summary[region] = {
            "avg_latency": round(sum(latencies) / len(latencies), 3),
            "p95_latency": round(percentile(latencies, 0.95), 3),
            "avg_uptime": round(sum(uptimes) / len(uptimes), 3),
            "breaches": breaches,
            "samples": len(region_data)
        }

    return {"regions": regions_summary}

# ---------------------------------------------------------------------
# Default homepage (unchanged boilerplate)
# ---------------------------------------------------------------------
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>eShopCo Latency API</title>
        <style>
            body { font-family: sans-serif; background: #000; color: #fff; text-align:center; padding:3rem; }
            a { color: #00eaff; text-decoration: none; }
            pre { background:#111; border-radius:8px; padding:1rem; text-align:left; color:#0f0; display:inline-block;}
        </style>
    </head>
    <body>
        <h1>🚀 eShopCo Latency API</h1>
        <p>Deployed on <strong>Vercel + FastAPI</strong></p>
        <p>POST endpoint:</p>
        <pre>/api/check-latency</pre>
        <p>Example body:</p>
        <pre>{
  "regions": ["apac", "emea"],
  "threshold_ms": 165
}</pre>
        <p><a href="/docs">Open Swagger UI →</a></p>
    </body>
    </html>
    """
