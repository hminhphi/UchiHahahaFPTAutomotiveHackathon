import os
import time
import math
import cv2
import numpy as np
from kuksa_client.grpc import VSSClient
import threading
import sys

# Import components from existing dashboard
import render_trip_dashboard as ui

KUKSA_HOST = os.environ.get("KUKSA_HOST", "127.0.0.1")
KUKSA_PORT = int(os.environ.get("KUKSA_PORT", 55555))

SPEED_HISTORY_LEN = 200
speed_history = np.full(SPEED_HISTORY_LEN, math.nan, dtype=np.float32)
current_alert = ""

def fetch_kuksa():
    global current_alert
    print(f"Connecting to KUKSA Databroker at {KUKSA_HOST}:{KUKSA_PORT}...")
    try:
        with VSSClient(KUKSA_HOST, KUKSA_PORT) as client:
            print("Connected! Listening for telemetry...")
            while True:
                # 1. Read Speed
                speed_dp = client.get_current_values(["Vehicle.Speed"]).get("Vehicle.Speed")
                s = speed_dp.value if speed_dp else 0.0
                
                # 2. Read Alert (may not exist locally)
                try:
                    w_dp = client.get_current_values(["Vehicle.Cabin.Infotainment.HMI.Warning"]).get("Vehicle.Cabin.Infotainment.HMI.Warning")
                    current_alert = w_dp.value if w_dp else ""
                except Exception:
                    # Tự động gán cảnh báo nếu chạy local không có schema
                    current_alert = "COLLISION_WARNING" if s > 80 else ""
                
                # Shift history
                speed_history[:-1] = speed_history[1:]
                speed_history[-1] = float(s)
                time.sleep(0.1)
    except Exception as e:
        print(f"KUKSA Client error: {e}")

def run_dashboard():
    # Bật thread nhận dữ liệu ngầm
    t = threading.Thread(target=fetch_kuksa, daemon=True)
    t.start()
    
    cv2.namedWindow("FleetIQ Live CarSky Dashboard", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("FleetIQ Live CarSky Dashboard", 1200, 700)
    
    while True:
        canvas = np.full((700, 1200, 3), ui.BG, dtype=np.uint8)
        
        # --- HEADER ---
        ui.draw_text(canvas, "FLEETIQ // LIVE EDGE-TO-CLOUD DEMO", 20, 45, ui.TEXT, 1.0, 2)
        cv2.line(canvas, (20, 65), (1180, 65), ui.GRID, 1)
        
        current_speed = speed_history[-1] if not math.isnan(speed_history[-1]) else 0.0
        
        # --- TELEMETRY PANEL ---
        ui.panel(canvas, 20, 90, 350, 180, "TELEMETRY")
        color = ui.GREEN
        if current_speed > 80:
            color = ui.RED
        elif current_speed > 60:
            color = ui.AMBER
            
        ui.draw_text(canvas, f"{current_speed:.1f}", 50, 200, color, 3.5, 4)
        ui.draw_text(canvas, "km/h", 250, 200, ui.MUTED, 1.0, 2)
        
        # --- ALERT PANEL ---
        ui.panel(canvas, 390, 90, 790, 180, "BACK-TO-CAR ALERT (VSS)")
        if current_speed > 80 or current_alert == "COLLISION_WARNING":
            cv2.rectangle(canvas, (400, 130), (1170, 260), (50, 50, 220), -1)
            # Use raw cv2.putText for custom centering inside the box
            text = "!!! COLLISION WARNING !!!"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)
            tx = 400 + (770 - tw) // 2
            ty = 130 + (130 + th) // 2
            cv2.putText(canvas, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3, cv2.LINE_AA)
        else:
            text = "ALL SYSTEMS NOMINAL"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)
            tx = 400 + (770 - tw) // 2
            ty = 130 + (130 + th) // 2
            cv2.putText(canvas, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1.2, ui.GREEN, 2, cv2.LINE_AA)
            
        # --- LIVE TIMELINE CHART ---
        ui.panel(canvas, 20, 290, 1160, 390, "LIVE SPEED TIMELINE")
        # Reuse their existing strip chart function
        ui.draw_strip_chart(
            canvas,
            (40, 340, 1120, 320),
            speed_history,
            SPEED_HISTORY_LEN - 1,
            "SPEED",
            ui.CYAN,
            fixed_range=(0, 130),
            threshold=80
        )
        
        cv2.imshow("FleetIQ Live CarSky Dashboard", canvas)
        if cv2.waitKey(100) & 0xFF == 27: # Phím ESC để thoát
            break
            
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_dashboard()
