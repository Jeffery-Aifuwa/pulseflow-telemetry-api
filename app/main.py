import os
import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import redis
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="PulseFlow Telemetry Engine")

# Expose standard Prometheus metrics
Instrumentator().instrument(app).expose(app)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_connect_timeout=2)
except Exception:
    r = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>PulseFlow Telemetry</title>
  <style>
    body { background-color: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
    .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 32px; width: 420px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); text-align: center; }
    h1 { color: #58a6ff; margin-bottom: 8px; font-size: 24px; }
    p.subtitle { color: #8b949e; margin-top: 0; font-size: 14px; }
    .counter { font-size: 48px; font-weight: bold; color: #3fb950; margin: 24px 0; }
    .status { font-size: 13px; padding: 6px 12px; border-radius: 20px; display: inline-block; }
    .online { background: rgba(56, 139, 253, 0.15); color: #58a6ff; border: 1px solid rgba(56, 139, 253, 0.4); }
  </style>
</head>
<body>
  <div class="card">
    <h1>PulseFlow Telemetry</h1>
    <p class="subtitle">Cloud Telemetry Engine • v1.2 Observability Active</p>
    <div class="counter">{{ count }}</div>
    <p>Telemetry Ingestion Events Processed</p>
    <div class="status online">● Redis: {{ redis_status }}</div>
  </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    count = "N/A"
    redis_status = "Disconnected"
    if r:
        try:
            count = r.incr("telemetry:events:count")
            redis_status = f"Connected ({REDIS_HOST}:{REDIS_PORT})"
        except Exception:
            redis_status = "Connection Failed"
    
    html = HTML_TEMPLATE.replace("{{ count }}", str(count)).replace("{{ redis_status }}", redis_status)
    return HTMLResponse(content=html)

@app.get("/healthz")
async def healthz():
    return {"status": "healthy", "timestamp": time.time()}