import os
import time
import gzip
import json
import logging
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FleetIQ-Guardian")

# --- AI ENGINE (TCN Model) ---
try:
    import torch
    import numpy as np
    import sys
    sys.path.append(str(Path(__file__).resolve().parent))
    from train_tcn import TCNModel, extract_features
    
    tcn_model = TCNModel(input_dim=9)
    model_path = Path(__file__).resolve().parents[1] / "models" / "tcn_risk_model.pth"
    if not model_path.exists():
        model_path = Path("/app/models/tcn_risk_model.pth")
    if model_path.exists():
        tcn_model.load_state_dict(torch.load(model_path, weights_only=True, map_location=torch.device('cpu')))
        tcn_model.eval()
        logger.info(f"[AI ENGINE] Loaded TCN Risk Model from {model_path}")
    else:
        tcn_model = None
        logger.info("[AI ENGINE] TCN weights file not found, using Context-Aware Rule Engine")
except Exception as e:
    tcn_model = None
    logger.warning(f"[AI ENGINE] TCN init fallback: {e}")
# ------------------------------

# Kuksa & Networking Configuration
KUKSA_PORT = int(os.environ.get("KUKSA_PORT", os.environ.get("KUKSA_DATA_BROKER_PORT", 55555)))
WARNING_SIGNAL = "Vehicle.Cabin.Infotainment.HMI.Warning"
SPEED_SIGNAL = "Vehicle.Speed"
HTTP_PORT = int(os.environ.get("PORT", os.environ.get("HTTP_PORT", 8080)))

# State shared between perception loop, KUKSA background sync, and HTTP Web Dashboard
current_warning_state = {
    "warning": "",
    "score": 100.0,
    "speed": 0.0,
    "min_ttc": 99.9,
    "driver_state": "attentive",
    "risk_level": "LOW (SAFE)",
    "connected": False,
    "frame_index": 0,
    "events_active": [],
    "recent_events": [],
    "history": []
}

def kuksa_sync_worker():
    """Background worker to synchronize state with KUKSA Databroker without blocking main engine."""
    candidate_hosts = []
    env_addr = os.environ.get("KUKSA_DATA_BROKER_ADDR")
    if env_addr and env_addr != "127.0.0.1":
        candidate_hosts.append(env_addr)
    env_host = os.environ.get("KUKSA_HOST")
    if env_host and env_host not in candidate_hosts:
        candidate_hosts.append(env_host)
        
    candidate_hosts.extend(["10.99.0.3", "10.99.0.14", "127.0.0.1"])

    try:
        from kuksa_client.grpc import VSSClient, Datapoint
    except ImportError:
        logger.warning("[KUKSA Worker] kuksa_client not installed, running in standalone mode.")
        return

    logger.info(f"[KUKSA Worker] Auto-discovery starting with candidate hosts: {candidate_hosts}")
    last_sent_warning = None

    while True:
        for host in candidate_hosts:
            try:
                with VSSClient(host, KUKSA_PORT) as client:
                    logger.info(f"[KUKSA Worker] Successfully connected to KUKSA Broker at {host}:{KUKSA_PORT}")
                    current_warning_state["connected"] = True
                    
                    while True:
                        target_warn = current_warning_state["warning"]
                        target_speed = current_warning_state["speed"]
                        try:
                            client.set_current_values({
                                SPEED_SIGNAL: Datapoint(float(target_speed))
                            })
                            if target_warn != last_sent_warning:
                                client.set_current_values({
                                    WARNING_SIGNAL: Datapoint(target_warn)
                                })
                                last_sent_warning = target_warn
                                if target_warn:
                                    logger.info(f"[KUKSA Event] VSS Alert Published to HMI: '{target_warn}'")
                        except Exception as write_err:
                            logger.debug(f"Kuksa write error: {write_err}")
                        time.sleep(0.5)
            except Exception:
                current_warning_state["connected"] = False
                continue
                
        time.sleep(5)

# --- WEB DASHBOARD & REST API SERVER ---
HTML_DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FleetIQ Guardian // Remote Driver Intelligence Platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090d16;
            --panel: rgba(18, 25, 41, 0.75);
            --border: rgba(255, 255, 255, 0.08);
            --accent-cyan: #00f2fe;
            --accent-blue: #4facfe;
            --green: #10b981;
            --amber: #f59e0b;
            --red: #ef4444;
            --text-primary: #f8fafc;
            --text-muted: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 24px;
            background-image: 
                radial-gradient(at 0% 0%, rgba(0, 242, 254, 0.08) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(79, 172, 254, 0.08) 0px, transparent 50%);
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 24px;
        }
        .title-group h1 {
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }
        .title-group p { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--green);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); animation: pulse 1.5s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.8); } }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }
        .card {
            background: var(--panel);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            transition: transform 0.2s, border-color 0.2s;
        }
        .card:hover { border-color: rgba(255, 255, 255, 0.2); transform: translateY(-2px); }
        .card-label { font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
        .card-value { font-size: 32px; font-weight: 700; margin-top: 8px; font-family: 'JetBrains Mono', monospace; }
        .card-sub { font-size: 12px; color: var(--text-muted); margin-top: 6px; }

        .main-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
        }
        .chart-panel {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
        }
        .panel-title { font-size: 16px; font-weight: 700; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }
        canvas#speedChart { width: 100% !important; height: 260px !important; }
        
        .events-panel {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
        }
        .alert-box {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: var(--red);
            border-radius: 12px;
            padding: 16px;
            font-weight: 700;
            text-align: center;
            font-size: 15px;
            margin-bottom: 16px;
            display: none;
            animation: alertGlow 1s infinite alternate;
        }
        @keyframes alertGlow { from { box-shadow: 0 0 10px rgba(239,68,68,0.2); } to { box-shadow: 0 0 25px rgba(239,68,68,0.6); } }
        
        .event-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            font-size: 13px;
        }
        .event-type { font-weight: 600; }
        .badge { padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; }
        .badge-low { background: rgba(16, 185, 129, 0.2); color: var(--green); }
        .badge-high { background: rgba(245, 158, 11, 0.2); color: var(--amber); }
        .badge-critical { background: rgba(239, 68, 68, 0.2); color: var(--red); }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="header">
        <div class="title-group">
            <h1>FLEETIQ GUARDIAN</h1>
            <p>Remote Driver Intelligence & Collision Risk Platform — Challenge #3 (CarSky Nydus)</p>
        </div>
        <div class="status-badge">
            <span class="status-dot"></span>
            <span id="kuksaStatus">KUKSA: CONNECTED</span>
        </div>
    </div>

    <div class="metrics-grid">
        <div class="card">
            <div class="card-label">Current Speed</div>
            <div class="card-value" id="valSpeed">0.0 <span style="font-size:16px;color:var(--text-muted)">km/h</span></div>
            <div class="card-sub">Ego Telemetry Stream</div>
        </div>
        <div class="card">
            <div class="card-label">Time-To-Collision (TTC)</div>
            <div class="card-value" id="valTTC" style="color:var(--accent-cyan)">-- s</div>
            <div class="card-sub">Multi-view Stereo & Depth Risk</div>
        </div>
        <div class="card">
            <div class="card-label">Driver State</div>
            <div class="card-value" id="valDriver" style="font-size:24px;text-transform:capitalize">Attentive</div>
            <div class="card-sub">In-cabin Attention Monitoring</div>
        </div>
        <div class="card">
            <div class="card-label">Trip Safety Score</div>
            <div class="card-value" id="valScore" style="color:var(--green)">100 / 100</div>
            <div class="card-sub" id="valRisk">LOW (SAFE)</div>
        </div>
    </div>

    <div class="main-grid">
        <div class="chart-panel">
            <div class="panel-title">
                <span>Real-Time Speed & Collision Risk Timeline</span>
                <span style="font-size:12px;color:var(--text-muted)">Updated every 500ms</span>
            </div>
            <canvas id="speedChart"></canvas>
        </div>

        <div class="events-panel">
            <div class="panel-title">Active Safety Stream & VSS Alerts</div>
            <div class="alert-box" id="alertBox">⚠️ ALERT: COLLISION_WARNING</div>
            <div id="eventsList">
                <div class="event-item">
                    <span class="event-type">Safety Engine Monitoring</span>
                    <span class="badge badge-low">NOMINAL</span>
                </div>
            </div>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('speedChart').getContext('2d');
        const speedChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Speed (km/h)',
                        data: [],
                        borderColor: '#00f2fe',
                        backgroundColor: 'rgba(0, 242, 254, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Safety Score',
                        data: [],
                        borderColor: '#10b981',
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                    y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' }, min: 0, max: 120 }
                },
                plugins: { legend: { labels: { color: '#f8fafc' } } }
            }
        });

        async function updateData() {
            try {
                const res = await fetch('/api/telemetry');
                const data = await res.json();

                document.getElementById('valSpeed').innerHTML = `${data.speed.toFixed(1)} <span style="font-size:16px;color:var(--text-muted)">km/h</span>`;
                const ttcStr = data.min_ttc > 90 ? '∞ s' : `${data.min_ttc.toFixed(1)} s`;
                document.getElementById('valTTC').innerText = ttcStr;
                
                const driverEl = document.getElementById('valDriver');
                driverEl.innerText = data.driver_state;
                driverEl.style.color = (data.driver_state === 'drowsy' || data.driver_state === 'distracted') ? 'var(--amber)' : 'var(--text-primary)';

                const scoreEl = document.getElementById('valScore');
                scoreEl.innerText = `${data.score.toFixed(1)} / 100`;
                scoreEl.style.color = data.score >= 80 ? 'var(--green)' : (data.score >= 50 ? 'var(--amber)' : 'var(--red)');
                document.getElementById('valRisk').innerText = data.risk_level;

                const alertBox = document.getElementById('alertBox');
                if (data.warning) {
                    alertBox.style.display = 'block';
                    alertBox.innerText = `⚠️ ALERT: ${data.warning}`;
                } else {
                    alertBox.style.display = 'none';
                }

                document.getElementById('kuksaStatus').innerText = data.connected ? 'KUKSA: CONNECTED' : 'KUKSA: AUTO-DISCOVERING';

                // Chart update
                if (data.history && data.history.length > 0) {
                    speedChart.data.labels = data.history.map((h, i) => `F${h.frame}`);
                    speedChart.data.datasets[0].data = data.history.map(h => h.speed);
                    speedChart.data.datasets[1].data = data.history.map(h => h.score);
                    speedChart.update('quiet');
                }
            } catch (err) {
                console.error("Fetch telemetry error:", err);
            }
        }

        setInterval(updateData, 500);
        updateData();
    </script>
</body>
</html>
"""

class FleetIQHttpHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress noisy HTTP access logs in console

    def do_GET(self):
        if self.path == "/api/telemetry":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(current_warning_state).encode("utf-8"))
        elif self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD_TEMPLATE.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def http_server_worker():
    """Background worker hosting the FleetIQ Guardian Web Dashboard & REST API."""
    try:
        server = HTTPServer(('0.0.0.0', HTTP_PORT), FleetIQHttpHandler)
        logger.info(f"[FleetIQ Dashboard] Web Server live at http://0.0.0.0:{HTTP_PORT}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"[FleetIQ Dashboard] HTTP Server error: {e}")

def generate_synthetic_frames(count=150):
    """Generate dynamic driving scenario for continuous testing."""
    frames = []
    for i in range(count):
        speed = 45.0 + 25.0 * np.sin(i / 10.0) if 'np' in globals() else 50.0
        ttc = max(1.1, 6.0 - (i % 25) * 0.25)
        driver_state = "attentive"
        if 40 <= (i % 80) <= 60:
            driver_state = "distracted"
        elif 65 <= (i % 80) <= 75:
            driver_state = "drowsy"

        frames.append({
            "ego": {
                "speed_kmh": float(speed),
                "longitudinal_accel": float(np.cos(i / 5.0) if 'np' in globals() else 0.0),
                "lateral_accel": float(np.sin(i / 8.0) if 'np' in globals() else 0.0)
            },
            "driver": {
                "state": driver_state,
                "alertness_score": 0.95 if driver_state == "attentive" else (0.4 if driver_state == "distracted" else 0.2),
                "eye_state": "open" if driver_state == "attentive" else "closed",
                "mouth_state": "yawning" if driver_state == "drowsy" else "normal",
                "head_pose": "down" if driver_state == "distracted" else "forward"
            },
            "min_ttc": float(ttc),
            "headway_sec": float(ttc * 0.8),
            "events_active": ["lane_departure"] if (i % 35 == 0) else []
        })
    return frames

def compute_trip_score(frame, history_frames=None):
    """Trip Safety Score Engine: fuses perception, driver state, handling and TTC."""
    if tcn_model is not None and history_frames is not None and len(history_frames) >= 29:
        try:
            frames_window = history_frames[-29:] + [frame]
            X_seq = [extract_features(f) for f in frames_window]
            X_tensor = torch.tensor(np.array([X_seq]), dtype=torch.float32)
            with torch.no_grad():
                return float(tcn_model(X_tensor).item())
        except Exception:
            pass

    ego = frame.get("ego", {})
    driver = frame.get("driver", {})
    min_ttc = frame.get("min_ttc", 99.9) or 99.9
    events = frame.get("events_active", [])
    
    speed = ego.get("speed_kmh", 0)
    alertness = driver.get("alertness_score", 1.0)
    long_accel = ego.get("longitudinal_accel", 0)
    lat_accel = ego.get("lateral_accel", 0)
    
    is_parked = (speed < 2.0)
    is_traffic_jam = (2.0 <= speed < 20.0)
    is_highway = (speed > 70.0)
    
    # 1. Attention Penalty
    attention_penalty = (1.0 - alertness) * 25
    driver_state = driver.get("state", "")
    if driver_state == "distracted":
        attention_penalty += 15
    elif driver_state == "drowsy":
        attention_penalty += 25

    if is_parked: attention_penalty *= 0.2
    elif is_traffic_jam: attention_penalty *= 0.8
    elif is_highway: attention_penalty *= 1.5
        
    # 2. Collision Risk Penalty
    collision_risk_penalty = 0
    if not is_parked:
        if min_ttc < 1.5: collision_risk_penalty += 35
        elif min_ttc < 2.5: collision_risk_penalty += 15
            
        if history_frames and len(history_frames) >= 5:
            past_ttc = history_frames[-5].get("min_ttc") or 99.9
            if min_ttc < 3.0 and (past_ttc - min_ttc > 1.5):
                collision_risk_penalty += 30

    # 3. Compound Risk
    if attention_penalty > 15 and collision_risk_penalty > 0:
        collision_risk_penalty += 20
        
    # 4. Vehicle Handling
    handling_penalty = 0
    if long_accel < -3.0: handling_penalty += 20
    if abs(lat_accel) > 3.0: handling_penalty += 15

    # 5. Lane Behavior
    lane_penalty = 0
    for event in events:
        evt_type = event.get("type", event.get("event_type", "")) if isinstance(event, dict) else str(event)
        if "lane" in evt_type.lower() or "departure" in evt_type.lower():
            lane_penalty += 15
            if is_highway: lane_penalty += 15
            
    final_score = 100 - attention_penalty - collision_risk_penalty - handling_penalty - lane_penalty
    return max(0.0, min(100.0, final_score))

def run_fusion_agent():
    logger.info("==========================================================")
    logger.info("  FleetIQ Guardian: Driver Intelligence & Safety Engine   ")
    logger.info("  Challenge #3 - Connected Car Platform (CarSky Nydus)   ")
    logger.info("==========================================================")
    
    # Start KUKSA background sync worker
    t_kuksa = threading.Thread(target=kuksa_sync_worker, daemon=True)
    t_kuksa.start()

    # Start HTTP Web Dashboard & REST API server
    t_http = threading.Thread(target=http_server_worker, daemon=True)
    t_http.start()

    # Load dataset if present
    dataset_candidates = [
        Path("data/Practice_Dataset/Practice_Dataset/T01-Sample/T01-Sample.json.gz"),
        Path("/app/data/T01-Sample.json.gz"),
        Path("data/T01-Sample.json.gz")
    ]
    
    frames = None
    for p in dataset_candidates:
        if p.exists():
            try:
                logger.info(f"Loading trip dataset from {p}...")
                with gzip.open(p, "rt", encoding="utf-8") as f:
                    data = json.load(f)
                frames = data.get("frames", [])
                logger.info(f"Loaded {len(frames)} frames from {p}")
                break
            except Exception as e:
                logger.warning(f"Error loading dataset from {p}: {e}")

    if not frames:
        logger.info("Generating synthetic real-time telemetry stream...")
        frames = generate_synthetic_frames(150)

    logger.info("FleetIQ Guardian Safety Stream Active. Processing frames...")
    
    cycle = 0
    while True:
        cycle += 1
        for index, frame in enumerate(frames):
            history = frames[max(0, index - 30):index]
            score = compute_trip_score(frame, history_frames=history)
            speed = frame.get("ego", {}).get("speed_kmh", 0)
            driver_state = frame.get("driver", {}).get("state", "attentive")
            min_ttc = frame.get("min_ttc", 99.9) or 99.9
            
            # Risk Level evaluation
            if score >= 80:
                risk_level = "LOW (SAFE)"
                warning = ""
            elif score >= 60:
                risk_level = "MEDIUM (CAUTION)"
                warning = "CAUTION"
            elif score >= 40:
                risk_level = "HIGH (RISK)"
                warning = "DROWSINESS_ALERT" if driver_state in ["drowsy", "distracted"] else "COLLISION_WARNING"
            else:
                risk_level = "CRITICAL (DANGER)"
                warning = "CRITICAL_COLLISION_ALERT"

            # Update shared state for background KUKSA synchronization & Web Dashboard
            current_warning_state["warning"] = warning
            current_warning_state["score"] = score
            current_warning_state["speed"] = speed
            current_warning_state["min_ttc"] = min_ttc
            current_warning_state["driver_state"] = driver_state
            current_warning_state["risk_level"] = risk_level
            current_warning_state["frame_index"] = index

            # Append to history for real-time dashboard charts
            history_list = current_warning_state["history"]
            history_list.append({"frame": index, "speed": speed, "score": score, "ttc": min_ttc})
            if len(history_list) > 40:
                history_list.pop(0)

            status_icon = "🟢" if score >= 80 else ("🟡" if score >= 60 else ("🟠" if score >= 40 else "🔴"))
            kuksa_status = "[KUKSA: CONNECTED]" if current_warning_state["connected"] else "[KUKSA: SYNCING]"

            alert_suffix = f" -> ⚠️ ALERT: {warning}" if warning else ""
            logger.info(f"{status_icon} [FleetIQ F{index:04d}] Spd: {speed:4.1f} km/h | TTC: {min_ttc:4.1f}s | Driver: {driver_state:<10} | Score: {score:5.1f}/100 | {risk_level} {kuksa_status}{alert_suffix}")

            time.sleep(0.5)
            
        logger.info(f"--- Completed Trip Cycle #{cycle}. Looping telemetry stream ---")
        time.sleep(1)

if __name__ == "__main__":
    run_fusion_agent()
