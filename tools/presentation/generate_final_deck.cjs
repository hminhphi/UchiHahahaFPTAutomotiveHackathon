/* Generate the Vietnamese, evidence-safe final-round deck. */

const path = require("node:path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "../..");
const OUTPUT = path.join(ROOT, "docs/proposal/UchiHahaha_FleetIQGuardian_Final_Round2.pptx");
const ASSET = (...parts) => path.join(ROOT, ...parts);

const image = {
  motorcycle: ASSET("docs/proposal/assets/t01d-motorcycle-evidence.png"),
  motorcycleCrop: ASSET("docs/proposal/assets/t01d-motorcycle-crop.png"),
  labels: ASSET("docs/proposal/assets/label-comparison.png"),
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
  green: "22B573",
};

const pptx = new pptxgen();
pptx.defineLayout({ name: "FLEETIQ", width: 13.333, height: 7.5 });
pptx.layout = "FLEETIQ";
pptx.author = "UchiHahaha";
pptx.company = "UchiHahaha";
pptx.subject = "Automotive Hackathon 2026 - FleetIQ Guardian";
pptx.title = "FleetIQ Guardian - Chung kết";
pptx.lang = "vi-VN";
pptx.theme = { headFontFace: "Quattrocento Sans", bodyFontFace: "Quattrocento Sans", lang: "vi-VN" };

const S = pptx.ShapeType;
const W = 13.333;

function text(slide, value, options = {}) {
  slide.addText(value, { fontFace: "Quattrocento Sans", margin: 0, breakLine: false, ...options });
}

function rect(slide, x, y, w, h, fill, line = fill) {
  slide.addShape(S.rect, {
    x, y, w, h,
    fill: { color: fill },
    line: { color: line, transparency: line === fill ? 100 : 0, width: 0.6 },
  });
}

function line(slide, x, y, w, h, color, endArrow = false) {
  slide.addShape(S.line, { x, y, w, h, line: { color, width: 1.3, endArrowType: endArrow ? "triangle" : "none" } });
}

function label(slide, value, x, y, w, color = C.blue) {
  rect(slide, x, y, w, 0.28, color);
  text(slide, value.toUpperCase(), { x: x + 0.1, y: y + 0.08, w: w - 0.2, h: 0.1, fontSize: 7.5, bold: true, color: C.white, align: "center", charSpacing: 0.6 });
}

function footer(slide, page, dark = false) {
  const color = dark ? "AFC6EA" : C.muted;
  line(slide, 0.56, 7.07, 12.2, 0, dark ? "47628E" : C.line);
  text(slide, "UchiHahaha | FleetIQ Guardian | AUTOMOTIVE HACKATHON 2026", { x: 0.6, y: 7.17, w: 8, h: 0.14, fontSize: 7.4, color });
  text(slide, String(page).padStart(2, "0"), { x: 12.06, y: 7.12, w: 0.65, h: 0.15, fontSize: 9, color: dark ? C.orange : C.blue, bold: true, align: "right" });
}

function heading(slide, page, kicker, title, subtitle = "") {
  slide.background = { color: C.panel };
  rect(slide, 0, 0, W, 0.18, C.orange);
  text(slide, kicker.toUpperCase(), { x: 0.6, y: 0.48, w: 6, h: 0.15, fontSize: 8.8, bold: true, color: C.orange, charSpacing: 1.3 });
  text(slide, title, { x: 0.6, y: 0.76, w: 12, h: 0.48, fontSize: 27, bold: true, color: C.navy, fit: "shrink" });
  if (subtitle) text(slide, subtitle, { x: 0.61, y: 1.38, w: 11.8, h: 0.26, fontSize: 10.8, color: C.muted, fit: "shrink" });
  footer(slide, page);
}

function card(slide, x, y, w, h, accent = C.blue, fill = C.white) {
  rect(slide, x, y, w, h, fill, C.line);
  rect(slide, x, y, 0.08, h, accent);
}

function iconCard(slide, value, title, body, x, y, w, accent) {
  card(slide, x, y, w, 1.76, accent);
  text(slide, value, { x: x + 0.28, y: y + 0.24, w: 0.54, h: 0.36, fontSize: 23, bold: true, color: accent });
  text(slide, title, { x: x + 0.28, y: y + 0.78, w: w - 0.55, h: 0.2, fontSize: 11, bold: true, color: C.navy, fit: "shrink" });
  text(slide, body, { x: x + 0.28, y: y + 1.12, w: w - 0.56, h: 0.35, fontSize: 8.8, color: C.muted, fit: "shrink" });
}

function source(slide, value, dark = false) {
  text(slide, value, { x: 0.6, y: 6.64, w: 11.8, h: 0.2, fontSize: 9.8, italic: true, color: dark ? "EAF2FF" : "34506E", fit: "shrink" });
}

// 01. Cover
{
  const slide = pptx.addSlide();
  slide.background = { color: C.navy };
  rect(slide, 0, 0, W, 0.18, C.orange);
  label(slide, "Chung kết | Challenge #3", 0.68, 0.65, 2.35, C.orange);
  text(slide, "FLEETIQ\nGUARDIAN", { x: 0.68, y: 1.3, w: 5.4, h: 1.15, fontSize: 39, bold: true, color: C.white, breakLine: true, fit: "shrink" });
  text(slide, "Nền tảng giám sát rủi ro tài xế và va chạm từ xa", { x: 0.7, y: 2.86, w: 5.2, h: 0.48, fontSize: 17, bold: true, color: C.paleBlue, fit: "shrink" });
  text(slide, "Hợp nhất camera đường, camera tài xế, độ sâu và telemetry thành bằng chứng có thể kiểm tra.", { x: 0.7, y: 3.64, w: 5.15, h: 0.52, fontSize: 12, color: "AFC6EA", fit: "shrink" });
  rect(slide, 0.7, 4.72, 5.1, 0.9, "21367E", "47628E");
  text(slide, "Challenge #3 là sản phẩm chính", { x: 0.95, y: 4.98, w: 2.8, h: 0.18, fontSize: 12, bold: true, color: C.white });
  text(slide, "Challenge #1 và #2 là hai động cơ bên dưới", { x: 0.95, y: 5.25, w: 3.6, h: 0.14, fontSize: 8.8, color: "AFC6EA" });
  rect(slide, 6.76, 1.15, 5.85, 4.65, "21367E", "47628E");
  text(slide, "TỪ TÍN HIỆU ĐẾN HÀNH ĐỘNG", { x: 7.18, y: 1.64, w: 4.8, h: 0.2, fontSize: 10, bold: true, color: C.orange, charSpacing: 0.8 });
  ["Phát hiện rủi ro", "Đồng bộ theo khung hình", "Mở bằng chứng", "Đề xuất coaching"].forEach((item, index) => {
    const y = 2.28 + index * 0.7;
    rect(slide, 7.2, y, 0.4, 0.4, index === 3 ? C.orange : C.blue);
    text(slide, String(index + 1), { x: 7.31, y: y + 0.12, w: 0.18, h: 0.1, fontSize: 7, bold: true, color: C.white, align: "center" });
    text(slide, item, { x: 7.95, y: y + 0.07, w: 3.6, h: 0.18, fontSize: 14, bold: true, color: C.white });
  });
  text(slide, "Nhóm UchiHahaha | Phi, Trung, Dũng, Kha, Tú", { x: 0.7, y: 6.18, w: 5.7, h: 0.16, fontSize: 10.5, bold: true, color: C.white });
  source(slide, "Điểm theo rule luôn đi cùng event và bằng chứng; không được diễn giải là độ chính xác test ẩn.", true);
  footer(slide, 1, true);
}

// 02. Problem
{
  const slide = pptx.addSlide();
  heading(slide, 2, "Bài toán", "VIDEO THÔ KHÔNG TẠO RA QUYẾT ĐỊNH AN TOÀN", "Quản lý đội xe cần biết chuyến nào cần xem, vì sao và bằng chứng nằm ở đâu.");
  iconCard(slide, "01", "DỮ LIỆU PHÂN MẢNH", "Road camera, DMS, độ sâu và telemetry đang ở các luồng độc lập.", 0.72, 2.04, 3.63, C.blue);
  iconCard(slide, "02", "CẢNH BÁO THIẾU NGỮ CẢNH", "Một giá trị TTC hay một ảnh đơn lẻ không nói lên toàn bộ sự kiện.", 4.84, 2.04, 3.63, C.orange);
  iconCard(slide, "03", "COACHING KHÓ KIỂM TRA", "Không có khung hình, thời điểm và lý do thì không thể coaching chính xác.", 8.96, 2.04, 3.63, C.green);
  rect(slide, 0.72, 4.45, 11.87, 1.15, C.navy);
  text(slide, "MỤC TIÊU: BIẾN NHIỀU DÒNG DỮ LIỆU THÀNH MỘT HỒ SƠ RỦI RO CÓ THỂ KIỂM TRA", { x: 1, y: 4.81, w: 11.25, h: 0.25, fontSize: 15, bold: true, color: C.white, align: "center", fit: "shrink" });
  source(slide, "Nhu cầu vận hành: xếp hàng ưu tiên, xem lại sự kiện và gán coaching có bằng chứng.");
}

// 03. Product
{
  const slide = pptx.addSlide();
  heading(slide, 3, "Giải pháp", "MỘT LỚP HỢP NHẤT CHO ĐỘI XE", "FleetIQ Guardian dùng chấm điểm và TTC như động cơ để tạo quy trình cho Challenge #3.");
  const engines = [
    ["01", "ĐỘNG CƠ HÀNH VI", "Tín hiệu attention, handling và làn đường được chuẩn hóa thành sự kiện.", C.blue],
    ["02", "ĐỘNG CƠ RỦI RO VA CHẠM", "Độ sâu, đối tượng dẫn đầu và telemetry tạo ngữ cảnh TTC/near-miss.", C.orange],
    ["03", "ĐỘNG CƠ HỢP NHẤT", "Liên kết sự kiện, độ tin cậy, giải thích và bằng chứng theo khung hình.", C.green],
  ];
  engines.forEach(([number, title, body, accent], index) => iconCard(slide, number, title, body, 0.73 + index * 4.08, 2.02, 3.55, accent));
  line(slide, 2.52, 4.15, 0, 0.55, C.blue, true);
  line(slide, 6.6, 4.15, 0, 0.55, C.orange, true);
  line(slide, 10.68, 4.15, 0, 0.55, C.green, true);
  rect(slide, 0.73, 4.92, 11.87, 0.78, C.paleBlue, C.blue);
  text(slide, "ĐẦU RA: dashboard đội xe · chuyến đi chi tiết · timeline · evidence · báo cáo coaching", { x: 1, y: 5.2, w: 11.3, h: 0.16, fontSize: 12, bold: true, color: C.navy, align: "center" });
}

// 04. Dataset
{
  const slide = pptx.addSlide();
  heading(slide, 4, "Dữ liệu", "NĂM NHÓM TÍN HIỆU, MỘT DÒNG THỜI GIAN", "Chúng tôi khai thác toàn bộ dữ liệu starter kit thay vì chỉ trình diễn một mô hình đơn lẻ.");
  const sources = [
    ["CAMERA ĐƯỜNG", "Đối tượng và ngữ cảnh"],
    ["CAMERA TÀI XẾ", "Trạng thái attention"],
    ["ĐỘ SÂU + CALIB", "Khoảng cách và TTC"],
    ["TELEMETRY", "Tốc độ và handling"],
    ["NHÃN + FUSION", "Đồng bộ và kiểm tra"],
  ];
  sources.forEach(([title, body], index) => {
    const x = 0.69 + index * 2.47;
    card(slide, x, 2.08, 2.15, 1.58, index === 1 ? C.orange : C.blue);
    text(slide, String(index + 1).padStart(2, "0"), { x: x + 0.24, y: 2.37, w: 0.4, h: 0.18, fontSize: 11, bold: true, color: index === 1 ? C.orange : C.blue });
    text(slide, title, { x: x + 0.23, y: 2.78, w: 1.72, h: 0.23, fontSize: 9.2, bold: true, color: C.navy, align: "center", fit: "shrink" });
    text(slide, body, { x: x + 0.21, y: 3.15, w: 1.75, h: 0.14, fontSize: 7.8, color: C.muted, align: "center", fit: "shrink" });
  });
  rect(slide, 0.7, 4.35, 11.86, 1.28, C.navy);
  text(slide, "17.999", { x: 1.04, y: 4.72, w: 1.8, h: 0.38, fontSize: 28, bold: true, color: C.orange, align: "center" });
  text(slide, "KHUNG HÌNH ĐƯỢC GẮN NHÃN", { x: 0.94, y: 5.18, w: 2, h: 0.12, fontSize: 7.4, bold: true, color: C.white, align: "center", fit: "shrink" });
  text(slide, "Dữ liệu đa nguồn cho phép chứng minh một sự kiện bằng nhiều góc nhìn, thay vì suy luận từ một tín hiệu duy nhất.", { x: 3.42, y: 4.82, w: 7.95, h: 0.32, fontSize: 13, bold: true, color: C.white, align: "center", fit: "shrink" });
  source(slide, "Starter kit: road stereo, driver camera, depth, calibration, telemetry, labels và fusion metadata.");
}

// 05. Demo flow
{
  const slide = pptx.addSlide();
  heading(slide, 5, "Trải nghiệm", "MỞ TỪ HÀNG ĐỢI, KẾT THÚC Ở BẰNG CHỨNG", "Giao diện bắt đầu bằng công việc vận hành, không phải landing page.");
  const steps = [
    ["01", "Chọn chuyến cần xem", "Mở điểm theo rule và bằng chứng liên kết."],
    ["02", "Mở timeline đồng bộ", "Road, driver, depth và telemetry cùng frame."],
    ["03", "Kiểm tra evidence", "Đối tượng, TTC, trạng thái tài xế và event."],
    ["04", "Gán coaching", "Hành động cụ thể, có liên kết đến bằng chứng."],
  ];
  steps.forEach(([number, title, body], index) => {
    const x = 0.72 + index * 3.02;
    card(slide, x, 2.02, 2.6, 2.75, index === 3 ? C.orange : C.blue);
    label(slide, number, x + 0.28, 2.36, 0.52, index === 3 ? C.orange : C.blue);
    text(slide, title, { x: x + 0.28, y: 2.96, w: 1.95, h: 0.42, fontSize: 14, bold: true, color: C.navy, fit: "shrink" });
    text(slide, body, { x: x + 0.28, y: 3.78, w: 1.92, h: 0.42, fontSize: 9.2, color: C.muted, fit: "shrink" });
    if (index < 3) line(slide, x + 2.64, 3.33, 0.3, 0, C.orange, true);
  });
  rect(slide, 0.72, 5.2, 11.86, 0.5, C.paleOrange, C.orange);
  text(slide, "Điểm theo rule được tạo từ artifact chuyến; không dùng để tuyên bố độ chính xác hay xếp hạng fleet.", { x: 1, y: 5.36, w: 11.3, h: 0.13, fontSize: 10.5, bold: true, color: C.navy, align: "center" });
}

// 06. Evidence
{
  const slide = pptx.addSlide();
  heading(slide, 6, "Bằng chứng", "MỘT ĐỐI TƯỢNG CÓ THỂ KIỂM TRA, KHÔNG PHẢI CẢNH BÁO HỘP ĐEN", "Frame 551 minh họa cách reviewer truy ngược output perception về cảnh gốc.");
  rect(slide, 0.7, 2.0, 6.26, 3.65, C.ink, C.ink);
  slide.addImage({ path: image.motorcycle, x: 0.88, y: 2.22, w: 5.82, h: 3.27 });
  label(slide, "CẢNH GỐC CÓ ANNOTATION", 2.3, 5.0, 2.0, C.blue);
  rect(slide, 7.38, 2.0, 2.86, 3.65, C.ink, C.ink);
  slide.addImage({ path: image.motorcycleCrop, x: 7.56, y: 2.2, w: 2.5, h: 2.5 });
  label(slide, "CROP PHÓNG TO", 7.82, 4.92, 1.95, C.orange);
  card(slide, 10.55, 2.0, 2.03, 1.55, C.orange);
  text(slide, "ĐỐI TƯỢNG\nXE MÁY", { x: 10.78, y: 2.43, w: 1.52, h: 0.38, fontSize: 12.4, bold: true, color: C.navy, align: "center", fit: "shrink" });
  text(slide, "Reviewer kiểm tra trực tiếp bbox và cảnh gốc.", { x: 10.76, y: 3.06, w: 1.58, h: 0.22, fontSize: 7.4, color: "34506E", align: "center", fit: "shrink" });
  card(slide, 10.55, 3.88, 2.03, 1.77, C.blue);
  text(slide, "VÙNG DEPTH ROI", { x: 10.76, y: 4.28, w: 1.58, h: 0.18, fontSize: 10.3, bold: true, color: C.blue, align: "center", fit: "shrink" });
  text(slide, "Khoảng cách được gắn cùng artifact của khung hình.", { x: 10.76, y: 4.78, w: 1.58, h: 0.28, fontSize: 7.8, color: "34506E", align: "center", fit: "shrink" });
  text(slide, "Giữ false positive chồng lấp để thấy giới hạn model.", { x: 10.76, y: 5.22, w: 1.58, h: 0.16, fontSize: 6.9, bold: true, color: C.navy, align: "center", fit: "shrink" });
  source(slide, "artifacts/trips/T01d/analysis/road/000551.json | rendered evidence frame | label comparison.");
}

// 07. Timeline
{
  const slide = pptx.addSlide();
  heading(slide, 7, "Đồng bộ", "CÙNG MỘT KHUNG HÌNH, NHIỀU LỚP BẰNG CHỨNG", "Tính đồng bộ biến dòng thời gian thành công cụ kiểm tra thay vì tập ảnh rời rạc.");
  const rows = [
    ["CAMERA ĐƯỜNG", C.blue, "Đối tượng trong làn · khoảng cách · TTC"],
    ["DMS", C.orange, "Trạng thái tài xế · độ tin cậy"],
    ["TELEMETRY", C.green, "Tốc độ · phanh · góc lái"],
    ["HỢP NHẤT", C.navy, "Sự kiện hợp nhất · giải thích · bằng chứng"],
  ];
  rows.forEach(([name, color, detail], index) => {
    const y = 2.04 + index * 0.85;
    label(slide, name, 0.75, y + 0.18, 1.5, color);
    line(slide, 2.58, y + 0.43, 7.72, 0, "B9C9DD");
    rect(slide, 6.82, y + 0.29, 0.26, 0.26, color);
    text(slide, detail, { x: 10.55, y: y + 0.33, w: 1.55, h: 0.14, fontSize: 8, color: C.muted, fit: "shrink" });
  });
  line(slide, 6.95, 1.93, 0, 3.45, C.orange);
  label(slide, "KHUNG 800", 6.31, 1.76, 1.28, C.orange);
  rect(slide, 2.58, 5.7, 9.5, 0.48, C.navy);
  text(slide, "KIỂM TRA THEO KHUNG HÌNH: chọn một sự kiện là mở đúng bối cảnh, không suy diễn từ thời điểm khác.", { x: 2.87, y: 5.86, w: 8.9, h: 0.12, fontSize: 8.8, bold: true, color: C.white, align: "center", fit: "shrink" });
  source(slide, "T01d–T10d có 1.800 khung logic (0–1799); T08d/1615 là source road-left không khả dụng và được đánh dấu rõ.");
}

// 08. Architecture
{
  const slide = pptx.addSlide();
  heading(slide, 8, "Kiến trúc", "TỪ NHIỀU TÍN HIỆU ĐẾN MỘT QUYẾT ĐỊNH CÓ BẰNG CHỨNG", "Pipeline tập trung vào điều quản lý đội xe có thể mở, kiểm tra và hành động.");
  const inputs = [["CAMERA\nĐƯỜNG", C.blue], ["CAMERA\nTÀI XẾ", C.orange], ["ĐỘ SÂU", C.blue], ["TELEMETRY", C.green], ["NHÃN +\nFUSION", C.navy]];
  inputs.forEach(([title, accent], index) => {
    const x = 0.72 + index * 2.42;
    card(slide, x, 1.95, 2.06, 0.72, accent);
    text(slide, title, { x: x + 0.18, y: 2.17, w: 1.7, h: 0.2, fontSize: 8.4, bold: true, color: C.navy, align: "center", fit: "shrink" });
    line(slide, x + 1.03, 2.72, 0, 0.37, accent, true);
  });
  const engines = [["TTC + NEAR-MISS", "Khoảng cách và object", C.orange], ["DRIVER STATE", "Attention và DMS", C.blue], ["RISK SCORER", "Rule minh bạch", C.green]];
  engines.forEach(([title, body, accent], index) => {
    const x = 0.82 + index * 4.12;
    card(slide, x, 3.18, 3.42, 1.12, accent);
    text(slide, title, { x: x + 0.27, y: 3.5, w: 2.88, h: 0.18, fontSize: 10.5, bold: true, color: C.navy, align: "center", fit: "shrink" });
    text(slide, body, { x: x + 0.28, y: 3.88, w: 2.84, h: 0.13, fontSize: 8.2, color: C.muted, align: "center", fit: "shrink" });
    line(slide, x + 1.71, 4.35, 0, 0.37, accent, true);
  });
  const outputs = [["EVENT WINDOW", "Thời điểm + mức độ", C.orange], ["TRIP SCORE", "Điểm theo rule", C.green], ["COACHING", "Hành động có evidence", C.blue]];
  outputs.forEach(([title, body, accent], index) => {
    const x = 0.82 + index * 4.12;
    card(slide, x, 4.82, 3.42, 1.0, accent);
    text(slide, title, { x: x + 0.25, y: 5.1, w: 2.9, h: 0.16, fontSize: 10, bold: true, color: accent, align: "center", fit: "shrink" });
    text(slide, body, { x: x + 0.28, y: 5.45, w: 2.84, h: 0.12, fontSize: 8.3, color: C.muted, align: "center", fit: "shrink" });
  });
  source(slide, "Đầu ra luôn liên kết event với điểm theo rule và khung hình nguồn; không diễn giải score là độ chính xác test ẩn.");
}

// 09. Event rules
{
  const slide = pptx.addSlide();
  heading(slide, 9, "Luật event và coaching", "MỘT EVENT CÓ ĐIỀU KIỆN, PENALTY VÀ KHUNG BẰNG CHỨNG", "DMS dùng cửa sổ 15 frame; cùng một trạng thái được gộp trong 5 giây để timeline không nhiễu.");
  const stages = [
    ["01", "LỌC OBJECT", "bbox >30 px\n>=50% overlap fixed ego-corridor", C.blue],
    ["02", "TTC TỪ DEPTH ROI", "<1,5 s: 35\n<2,5 s: 26\n<4 s: 15", C.orange],
    ["03", "DMS + TELEMETRY", "window 15 frame · drowsy 25 · distracted/phone 15\nspeeding 5–15 · harsh accel 10", C.green],
  ];
  stages.forEach(([number, title, body, accent], index) => {
    const x = 0.72 + index * 4.08;
    card(slide, x, 1.96, 3.55, 1.58, accent);
    label(slide, number, x + 0.3, 2.26, 0.54, accent);
    text(slide, title, { x: x + 1.03, y: 2.27, w: 2.08, h: 0.16, fontSize: 10, bold: true, color: C.navy, align: "center", fit: "shrink" });
    text(slide, body, { x: x + 0.34, y: 2.83, w: 2.86, h: 0.34, fontSize: 8.7, color: C.muted, align: "center", fit: "shrink" });
    if (index < 2) line(slide, x + 3.61, 2.75, 0.35, 0, C.orange, true);
  });
  rect(slide, 0.72, 4.08, 7.08, 1.62, C.navy);
  text(slide, "ĐIỂM THEO RULE", { x: 1.03, y: 4.4, w: 6.45, h: 0.15, fontSize: 11, bold: true, color: C.orange, align: "center" });
  text(slide, "Bắt đầu từ 100 điểm\nTrừ theo khoảng cách, attention, handling và làn đường\nRủi ro kết hợp chỉ tăng mức độ, không trừ hai lần", { x: 1.06, y: 4.8, w: 6.4, h: 0.48, fontSize: 10, bold: true, color: C.white, align: "center", fit: "shrink" });
  card(slide, 8.18, 4.08, 4.38, 1.62, C.orange);
  text(slide, "EVENT WINDOW → COACHING", { x: 8.56, y: 4.4, w: 3.62, h: 0.15, fontSize: 10.2, bold: true, color: C.orange, align: "center" });
  text(slide, "DMS cùng trạng thái: 1 event / 5 giây\nTrạng thái khác mới tạo transition\nSeverity 4–5: visual 10–15s", { x: 8.58, y: 4.8, w: 3.57, h: 0.5, fontSize: 9, bold: true, color: C.navy, align: "center", fit: "shrink" });
  rect(slide, 0.72, 5.95, 11.84, 0.42, C.paleOrange, C.orange);
  text(slide, "ĐIỂM THEO RULE KHÔNG ĐƯỢC DÙNG ĐỂ XẾP HẠNG HAY TÍNH TRUNG BÌNH FLEET.", { x: 0.98, y: 6.1, w: 11.3, h: 0.12, fontSize: 9.5, bold: true, color: C.navy, align: "center", fit: "shrink" });
  source(slide, "Nguồn: RiskScorer v1 · event window · policy coaching.");
}

// 10. Model boundaries
{
  const slide = pptx.addSlide();
  heading(slide, 10, "Nguồn model", "MỖI TẦNG DÙNG GÌ, KHÔNG DÙNG GÌ", "Tách rõ precomputed label, GT depth, geometry rule và model training artifact để tránh overclaim.");
  const models = [
    ["ROAD OBJECT", "label2_yolo_v3\nCustom YOLO v3 precomputed", "Training record: mAP50 0,40952\nKhông re-infer live trong artifact pass", C.blue],
    ["KHOẢNG CÁCH / TTC", "GT depth ROI + calibration", "Không dùng learned depth\nChỉ TTC object giữ lại trong corridor", C.orange],
    ["DMS RUNTIME", "MediaPipe Face Landmarker\nEAR / pose / PERCLOS geometry", "Pseudo-label rule runtime\nCheckpoint 95,17% là artifact riêng", C.green],
    ["FUSION / COACHING", "RiskScorer v1 + 12 mapping rules", "Deterministic, replayable\nKhông gọi đây là fusion model ML", C.navy],
  ];
  models.forEach(([tag, model, detail, accent], index) => {
    const x = 0.72 + (index % 2) * 6.03;
    const y = 1.95 + Math.floor(index / 2) * 2.05;
    card(slide, x, y, 5.52, 1.63, accent);
    label(slide, tag, x + 0.28, y + 0.27, 1.55, accent);
    text(slide, model, { x: x + 0.32, y: y + 0.78, w: 2.55, h: 0.38, fontSize: 11.2, bold: true, color: C.navy, fit: "shrink" });
    text(slide, detail, { x: x + 3.02, y: y + 0.77, w: 2.02, h: 0.43, fontSize: 8.6, color: C.muted, fit: "shrink" });
  });
  rect(slide, 0.72, 6.05, 11.85, 0.52, C.paleOrange, C.orange);
  text(slide, "KHÔNG CÓ LANE MODEL: x=250..390 là fixed image corridor để lọc object; lane penalty hiện bằng 0 trong RiskScorer.", { x: 1.0, y: 6.23, w: 11.3, h: 0.12, fontSize: 9.5, bold: true, color: C.navy, align: "center", fit: "shrink" });
  source(slide, "Nguồn runtime: label2_yolo_v3 · GT depth · MediaPipe Face Landmarker · RiskScorer v1.");
}

// 11. Technical proof
{
  const slide = pptx.addSlide();
  heading(slide, 11, "Kiểm chứng", "CÓ CHỈ SỐ CHO MÔ HÌNH, CÓ GIỚI HẠN CHO SẢN PHẨM", "Đánh giá training artifact và rule output đội xe là hai phạm vi khác nhau.");
  card(slide, 0.72, 2.0, 3.6, 3.45, C.blue);
  text(slide, "95,17%", { x: 1.06, y: 2.48, w: 2.7, h: 0.48, fontSize: 30, bold: true, color: C.blue, align: "center" });
  text(slide, "DMS SEQUENCE CHECKPOINT OFFLINE", { x: 1.06, y: 3.1, w: 2.7, h: 0.16, fontSize: 8.3, bold: true, color: C.navy, align: "center", fit: "shrink" });
  text(slide, "Validation epoch 7; không phải hiệu năng DMS geometry runtime của demo.", { x: 1.05, y: 3.54, w: 2.74, h: 0.31, fontSize: 8.5, color: "34506E", align: "center", fit: "shrink" });
  card(slide, 4.84, 2.0, 3.6, 3.45, C.orange);
  text(slide, "0,40952", { x: 5.18, y: 2.48, w: 2.7, h: 0.48, fontSize: 30, bold: true, color: C.orange, align: "center" });
  text(slide, "YOLO v3 · mAP50 tốt nhất", { x: 5.18, y: 3.1, w: 2.7, h: 0.16, fontSize: 9.2, bold: true, color: C.navy, align: "center" });
  text(slide, "Kết quả v3 được ghi nhận tại epoch 43.", { x: 5.18, y: 3.58, w: 2.7, h: 0.25, fontSize: 9, color: "34506E", align: "center", fit: "shrink" });
  rect(slide, 8.96, 2.0, 3.6, 3.45, C.ink, C.ink);
  text(slide, "17.999", { x: 9.24, y: 2.45, w: 3.05, h: 0.45, fontSize: 28, bold: true, color: C.orange, align: "center" });
  text(slide, "FRAME ĐƯỢC GẮN NHÃN", { x: 9.24, y: 3.08, w: 3.05, h: 0.16, fontSize: 9, bold: true, color: C.white, align: "center" });
  ["Xe", "Người", "Xe máy", "Bối cảnh làn"].forEach((name, index) => {
    const x = 9.28 + (index % 2) * 1.48;
    const y = 3.72 + Math.floor(index / 2) * 0.58;
    rect(slide, x, y, 1.24, 0.36, index === 2 ? C.orange : C.blue);
    text(slide, name, { x, y: y + 0.12, w: 1.24, h: 0.08, fontSize: 6.8, bold: true, color: C.white, align: "center", fit: "shrink" });
  });
  text(slide, "GIỚI HẠN: không diễn giải điểm theo rule là độ chính xác kiểm thử ẩn hoặc xếp hạng an toàn toàn đội.", { x: 1.0, y: 5.83, w: 11.25, h: 0.18, fontSize: 9.3, bold: true, color: C.orange, align: "center", fit: "shrink" });
  source(slide, "Nguồn: DMS offline checkpoint · YOLO v3 epoch 43 · label2_custom export.");
}

// 12. Risk control
{
  const slide = pptx.addSlide();
  heading(slide, 12, "Kiểm soát rủi ro", "MINH BẠCH GIỚI HẠN ĐỂ DEMO ĐÁNG TIN", "Sản phẩm hiển thị trạng thái thiếu dữ liệu, không tạo ra bằng chứng hoặc điểm số giả.");
  const risks = [
    ["Đồng bộ media", "T01d–T10d có 0–1799. T08d/1615 thiếu source road-left và replay chèn marker unavailable, không thay frame lân cận.", C.blue],
    ["DMS", "DMS state đến từ geometry rule; deck và UI không gọi đó là checkpoint inference đã đánh giá trên test ẩn.", C.orange],
    ["Điểm theo rule", "Chạy từ artifact chuyến và hiển thị kèm evidence; không xếp hạng hoặc tính trung bình fleet.", C.green],
    ["Kiểm thử ẩn", "Ground truth T01d–T10d bị che; không suy diễn độ chính xác từ tập thực hành.", C.navy],
  ];
  risks.forEach(([title, body, accent], index) => {
    const x = 0.72 + (index % 2) * 6.03;
    const y = 2.0 + Math.floor(index / 2) * 1.85;
    card(slide, x, y, 5.5, 1.45, accent);
    text(slide, title, { x: x + 0.3, y: y + 0.3, w: 1.6, h: 0.18, fontSize: 11, bold: true, color: accent, fit: "shrink" });
    text(slide, body, { x: x + 1.95, y: y + 0.28, w: 3.05, h: 0.55, fontSize: 9, color: "34506E", fit: "shrink" });
  });
  source(slide, "UX theo bằng chứng: media thiếu được biểu diễn rõ; score luôn đi cùng rule, event và frame liên kết.");
}

// 13. Delivery
{
  const slide = pptx.addSlide();
  heading(slide, 13, "Sẵn sàng trình diễn", "MỘT LUỒNG QUYẾT ĐỊNH HOÀN CHỈNH CHO FLEET MANAGER", "Từ chuyến cần xem đến coaching, mọi bước đều có ngữ cảnh để người vận hành hành động.");
  const columns = [
    ["MỞ", "Chọn đúng chuyến", "Dashboard hiển thị điểm theo rule và những event cần ưu tiên xem lại.", C.blue],
    ["KIỂM", "Xem đúng bối cảnh", "Timeline mở camera đường, DMS và telemetry tại cùng một khung hình.", C.orange],
    ["HÀNH ĐỘNG", "Gán coaching rõ ràng", "Kết thúc bằng hướng dẫn liên kết với bằng chứng, không phải cảnh báo chung chung.", C.green],
  ];
  columns.forEach(([tag, title, body, accent], index) => {
    const x = 0.74 + index * 4.08;
    card(slide, x, 2.05, 3.54, 2.4, accent);
    label(slide, tag, x + 0.3, 2.36, 1.1, accent);
    text(slide, title, { x: x + 0.3, y: 2.95, w: 2.7, h: 0.26, fontSize: 15, bold: true, color: C.navy, fit: "shrink" });
    text(slide, body, { x: x + 0.3, y: 3.53, w: 2.72, h: 0.48, fontSize: 9.3, color: C.muted, fit: "shrink" });
  });
  rect(slide, 0.74, 4.96, 11.8, 0.93, C.navy);
  text(slide, "MVP ĐÃ SẴN SÀNG: dashboard · trip replay · event evidence · điểm theo rule · coaching có ngữ cảnh.", { x: 1.0, y: 5.27, w: 11.25, h: 0.16, fontSize: 10.5, bold: true, color: C.white, align: "center", fit: "shrink" });
  source(slide, "Demo flow: dashboard → chuyến rủi ro → timeline → evidence → điểm theo rule → coaching.");
}

// 14. Close
{
  const slide = pptx.addSlide();
  slide.background = { color: C.navy };
  rect(slide, 0, 0, W, 0.18, C.orange);
  label(slide, "Trình diễn trong 3 phút", 0.7, 0.68, 2.05, C.orange);
  text(slide, "TỪ HÀNG ĐỢI RỦI RO\nĐẾN HƯỚNG DẪN CÓ BẰNG CHỨNG", { x: 0.7, y: 1.3, w: 5.95, h: 1.08, fontSize: 31, bold: true, color: C.white, breakLine: true, fit: "shrink" });
  ["Mở chuyến cần kiểm tra", "Chọn sự kiện theo dòng thời gian", "Xem camera, DMS và telemetry", "Kiểm tra bằng chứng liên kết", "Gán hướng dẫn phù hợp"].forEach((item, index) => {
    const y = 3.0 + index * 0.55;
    rect(slide, 0.74, y, 0.43, 0.31, index === 4 ? C.orange : C.blue);
    text(slide, String(index + 1).padStart(2, "0"), { x: 0.78, y: y + 0.09, w: 0.35, h: 0.1, fontSize: 7.3, bold: true, color: C.white, align: "center" });
    text(slide, item, { x: 1.42, y: y + 0.06, w: 3.7, h: 0.15, fontSize: 11.5, bold: index === 4, color: C.white });
  });
  rect(slide, 7.15, 1.16, 4.97, 4.7, "21367E", "47628E");
  text(slide, "FLEETIQ GUARDIAN", { x: 7.58, y: 1.65, w: 4.1, h: 0.24, fontSize: 15, bold: true, color: C.orange, align: "center" });
  text(slide, "Giúp quản lý đội xe hiểu rủi ro trước khi họ phải xem hàng giờ video.", { x: 7.75, y: 2.4, w: 3.75, h: 0.58, fontSize: 18, bold: true, color: C.white, align: "center", fit: "shrink" });
  rect(slide, 7.8, 3.55, 3.68, 0.76, C.blue);
  text(slide, "18.000 FRAME ANALYSIS\n1.800 FRAME / TRIP · EVENT REPLAY", { x: 8.02, y: 3.78, w: 3.24, h: 0.24, fontSize: 8.6, bold: true, color: C.white, align: "center", fit: "shrink" });
  text(slide, "Cảm ơn", { x: 7.58, y: 4.85, w: 4.1, h: 0.28, fontSize: 22, bold: true, color: C.white, align: "center" });
  source(slide, "Bản trình bày cuối | Claim được giới hạn bởi bằng chứng hiện có.", true);
  footer(slide, 14, true);
}

(async () => {
  await pptx.writeFile({ fileName: OUTPUT });
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
