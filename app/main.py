import os
import redis
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="PulseFlow Telemetry Service", version="1.0.0")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# High-speed in-memory buffer
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


@app.get("/healthz")
def health_check():
  return {"status": "healthy", "service": "pulseflow-telemetry"}


@app.get("/api/v1/telemetry/hits")
def record_hit():
  try:
    count = r.incr("pulseflow_telemetry_hits")
    return {
        "status": "success",
        "total_hits": count,
        "datastore": f"{REDIS_HOST}:{REDIS_PORT}",
    }
  except redis.exceptions.ConnectionError:
    return {
        "status": "degraded",
        "total_hits": "Offline",
        "datastore": f"{REDIS_HOST}:{REDIS_PORT} (Unreachable)",
    }


@app.get("/", response_class=HTMLResponse)
def dashboard():
  try:
    total_hits = r.incr("pulseflow_telemetry_hits")
    db_status = "Connected"
    status_badge_color = "#22c55e"
  except redis.exceptions.ConnectionError:
    total_hits = "N/A"
    db_status = "Disconnected (Standalone Mode)"
    status_badge_color = "#eab308"

  html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PulseFlow | Cloud Telemetry Engine</title>
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: 'Montserrat', sans-serif;
            }}
            body {{
                background-color: #0b0f19;
                color: #f3f4f6;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 20px;
            }}
            .card {{
                background: rgba(18, 24, 38, 0.85);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 20px;
                padding: 40px;
                max-width: 520px;
                width: 100%;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
                text-align: center;
            }}
            .brand {{
                display: inline-flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 20px;
            }}
            .brand-dot {{
                width: 14px;
                height: 14px;
                background-color: #CC5500;
                border-radius: 50%;
                box-shadow: 0 0 14px #CC5500;
            }}
            h1 {{
                font-size: 26px;
                font-weight: 800;
                letter-spacing: 1px;
                color: #ffffff;
            }}
            p.subtitle {{
                font-size: 13px;
                color: #9ca3af;
                margin-bottom: 30px;
                text-transform: uppercase;
                letter-spacing: 1.5px;
            }}
            .metric-box {{
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 14px;
                padding: 25px;
                margin-bottom: 25px;
            }}
            .metric-label {{
                font-size: 12px;
                color: #9ca3af;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 8px;
            }}
            .metric-value {{
                font-size: 48px;
                font-weight: 800;
                color: #CC5500;
            }}
            .status-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 16px;
                background: rgba(255, 255, 255, 0.02);
                border-radius: 10px;
                margin-bottom: 10px;
                font-size: 13px;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 10px;
                border-radius: 20px;
                font-size: 11px;
                font-weight: 600;
                background-color: {status_badge_color}22;
                color: {status_badge_color};
                border: 1px solid {status_badge_color}55;
            }}
            .refresh-btn {{
                display: inline-block;
                margin-top: 20px;
                padding: 12px 28px;
                background: #CC5500;
                color: #ffffff;
                text-decoration: none;
                font-weight: 600;
                font-size: 13px;
                border-radius: 10px;
                transition: transform 0.15s ease, background 0.15s ease;
            }}
            .refresh-btn:hover {{
                background: #e05e00;
                transform: translateY(-2px);
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="brand">
                <div class="brand-dot"></div>
                <h1>PulseFlow</h1>
            </div>
            <p class="subtitle">Cloud Telemetry Engine • v1.1 Automated CI/CD</p>

            <div class="metric-box">
                <div class="metric-label">Live Ingestion Counter</div>
                <div class="metric-value">{total_hits}</div>
            </div>

            <div class="status-row">
                <span style="color: #9ca3af;">Service Status</span>
                <span class="badge">Healthy (Port 8000)</span>
            </div>

            <div class="status-row">
                <span style="color: #9ca3af;">Redis Cluster</span>
                <span class="badge">{db_status}</span>
            </div>

            <div class="status-row">
                <span style="color: #9ca3af;">Datastore Node</span>
                <span style="font-family: monospace; color: #d1d5db;">{REDIS_HOST}:{REDIS_PORT}</span>
            </div>

            <a href="/" class="refresh-btn">Simulate Telemetry Event</a>
        </div>
    </body>
    </html>
    """
  return html_content


if __name__ == "__main__":
  import uvicorn

  uvicorn.run(app, host="0.0.0.0", port=8000)