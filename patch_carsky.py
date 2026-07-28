import re

with open("scripts/carsky_agent.py", "r") as f:
    content = f.read()

# Define the new fallback engine text
new_fallback = """    # 2. FALLBACK: RULE-BASED ENGINE (Context-Aware)
    ego = frame.get("ego", {})
    driver = frame.get("driver", {})
    min_ttc = frame.get("min_ttc", 99.9)
    if min_ttc is None: min_ttc = 99.9
    headway = frame.get("headway_sec", 99.9)
    if headway is None: headway = 99.9
    events = frame.get("events_active", [])
    
    speed = ego.get("speed_kmh", 0)
    alertness = driver.get("alertness_score", 1.0)
    long_accel = ego.get("longitudinal_accel", 0)
    lat_accel = ego.get("lateral_accel", 0)
    
    # Nhận diện ngữ cảnh thực tế (Context-Aware)
    is_parked = (speed < 2.0)
    is_traffic_jam = (2.0 <= speed < 20.0)
    is_highway = (speed > 70.0)
    
    # --- 1. DRIVER STATE ---
    attention_penalty = (1.0 - alertness) * 25
    driver_state = driver.get("state", "")
    
    if driver_state == "distracted":
        attention_penalty += 15
    elif driver_state == "drowsy":
        attention_penalty += 25

    if history_frames:
        closed_count = sum(1 for f in history_frames if f.get("driver", {}).get("eye_state") == "closed")
        if closed_count >= 3: attention_penalty += 15
            
        yawning_count = sum(1 for f in history_frames if f.get("driver", {}).get("mouth_state") == "yawning")
        if yawning_count >= 10: attention_penalty += 35
        elif yawning_count >= 5: attention_penalty += 20
        elif yawning_count > 0: attention_penalty += 10
        
        down_count = sum(1 for f in history_frames if f.get("driver", {}).get("head_pose") == "down")
        if down_count >= 5: attention_penalty += 25
    else:
        if driver.get("eye_state") == "closed": attention_penalty += 15
        if driver.get("mouth_state") == "yawning": attention_penalty += 10
        if driver.get("head_pose") == "down": attention_penalty += 10

    # Điều chỉnh theo Bối cảnh
    if is_parked: attention_penalty *= 0.2
    elif is_traffic_jam: attention_penalty *= 0.8
    elif is_highway: attention_penalty *= 1.5
        
    # --- 2. COLLISION RISK ---
    collision_risk_penalty = 0
    if not is_parked:
        if min_ttc < 1.5: collision_risk_penalty += 35
        elif min_ttc < 2.5: collision_risk_penalty += 15
            
        # Delta TTC (Phát hiện phanh gấp)
        if history_frames and len(history_frames) >= 5:
            past_ttc = history_frames[-5].get("min_ttc")
            if past_ttc is None: past_ttc = 99.9
            if min_ttc < 3.0 and (past_ttc - min_ttc > 1.5):
                collision_risk_penalty += 40

    # --- 3. COMPOUND RISK ---
    if attention_penalty > 15 and collision_risk_penalty > 0:
        collision_risk_penalty += 20
        
    # --- 4. VEHICLE HANDLING ---
    handling_penalty = 0
    if long_accel < -3.0: handling_penalty += 20
    if abs(lat_accel) > 3.0: handling_penalty += 15

    # --- 5. LANE BEHAVIOR ---
    lane_penalty = 0
    for event in events:
        evt_type = event.get("type", event.get("event_type", "")) if isinstance(event, dict) else str(event)
        if "lane" in evt_type.lower() or "departure" in evt_type.lower():
            lane_penalty += 15
            if is_highway: lane_penalty += 15
            
    final_score = 100 - attention_penalty - collision_risk_penalty - handling_penalty - lane_penalty
    return max(0, min(100, final_score))"""

# Replace the content from # 2. FALLBACK to the end of the function (before def run_fusion_agent)
pattern = re.compile(r'    # 2\. FALLBACK: RULE-BASED ENGINE.*?return max\(0, min\(100, final_score\)\)', re.DOTALL)
new_content = pattern.sub(new_fallback, content)

with open("scripts/carsky_agent.py", "w") as f:
    f.write(new_content)

print("Patched carsky_agent.py successfully!")
