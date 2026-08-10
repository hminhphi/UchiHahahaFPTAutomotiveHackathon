/* Generate the judge-facing FleetIQ Guardian final deck from verified evidence. */

const path = require("node:path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "../..");
const OUTPUT = path.join(ROOT, "docs/proposal/UchiHahaha_FleetIQGuardian_Final_R2.pptx");
const ASSET = (...parts) => path.join(ROOT, ...parts);

const image = {
  fleet: ASSET("docs/proposal/assets/fleet-overview.png"),
  trip: ASSET("docs/proposal/assets/t01d-trip-detail.png"),
  motorcycle: ASSET("docs/proposal/assets/t01d-motorcycle-evidence.png"),
  motorcycleCrop: ASSET("docs/proposal/assets/t01d-motorcycle-crop.png"),
  comparison: ASSET("docs/proposal/assets/label-comparison.png"),
};

const C = {
  navy: "19226D",
  ink: "0B1020",
  blue: "034EA2",
  brightBlue: "147DF5",
  orange: "F37021",
  white: "FFFFFF",
  panel: "F4F7FC",
  paleBlue: "DCE9FA",
  paleOrange: "FFF0E5",
  muted: "6B7A90",
  line: "CDCCCC",
  success: "22B573",
};

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "UchiHahaha";
pptx.company = "UchiHahaha";
pptx.subject = "Automotive Hackathon 2026 - FleetIQ Guardian";
pptx.title = "FleetIQ Guardian - Final Round 2";
pptx.lang = "vi-VN";
pptx.theme = {
  headFontFace: "Quattrocento Sans",
  bodyFontFace: "Quattrocento Sans",
  lang: "vi-VN",
};
pptx.defineLayout({ name: "FLEETIQ", width: 13.333, height: 7.5 });
pptx.layout = "FLEETIQ";

const S = pptx.ShapeType;
const W = 13.333;
const H = 7.5;

function addText(slide, text, options = {}) {
  slide.addText(text, {
    fontFace: "Quattrocento Sans",
    margin: 0,
    breakLine: false,
    ...options,
  });
}

function rect(slide, x, y, w, h, fill, line = fill, extra = {}) {
  slide.addShape(S.rect, {
    x,
    y,
    w,
    h,
    fill: { color: fill },
    line: { color: line, transparency: line === fill ? 100 : 0, width: 0.6 },
    ...extra,
  });
}

function card(slide, x, y, w, h, accent = C.blue, fill = C.white) {
  rect(slide, x, y, w, h, fill, C.line);
  rect(slide, x, y, 0.08, h, accent, accent);
}

function footer(slide, number, dark = false) {
  const color = dark ? "AFC6EA" : C.muted;
  slide.addShape(S.line, {
    x: 0.55,
    y: 7.08,
    w: 12.23,
    h: 0,
    line: { color: dark ? "47628E" : C.line, width: 0.5 },
  });
  addText(slide, "UchiHahaha | FleetIQ Guardian | Automotive Hackathon 2026", {
    x: 0.58,
    y: 7.18,
    w: 8.8,
    h: 0.16,
    fontSize: 7.5,
    color,
  });
  addText(slide, String(number).padStart(2, "0"), {
    x: 12.05,
    y: 7.12,
    w: 0.7,
    h: 0.2,
    fontSize: 9,
    bold: true,
    color: dark ? C.orange : C.blue,
    align: "right",
  });
}

function heading(slide, number, kicker, title, subtitle = "") {
  slide.background = { color: C.panel };
  rect(slide, 0, 0, W, 0.18, C.orange);
  addText(slide, kicker.toUpperCase(), {
    x: 0.6,
    y: 0.48,
    w: 5.6,
    h: 0.18,
    fontSize: 9,
    bold: true,
    color: C.orange,
    charSpacing: 1.4,
  });
  addText(slide, title, {
    x: 0.58,
    y: 0.76,
    w: 11.9,
    h: 0.55,
    fontSize: 28,
    bold: true,
    color: C.navy,
    fit: "shrink",
  });
  if (subtitle) {
    addText(slide, subtitle, {
      x: 0.6,
      y: 1.4,
      w: 11.6,
      h: 0.28,
      fontSize: 11,
      color: C.muted,
      fit: "shrink",
    });
  }
  footer(slide, number);
}

function label(slide, text, x, y, w, color = C.blue) {
  rect(slide, x, y, w, 0.28, color);
  addText(slide, text.toUpperCase(), {
    x: x + 0.12,
    y: y + 0.07,
    w: w - 0.24,
    h: 0.11,
    fontSize: 7.5,
    bold: true,
    color: C.white,
    align: "center",
    charSpacing: 0.7,
  });
}

function stat(slide, value, caption, x, y, w, accent = C.orange, dark = false) {
  const color = dark ? C.white : C.navy;
  addText(slide, value, {
    x,
    y,
    w,
    h: 0.55,
    fontSize: 31,
    bold: true,
    color: accent,
    fit: "shrink",
  });
  addText(slide, caption.toUpperCase(), {
    x,
    y: y + 0.62,
    w,
    h: 0.32,
    fontSize: 8.5,
    bold: true,
    color,
    charSpacing: 0.8,
    fit: "shrink",
  });
}

function source(slide, text, dark = false) {
  addText(slide, text, {
    x: 0.6,
    y: 6.75,
    w: 10.8,
    h: 0.14,
    fontSize: 6.6,
    color: dark ? "AFC6EA" : C.muted,
    italic: true,
    fit: "shrink",
  });
}

// 01. Cover
{
  const slide = pptx.addSlide();
  slide.background = { color: C.navy };
  rect(slide, 6.72, 1.2, 5.92, 3.68, "21367E", "47628E");
  slide.addImage({ path: image.fleet, x: 6.86, y: 1.34, w: 5.64, h: 3.17 });
  label(slide, "LIVE OPS CONSOLE", 8.57, 4.51, 1.95, C.blue);
  label(slide, "FINAL ROUND 2 | v1.0.0", 0.65, 0.68, 2.35, C.orange);
  addText(slide, "FLEETIQ\nGUARDIAN", {
    x: 0.65,
    y: 1.28,
    w: 5.2,
    h: 1.3,
    fontSize: 39,
    bold: true,
    color: C.white,
    breakLine: true,
    fit: "shrink",
  });
  addText(slide, "Remote Driver Intelligence & Collision Risk Platform", {
    x: 0.68,
    y: 2.87,
    w: 5.15,
    h: 0.46,
    fontSize: 18,
    color: "DCE9FA",
    bold: true,
    fit: "shrink",
  });
  addText(slide, "Challenge #3: Driver Intelligence Platform\nChallenge #1 scoring + Challenge #2 TTC as core engines", {
    x: 0.68,
    y: 3.58,
    w: 5.4,
    h: 0.64,
    fontSize: 12.5,
    color: "AFC6EA",
    breakLine: true,
  });
  rect(slide, 0.68, 4.62, 4.82, 1.32, "21367E", "47628E");
  stat(slide, "10", "blind-test trips ranked", 0.95, 4.82, 1.15, C.orange, true);
  stat(slide, "17,999", "custom YOLO labels", 2.32, 4.82, 1.75, C.brightBlue, true);
  stat(slide, "1", "auditable risk view", 4.42, 4.82, 0.82, C.success, true);
  addText(slide, "Team UchiHahaha | Phi, Trung, Dung, Kha, Tu", {
    x: 0.68,
    y: 6.2,
    w: 5.5,
    h: 0.22,
    fontSize: 10.5,
    color: C.white,
    bold: true,
  });
  source(slide, "Live local dashboard screenshot, build v1.0.0", true);
  footer(slide, 1, true);
}

// 02. Rubric alignment
{
  const slide = pptx.addSlide();
  heading(slide, 2, "Why FleetIQ can be verified", "KHONG CHI LA AI: DAY LA WORKFLOW CO BANG CHUNG", "Mỗi claim được map tới output, route/API, artifact và limitation để BGK kiểm tra nhanh.");
  const cards = [
    ["01", "INNOVATION", "Fusion road risk + driver state + telemetry into one evidence-first decision.", C.orange],
    ["02", "FEASIBILITY", "Custom detector, deterministic fusion, Docker Compose and static artifact fallback.", C.blue],
    ["03", "TECHNICAL DEPTH", "Stereo/depth TTC proxy, DMS state, event schema, API replay and CSV output.", C.brightBlue],
    ["04", "BUSINESS VALUE", "Fleet ranking, incident review and targeted coaching instead of raw video review.", C.success],
  ];
  cards.forEach(([number, title, body, accent], index) => {
    const x = 0.68 + (index % 2) * 6.05;
    const y = 2.0 + Math.floor(index / 2) * 2.1;
    card(slide, x, y, 5.52, 1.62, accent);
    addText(slide, number, { x: x + 0.34, y: y + 0.28, w: 0.55, h: 0.32, fontSize: 21, bold: true, color: accent });
    addText(slide, title, { x: x + 1.0, y: y + 0.32, w: 4.08, h: 0.22, fontSize: 12, bold: true, color: C.navy, charSpacing: 0.7 });
    addText(slide, body, { x: x + 1.0, y: y + 0.76, w: 4.05, h: 0.54, fontSize: 10.5, color: C.muted, fit: "shrink" });
  });
  rect(slide, 0.68, 6.05, 11.56, 0.5, C.navy);
  addText(slide, "REVIEW PATH: dashboard -> risky trip -> synchronized evidence -> score explanation -> coaching context", {
    x: 0.95, y: 6.21, w: 11.0, h: 0.15, fontSize: 10, color: C.white, bold: true, align: "center", charSpacing: 0.25,
  });
}

// 03. Dataset signals
{
  const slide = pptx.addSlide();
  heading(slide, 3, "Data advantage", "5 LUONG TIN HIEU, 1 QUYET DINH VAN HANH", "Challenge #3 dùng trọn bộ dữ liệu thay vì biến một model đơn lẻ thành sản phẩm.");
  const signals = [
    ["ROAD", "Stereo road cameras", "Object + context", C.blue],
    ["DRIVER", "In-cabin camera", "Attention state", C.orange],
    ["DEPTH", "Depth + calibration", "Distance / TTC", C.brightBlue],
    ["TELEMETRY", "Vehicle signals", "Speed + handling", C.navy],
    ["LABELS", "GT / fusion metadata", "Validate + align", C.success],
  ];
  signals.forEach(([tag, title, body, accent], index) => {
    const x = 0.66 + index * 2.47;
    card(slide, x, 2.04, 2.16, 1.65, accent);
    label(slide, tag, x + 0.22, 2.3, 1.72, accent);
    addText(slide, title, { x: x + 0.22, y: 2.79, w: 1.72, h: 0.28, fontSize: 10.5, bold: true, color: C.navy, align: "center", fit: "shrink" });
    addText(slide, body, { x: x + 0.22, y: 3.19, w: 1.72, h: 0.16, fontSize: 8.5, color: C.muted, align: "center", fit: "shrink" });
  });
  rect(slide, 0.68, 4.32, 11.56, 1.55, C.navy);
  stat(slide, "17,999", "custom road-object labels", 1.05, 4.72, 2.1, C.orange, true);
  stat(slide, "10", "scored trips in fleet view", 4.35, 4.72, 1.25, C.brightBlue, true);
  stat(slide, "1,800", "frames per submission file", 6.38, 4.72, 1.9, C.success, true);
  stat(slide, "5", "accepted driver states", 9.52, 4.72, 1.1, C.orange, true);
  source(slide, "Inputs: organizer starter kit; output contract: predictions/UchiHahaha/T01d.csv ... T10d.csv");
}

// 04. Problem
{
  const slide = pptx.addSlide();
  heading(slide, 4, "Fleet manager problem", "RAW VIDEO KHONG PHAT SINH QUYET DINH AN TOAN", "Fleet manager cần biết xe nào rủi ro, vì sao, lúc nào và hành động tiếp theo là gì.");
  const problems = [
    ["01", "DATA PHAN MANH", "Camera, DMS, depth và telemetry nằm ở luồng riêng; reviewer không thể kể lại sự kiện."],
    ["02", "ALERT THIEU NGU CANH", "Một TTC đơn lẻ hoặc một frame DMS không đủ để đánh giá mức độ rủi ro."],
    ["03", "KHONG CO EVIDENCE", "Không có timestamp, score impact và visual evidence thì coaching không thể audit."],
  ];
  problems.forEach(([number, title, body], index) => {
    const x = 0.72 + index * 4.08;
    rect(slide, x, 2.1, 3.57, 3.24, index === 1 ? C.navy : C.white, index === 1 ? C.navy : C.line);
    addText(slide, number, { x: x + 0.32, y: 2.44, w: 0.55, h: 0.32, fontSize: 23, bold: true, color: index === 1 ? C.orange : C.blue });
    addText(slide, title, { x: x + 0.32, y: 3.1, w: 2.72, h: 0.35, fontSize: 13, bold: true, color: index === 1 ? C.white : C.navy, fit: "shrink" });
    addText(slide, body, { x: x + 0.32, y: 3.78, w: 2.8, h: 0.76, fontSize: 10.5, color: index === 1 ? "DCE9FA" : C.muted, fit: "shrink" });
    rect(slide, x + 0.32, 4.9, 0.92, 0.08, index === 1 ? C.orange : C.brightBlue);
  });
  addText(slide, "FLEETIQ BIEN 'NHIEU TIN HIEU' THANH 'MOT QUYET DINH CO THE KIEM TRA'", {
    x: 0.9, y: 5.94, w: 11.3, h: 0.3, fontSize: 15, bold: true, color: C.orange, align: "center", fit: "shrink",
  });
}

// 05. Dashboard
{
  const slide = pptx.addSlide();
  heading(slide, 5, "Fleet overview", "RISK, RANKED FOR ACTION", "Trang đầu tiên là operations console: đội xe được xếp theo severity và safety score, không phải landing page.");
  card(slide, 0.68, 2.0, 4.03, 3.85, C.orange, C.white);
  label(slide, "LIVE FLEET VIEW", 1.03, 2.36, 1.8, C.orange);
  addText(slide, "Một màn hình để chọn đúng trip cần xem trước.", { x: 1.03, y: 2.92, w: 3.08, h: 0.62, fontSize: 17, bold: true, color: C.navy, fit: "shrink" });
  addText(slide, "Mỗi card nối score, speed, driver state và trigger sự kiện. Reviewer có thể drill-down trực tiếp vào evidence.", { x: 1.03, y: 3.72, w: 3.05, h: 0.78, fontSize: 10.5, color: C.muted, fit: "shrink" });
  stat(slide, "10", "active trips", 1.03, 4.82, 0.78, C.blue);
  stat(slide, "08", "critical now", 2.15, 4.82, 0.95, C.orange);
  stat(slide, "60", "fleet score", 3.35, 4.82, 0.75, C.brightBlue);
  rect(slide, 5.05, 1.95, 7.58, 4.27, C.ink, C.ink);
  slide.addImage({ path: image.fleet, x: 5.18, y: 2.08, w: 7.32, h: 4.01 });
  source(slide, "Live local Docker dashboard screenshot: http://localhost:3000/ | build v1.0.0");
}

// 06. Trip drill-down
{
  const slide = pptx.addSlide();
  heading(slide, 6, "Trip drill-down", "T01d: SCORE -> EVENT -> EVIDENCE", "Trip report giữ evidence navigation, replay và score explanation trên cùng luồng review.");
  rect(slide, 0.65, 1.95, 8.17, 4.63, C.ink, C.ink);
  slide.addImage({ path: image.trip, x: 0.76, y: 2.06, w: 7.95, h: 4.41 });
  const callouts = [
    ["57/100", "Safety score", "Risk card gives a reviewer one starting signal."],
    ["4/5", "Current risk", "Severity is traceable to road, driver and telemetry artifacts."],
    ["2", "Frame-linked events", "Harsh brake and fast corner point to specific frame ranges."],
  ];
  callouts.forEach(([value, title, body], index) => {
    const y = 2.03 + index * 1.45;
    card(slide, 9.15, y, 3.1, 1.12, index === 1 ? C.orange : C.blue);
    addText(slide, value, { x: 9.46, y: y + 0.24, w: 1.28, h: 0.32, fontSize: 20, bold: true, color: index === 1 ? C.orange : C.blue, fit: "shrink" });
    addText(slide, title.toUpperCase(), { x: 10.88, y: y + 0.27, w: 0.98, h: 0.18, fontSize: 7.2, bold: true, color: C.navy, fit: "shrink" });
    addText(slide, body, { x: 9.46, y: y + 0.68, w: 2.3, h: 0.25, fontSize: 7.7, color: C.muted, fit: "shrink" });
  });
  source(slide, "Live local Docker dashboard screenshot: /trips/T01d | actual UI state is shown, including any N/A detail fields.");
}

// 07. Object evidence
{
  const slide = pptx.addSlide();
  heading(slide, 7, "Evidence-first perception", "MOTORCYCLE EVIDENCE, NOT A BLACK-BOX ALERT", "Frame 551 turns a model output into an inspectable road-risk record.");
  rect(slide, 0.68, 2.0, 6.58, 3.69, C.ink, C.ink);
  slide.addImage({ path: image.motorcycle, x: 0.8, y: 2.62, w: 3.5, h: 1.97 });
  slide.addImage({ path: image.motorcycleCrop, x: 4.62, y: 2.29, w: 2.4, h: 2.5 });
  label(slide, "SCENE", 1.06, 4.8, 0.86, C.blue);
  label(slide, "ENLARGED TARGET", 4.85, 4.8, 1.75, C.orange);
  card(slide, 7.66, 2.0, 4.62, 1.02, C.orange);
  addText(slide, "Motorcycle", { x: 7.98, y: 2.28, w: 1.7, h: 0.26, fontSize: 17, bold: true, color: C.navy });
  addText(slide, "confidence 0.3941", { x: 9.85, y: 2.35, w: 1.8, h: 0.15, fontSize: 9, color: C.muted, bold: true });
  card(slide, 7.66, 3.31, 4.62, 1.02, C.blue);
  addText(slide, "5.02 m", { x: 7.98, y: 3.59, w: 1.42, h: 0.26, fontSize: 17, bold: true, color: C.blue });
  addText(slide, "depth ROI estimate", { x: 9.85, y: 3.66, w: 1.8, h: 0.15, fontSize: 9, color: C.muted, bold: true });
  rect(slide, 7.66, 4.62, 4.62, 1.07, C.paleOrange, C.orange);
  addText(slide, "DISCLOSURE", { x: 7.98, y: 4.87, w: 1.0, h: 0.14, fontSize: 8, bold: true, color: C.orange, charSpacing: 0.8 });
  addText(slide, "The same frame has an overlapping pedestrian false positive. We keep it visible rather than hide it.", { x: 7.98, y: 5.1, w: 3.83, h: 0.28, fontSize: 8.6, color: C.navy, fit: "shrink" });
  source(slide, "artifacts/trips/T01d/analysis/road/000551.json | label2_yolo_v3/000551.txt | rendered evidence frame");
}

// 08. Architecture
{
  const slide = pptx.addSlide();
  heading(slide, 8, "System architecture", "FROM SENSORS TO A FLEET ACTION", "The intelligence layer carries one event schema: severity, confidence, score impact, explanation and evidence.");
  const bands = [
    ["01 INPUTS", ["Road stereo", "Driver camera", "Depth + calib", "Telemetry + labels"], C.blue, 1.85],
    ["02 ENGINES", ["TTC proxy", "Driver state", "Handling events", "Trip scoring"], C.orange, 3.03],
    ["03 INTELLIGENCE", ["Canonical events", "Fusion", "Risk score", "Evidence link"], C.navy, 4.21],
    ["04 OUTPUTS", ["Fleet ranking", "Trip detail", "Coach context", "CSV/report"], C.success, 5.39],
  ];
  bands.forEach(([title, items, accent, y], bandIndex) => {
    label(slide, title, 0.7, y + 0.26, 1.6, accent);
    items.forEach((item, index) => {
      const x = 2.62 + index * 2.37;
      rect(slide, x, y, 1.94, 0.77, C.white, C.line);
      addText(slide, item, { x: x + 0.12, y: y + 0.27, w: 1.7, h: 0.16, fontSize: 9.2, bold: true, color: C.navy, align: "center", fit: "shrink" });
      if (bandIndex < bands.length - 1) {
        slide.addShape(S.line, { x: x + 0.97, y: y + 0.78, w: 0, h: 0.28, line: { color: accent, width: 1.4, beginArrowType: "none", endArrowType: "triangle" } });
      }
    });
  });
  source(slide, "Runtime: precomputed artifacts -> FastAPI -> Next.js | Workers use bounded JSON/JSONL and compose profiles.");
}

// 09. Evaluation
{
  const slide = pptx.addSlide();
  heading(slide, 9, "Practice-trip evaluation", "IMPROVE ERROR AND RECALL; DISCLOSE THE TRADE-OFF", "Organizer evaluation on full-GT T01-Sample only. This is not a blind-test score for T01d-T10d.");
  card(slide, 0.7, 2.0, 5.6, 3.7, C.blue);
  addText(slide, "CRITICAL TTC MAE", { x: 1.05, y: 2.37, w: 2.4, h: 0.18, fontSize: 10, bold: true, color: C.navy, charSpacing: 0.8 });
  addText(slide, "58.595s", { x: 1.05, y: 2.82, w: 1.55, h: 0.42, fontSize: 24, bold: true, color: C.muted });
  addText(slide, "Organizer SGBM baseline", { x: 1.05, y: 3.3, w: 1.92, h: 0.18, fontSize: 8.5, color: C.muted });
  rect(slide, 3.13, 2.85, 2.55, 0.32, "D7E0ED");
  rect(slide, 3.13, 3.55, 0.85, 0.32, C.orange);
  addText(slide, "19.612s", { x: 1.05, y: 3.82, w: 1.55, h: 0.42, fontSize: 24, bold: true, color: C.orange });
  addText(slide, "Custom detector + depth ROI", { x: 1.05, y: 4.29, w: 2.05, h: 0.18, fontSize: 8.5, color: C.muted });
  addText(slide, "66.5% lower critical-zone MAE", { x: 3.13, y: 4.23, w: 2.3, h: 0.2, fontSize: 10, bold: true, color: C.orange, fit: "shrink" });
  card(slide, 6.63, 2.0, 5.65, 3.7, C.orange);
  addText(slide, "CRITICAL TTC F1", { x: 6.98, y: 2.37, w: 2.2, h: 0.18, fontSize: 10, bold: true, color: C.navy, charSpacing: 0.8 });
  stat(slide, "0.125", "baseline", 6.98, 2.84, 1.22, C.muted);
  stat(slide, "0.240", "custom", 9.15, 2.84, 1.22, C.orange);
  rect(slide, 6.98, 4.42, 4.72, 0.78, C.paleOrange, C.orange);
  addText(slide, "TTC composite: 30.6 baseline vs 28.3 custom", { x: 7.23, y: 4.64, w: 4.2, h: 0.16, fontSize: 10, bold: true, color: C.navy, align: "center" });
  addText(slide, "Reason: custom path has higher false-positive rate (0.058 vs 0.008).", { x: 7.08, y: 5.02, w: 4.52, h: 0.16, fontSize: 8.2, color: C.muted, align: "center", fit: "shrink" });
  source(slide, "artifacts/evaluation/T01-Sample_baseline_evaluation.json | T01-Sample_custom_evaluation.json");
}

// 10. Team-owned delta
{
  const slide = pptx.addSlide();
  heading(slide, 10, "Team-owned delta", "BTC CUNG CAP DATA; UCHiHAHAHA CUNG CAP WORKFLOW", "Giá trị không nằm ở việc gọi một model, mà ở integration để Fleet Manager hành động được.");
  card(slide, 0.72, 2.04, 5.4, 3.92, C.muted, C.white);
  label(slide, "STARTER / BASELINE", 1.04, 2.36, 1.82, C.muted);
  ["Road, driver, depth, calibration, telemetry", "Team-kit fixed-ROI StereoSGBM baseline", "Redacted scored-trip ground truth", "YOLOP road/lane segmentation"].forEach((item, index) => {
    rect(slide, 1.07, 2.98 + index * 0.61, 0.16, 0.16, C.muted);
    addText(slide, item, { x: 1.43, y: 2.95 + index * 0.61, w: 4.1, h: 0.23, fontSize: 10.2, color: C.navy, fit: "shrink" });
  });
  card(slide, 6.6, 2.04, 5.98, 3.92, C.orange, C.white);
  label(slide, "TEAM-OWNED", 6.92, 2.36, 1.48, C.orange);
  ["17,999 custom YOLO v3 labels + selected checkpoint", "Road/DMS/fusion artifacts and depth-TTC evidence", "Fleet ranking, replay, video-range and overlay routes", "Submission exporter, validator, evaluation evidence and package"].forEach((item, index) => {
    rect(slide, 6.95, 2.98 + index * 0.61, 0.16, 0.16, C.orange);
    addText(slide, item, { x: 7.31, y: 2.95 + index * 0.61, w: 4.62, h: 0.23, fontSize: 10.2, color: C.navy, fit: "shrink" });
  });
  rect(slide, 0.72, 6.25, 11.86, 0.4, C.navy);
  addText(slide, "REMOVE OUR INTEGRATION -> raw data remains, but the reviewer loses ranked risk, synchronized evidence and auditable CSV outputs.", {
    x: 0.96, y: 6.37, w: 11.38, h: 0.13, fontSize: 8.7, color: C.white, bold: true, align: "center", fit: "shrink",
  });
}

// 11. Deployment / team
{
  const slide = pptx.addSlide();
  heading(slide, 11, "Deployable by design", "DEMO HAY HANDOFF: CUNG MOT BUILD, CUNG MOT EVIDENCE", "Release v1.0.0 separates source, organizer data and runtime artifacts so reviewers can rerun the final workflow.");
  const columns = [
    ["RUN", "Docker Compose", "API, web, MinIO, Redis, PostgreSQL, MQTT, model mock and CarSky bridge.", C.blue],
    ["REVIEW", "Evidence package", "Models, trip artifacts, evaluator reports, predictions and SHA-256 manifest.", C.orange],
    ["SCALE", "OEM / fleet path", "Input, engine, intelligence and output layers can expand without replacing the workflow.", C.success],
  ];
  columns.forEach(([tag, title, body, accent], index) => {
    const x = 0.73 + index * 4.08;
    card(slide, x, 2.08, 3.54, 2.42, accent);
    label(slide, tag, x + 0.3, 2.4, 0.92, accent);
    addText(slide, title, { x: x + 0.3, y: 2.95, w: 2.68, h: 0.26, fontSize: 15, bold: true, color: C.navy, fit: "shrink" });
    addText(slide, body, { x: x + 0.3, y: 3.55, w: 2.75, h: 0.48, fontSize: 9.5, color: C.muted, fit: "shrink" });
  });
  rect(slide, 0.73, 4.95, 11.8, 0.94, C.navy);
  addText(slide, "TEAM OWNERSHIP", { x: 1.04, y: 5.2, w: 1.35, h: 0.15, fontSize: 8, bold: true, color: C.orange, charSpacing: 0.8 });
  addText(slide, "Phi: roadface + automotive | Trung: DMS | Dung: agent/coaching | Kha: CV/ML + depth | Tu: backend + dashboard", {
    x: 2.45, y: 5.16, w: 8.9, h: 0.22, fontSize: 10.2, color: C.white, bold: true, align: "center", fit: "shrink",
  });
  addText(slide, "CarSky disclosure: bridge is part of the build; Android Automotive end-to-end HMI must be demonstrated separately before claiming it.", {
    x: 0.85, y: 6.25, w: 11.4, h: 0.18, fontSize: 8.5, color: C.muted, italic: true, align: "center", fit: "shrink",
  });
}

// 12. Closing / reviewer route
{
  const slide = pptx.addSlide();
  slide.background = { color: C.navy };
  rect(slide, 0, 0, W, 0.18, C.orange);
  label(slide, "REVIEW IN 3 MINUTES", 0.7, 0.68, 2.05, C.orange);
  addText(slide, "FROM RISK QUEUE\nTO COACHING CONTEXT", {
    x: 0.7, y: 1.3, w: 5.65, h: 1.12, fontSize: 33, bold: true, color: C.white, breakLine: true, fit: "shrink",
  });
  const steps = [
    ["01", "Open fleet ranking"],
    ["02", "Select T01d"],
    ["03", "Inspect timeline + replay"],
    ["04", "Open frame-linked evidence"],
    ["05", "Assign targeted coaching"],
  ];
  steps.forEach(([number, text], index) => {
    const y = 3.0 + index * 0.55;
    rect(slide, 0.74, y, 0.43, 0.31, index === 4 ? C.orange : C.blue);
    addText(slide, number, { x: 0.78, y: y + 0.09, w: 0.35, h: 0.1, fontSize: 7.4, bold: true, color: C.white, align: "center" });
    addText(slide, text, { x: 1.42, y: y + 0.05, w: 3.25, h: 0.17, fontSize: 12, color: C.white, bold: index === 4, fit: "shrink" });
  });
  rect(slide, 7.08, 1.1, 5.05, 4.78, "21367E", "47628E");
  addText(slide, "FINAL DISCLOSURE", { x: 7.5, y: 1.55, w: 2.2, h: 0.18, fontSize: 10, bold: true, color: C.orange, charSpacing: 1 });
  addText(slide, "- Redacted trips have no local ground truth.\n- Practice evaluation is not blind-test accuracy.\n- Frame 551 false positive is kept visible.\n- CarSky HMI remains partial until recorded.", {
    x: 7.5, y: 2.1, w: 4.12, h: 1.42, fontSize: 12, color: "DCE9FA", breakLine: true, fit: "shrink",
  });
  addText(slide, "v1.0.0", { x: 7.5, y: 4.42, w: 1.2, h: 0.28, fontSize: 18, bold: true, color: C.success });
  addText(slide, "Source + runtime handoff\nfor reproducible review", { x: 8.95, y: 4.43, w: 2.45, h: 0.38, fontSize: 10, color: C.white, bold: true, align: "right", breakLine: true, fit: "shrink" });
  addText(slide, "THANK YOU", { x: 7.5, y: 5.2, w: 4.15, h: 0.28, fontSize: 19, bold: true, color: C.white, align: "right" });
  source(slide, "Release runbook: docs/runbooks/final-release.md", true);
  footer(slide, 12, true);
}

pptx.writeFile({ fileName: OUTPUT });
