# FleetIQ Guardian Risk Pipeline Architecture

## Core Reframe

Flow brainstorm hien tai dung huong, nhung can tach thanh 3 duong doc lap:

- **Online inference:** chay on dinh de tao risk event, trip score, dashboard.
- **Model training:** dung ground truth, high-precision rules va human-verified labels de train model online.
- **Post-inference risk discovery:** cluster risk event/embedding, sau do dung LLM 4B-8B de gan semantic label cho tung cluster.

LLM khong tao training label, khong cap nhat training dataset va khong tham gia real-time inference. Vai tro duy nhat cua LLM la bien cac cluster da hoan tat thanh ten risk de Fleet Manager de doc va phan tich. Online path dung GBDT baseline hoac temporal model nhe de dam bao latency, deterministic behavior va kha nang debug.

## Final Proposed Flow

1. **Road-view model**
   - Detect/classify object quanh xe.
   - Track object theo thoi gian.
   - Uoc luong distance bang depth ROI + single-view geometry theo paper distance estimation.
   - Tinh relative velocity va relative acceleration.
   - Tinh TTC cho cac object dang closing-in.
   - Detect lane/lane offset/lane departure.
   - Output `road_context_vector`.

2. **Sensor-fusion normalizer**
   - Normalize speed, brake state, steering angle, throttle, turn signal, gear, ego acceleration.
   - Resample ve cung timestamp/frame index.
   - Tao `vehicle_state_vector`.

3. **Driver camera / DMS model**
   - Phan tich fatigue, drowsiness, distraction.
   - Detect unsafe behavior: phone use, seatbelt missing, eyes closed too long, gaze off road.
   - Smooth theo thoi gian de tranh alert nhieu.
   - Output `driver_state_vector`.

4. **Time alignment + vectorizer**
   - Gom 3 vector theo rolling window 1s/3s/5s.
   - Them confidence, missing-data flags, previous state.
   - Output `multimodal_window_vector`.

5. **Risk event detector**
   - MVP: rule seed + GBDT/LightGBM/XGBoost baseline.
   - Stretch: TCN/GRU/Tiny Transformer tren sequence multimodal.
   - Output: risk label, severity, confidence, timestamp, evidence URI.

6. **Trip scoring engine**
   - Gom risk event theo trip.
   - Merge repeated/flickering events.
   - Tinh score bang severity x duration x confidence x context multiplier.
   - Calibrate bang model hoc duoc khi co label.
   - Output: score, breakdown, coaching report.

7. **Dashboard**
   - Fleet overview.
   - Driver ranking.
   - Trip detail.
   - TTC + driver-state timeline.
   - Evidence viewer.
   - Coaching report.

## Rule-Based Co Hop Ly Khong?

Rule-based **rat hop ly cho MVP, guardrail va high-precision training labels**, nhung khong nen la final-only engine.

Ly do:

- Neu co 5 nhom signal chinh: TTC, lane, ego motion, surrounding vehicles, driver state.
- Moi nhom chi can 4-6 trang thai da co khoang 4^5 den 6^5 = 1024 den 7776 combination.
- Them context nhu intersection, turn signal, road type, weather/night, object side/front/rear thi so case tang rat nhanh.
- Rule thu cong de bi thieu edge case va kho tuning threshold.

De xuat:

- Dung **20-40 high-precision rules** de tao verified seed labels va demo explainability.
- Human review cac case mo hoac co anh huong cao truoc khi dua vao training dataset.
- Train model nhe de hoc interaction phuc tap tu cac label da duoc verify.
- Cluster risk output/embedding sau inference de tim cac pattern lap lai.
- Dung LLM 4B-8B chi de dat semantic label cho cac cluster da co.
- Giu rule layer lam guardrail cho critical cases va audit.

## Suggested Risk Classes

Nen bat dau voi 8-12 risk classes, du de cover demo nhung khong qua lon:

- `short_ttc_following`
- `near_miss_front`
- `rear_collision_risk`
- `unsafe_lane_change`
- `lane_departure_no_signal`
- `unsafe_turn_no_signal`
- `distracted_driving`
- `drowsy_driving`
- `harsh_brake_following`
- `speeding_with_close_gap`
- `side_swipe_risk`
- `compound_risk`

## Model Recommendation

### MVP Model

Use:

- rule seed features,
- LightGBM/XGBoost/GBDT-style classifier,
- calibrated probability,
- additive trip score.

Why:

- Fast.
- Works with tabular/window features.
- Easy to explain.
- Strong hackathon baseline.

### Stronger Model

Use:

- TCN or GRU over 1-5 second windows,
- multimodal feature vector per frame/window,
- attention or feature importance for explanation.

Why:

- Learns temporal patterns: closing speed, delayed brake, distraction duration.
- Easier than full video model.
- Can train from extracted features, not raw video.

### LLM Role

Use 4B-8B LLM for:

- receiving cluster summaries and representative risk samples,
- assigning a concise semantic risk label to each completed cluster,
- producing cluster metadata for analytics and dashboard display.

Avoid using LLM as:

- source of labels for model training,
- input to the training dataset,
- real-time safety judge,
- only risk detector,
- latency-critical model.

Correct order:

```text
risk events / embeddings
  -> clustering
  -> cluster summary + representative samples
  -> LLM semantic label
  -> analyst validation
  -> risk cluster catalog / dashboard analytics
```

There is no arrow from the LLM branch to model training or model registry.

## Trip Score Recommendation

Use hybrid scoring:

```text
trip_score = 100
  - road_risk_penalty
  - driver_state_penalty
  - vehicle_handling_penalty
  - lane_behavior_penalty
  + recovery_bonus
```

Each penalty:

```text
penalty = base_weight(label)
        x severity
        x duration_factor
        x confidence
        x context_multiplier
```

Examples:

- distracted + speed > 5 km/h: multiplier 1.3
- low TTC + high closing speed: multiplier 1.5
- side vehicle + sharp steering: multiplier 1.4
- braking response after TTC drop: recovery bonus

This keeps the score explainable for Fleet Manager while leaving room for learned calibration.

## Generated Diagrams

PlantUML sources:

- `docs/diagrams/00_fleetiq_overview.puml`
- `docs/diagrams/01_road_view_model.puml`
- `docs/diagrams/02_driver_dms_model.puml`
- `docs/diagrams/03_training_and_labeling_loop.puml`
- `docs/diagrams/04_trip_scoring_model.puml`
- `docs/diagrams/05_dashboard_system_architecture.puml`
- `docs/diagrams/06_risk_case_examples.puml`
- `docs/diagrams/07_deck_solution_flow.puml`

Recommended use in proposal deck:

- Use `00_fleetiq_overview` for solution overview.
- Use `07_deck_solution_flow` for the compact 16:9 deck overview.
- Use `01_road_view_model` for technical depth.
- Use `03_training_and_labeling_loop` to separate verified model training from post-hoc LLM cluster naming.
- Use `04_trip_scoring_model` for explainable trip score.
- Use `05_dashboard_system_architecture` for deployment/dashboard story.
