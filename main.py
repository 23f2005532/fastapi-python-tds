from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import json

# Load telemetry once at startup
with open("telemetry.json") as f:
    telemetry_data = json.load(f)
df = pd.DataFrame(telemetry_data)

app = FastAPI(title="eShopCo Latency Metrics")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins
    allow_methods=["POST"],
    allow_headers=["*"]
)

# Request model
class MetricsRequest(BaseModel):
    regions: list[str]
    threshold_ms: float

@app.post("/api/metrics")
def compute_metrics(request: MetricsRequest):
    result = {}
    for region in request.regions:
        region_df = df[df["region"] == region]
        if region_df.empty:
            # If no data for region
            result[region] = {
                "avg_latency": None,
                "p95_latency": None,
                "avg_uptime": None,
                "breaches": 0
            }
            continue
        
        avg_latency = region_df["latency_ms"].mean()
        p95_latency = np.percentile(region_df["latency_ms"], 95)
        avg_uptime = region_df["uptime_pct"].mean()
        breaches = (region_df["latency_ms"] > request.threshold_ms).sum()

        result[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": int(breaches)
        }
    return result
