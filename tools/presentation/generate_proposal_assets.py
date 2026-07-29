from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = ROOT / "artifacts" / "pptx-assets"

NAVY = "#19226D"
ORANGE = "#F37021"
BLUE = "#034EA2"
WHITE = "#FFFFFF"
INK = "#0F172A"
MUTED = "#6B7A90"
LIGHT = "#EEF3FF"
PANEL = "#F7F9FC"
GRID = "#D9E2F1"
SUCCESS = "#2F855A"
WARN = "#E67E22"
CRIT = "#D64545"


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                Path("C:/Windows/Fonts/arialbd.ttf"),
                Path("C:/Windows/Fonts/segoeuib.ttf"),
            ]
        )
    else:
        candidates.extend(
            [
                Path("C:/Windows/Fonts/arial.ttf"),
                Path("C:/Windows/Fonts/segoeui.ttf"),
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, start: int, bold: bool = False) -> ImageFont.ImageFont:
    size = start
    while size >= 16:
        font = load_font(size, bold=bold)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 2
    return load_font(16, bold=bold)


def draw_round_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, radius: int = 24, outline: str | None = None, width: int = 2) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_center_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font: ImageFont.ImageFont, fill: str) -> None:
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=6, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = box[0] + (box[2] - box[0] - text_w) / 2
    y = box[1] + (box[3] - box[1] - text_h) / 2
    draw.multiline_text((x, y), text, font=font, fill=fill, spacing=6, align="center")


def draw_team_composition() -> None:
    width, height = 1600, 900
    image = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, width, 170), fill=NAVY)
    title_font = load_font(54, bold=True)
    subtitle_font = load_font(24, bold=False)
    draw.text((80, 48), "TEAM COMPOSITION", font=title_font, fill=WHITE)
    draw.text((82, 114), "FleetIQ Guardian | 5 members | 4 AI + 1 Automotive C++", font=subtitle_font, fill="#D8E2FF")

    draw_round_rect(draw, (70, 220, 690, 820), fill=PANEL, outline=GRID, width=3)
    draw_round_rect(draw, (735, 220, 1530, 820), fill=PANEL, outline=GRID, width=3)

    # Left: capability split.
    draw.text((110, 255), "Capability split", font=load_font(28, bold=True), fill=INK)
    draw.text((110, 300), "Team is optimized for rapid prototyping and a stable demo path.", font=load_font(20), fill=MUTED)

    bar_x, bar_y, bar_w, bar_h = 110, 360, 540, 42
    draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=21, fill="#E5EAF5")
    ai_w = int(bar_w * 0.8)
    draw.rounded_rectangle((bar_x, bar_y, bar_x + ai_w, bar_y + bar_h), radius=21, fill=ORANGE)
    draw.rounded_rectangle((bar_x + ai_w - 30, bar_y, bar_x + bar_w, bar_y + bar_h), radius=21, fill=BLUE)
    draw.text((110, 420), "80% AI delivery", font=load_font(38, bold=True), fill=ORANGE)
    draw.text((110, 470), "20% Automotive bridge", font=load_font(28, bold=True), fill=BLUE)

    cards = [
        ("Perception", "2 AI members", ORANGE),
        ("Driver State", "1 AI member", ORANGE),
        ("Backend + Fusion", "1 AI member", ORANGE),
        ("Automotive C++", "1 member", BLUE),
    ]
    cy = 540
    for idx, (title, body, color) in enumerate(cards):
        top = cy + idx * 60
        draw.ellipse((110, top, 140, top + 30), fill=color)
        draw.text((160, top - 2), title, font=load_font(22, bold=True), fill=INK)
        draw.text((370, top - 2), body, font=load_font(20), fill=MUTED)

    # Right: team roster circles.
    draw.text((775, 255), "Execution pods", font=load_font(28, bold=True), fill=INK)
    draw.text((775, 300), "Parallel work reduces scope risk across a 2-3 week sprint.", font=load_font(20), fill=MUTED)
    pod_positions = [
        (860, 420, ORANGE, "AI 1", "TTC + depth"),
        (1095, 420, ORANGE, "AI 2", "Tracking + labels"),
        (1330, 420, ORANGE, "AI 3", "Driver state"),
        (980, 640, ORANGE, "AI 4", "API + dashboard"),
        (1215, 640, BLUE, "C++", "Automotive bridge"),
    ]
    for cx, cy, color, short, label in pod_positions:
        draw.ellipse((cx - 76, cy - 76, cx + 76, cy + 76), fill=color)
        short_font = fit_font(draw, short, 120, 34, bold=True)
        draw_center_text(draw, (cx - 76, cy - 50, cx + 76, cy + 30), short, short_font, WHITE)
        label_font = fit_font(draw, label, 180, 24, bold=False)
        bbox = draw.textbbox((0, 0), label, font=label_font)
        label_w = bbox[2] - bbox[0]
        draw.text((cx - label_w / 2, cy + 98), label, font=label_font, fill=INK)

    draw.line((980, 520, 980, 560), fill=GRID, width=4)
    draw.line((1095, 520, 1095, 560), fill=GRID, width=4)
    draw.line((1210, 520, 1210, 560), fill=GRID, width=4)
    draw.line((980, 560, 1210, 560), fill=GRID, width=4)

    image.save(ASSET_DIR / "team-composition.png")


def draw_dashboard_preview() -> None:
    width, height = 1600, 900
    image = Image.new("RGB", (width, height), "#ECF2FB")
    draw = ImageDraw.Draw(image)

    draw_round_rect(draw, (45, 45, 1555, 855), fill=WHITE, outline="#D1DBEC", width=4, radius=36)
    draw_round_rect(draw, (45, 45, 300, 855), fill=NAVY, radius=36)
    draw.rectangle((300, 45, 320, 855), fill=NAVY)
    draw.text((82, 92), "FleetIQ", font=load_font(42, bold=True), fill=WHITE)
    draw.text((82, 145), "Guardian", font=load_font(28), fill="#D7E0FF")

    nav_items = ["Fleet overview", "Driver ranking", "Trip detail", "Risk events", "Coaching report"]
    for idx, item in enumerate(nav_items):
        y = 250 + idx * 88
        fill = ORANGE if idx == 2 else "#2C377C"
        draw_round_rect(draw, (70, y, 270, y + 56), fill=fill, radius=18)
        draw.text((92, y + 14), item, font=load_font(20, bold=idx == 2), fill=WHITE)

    draw.text((360, 92), "Trip T01 | Near-miss review", font=load_font(42, bold=True), fill=INK)
    draw.text((360, 145), "Dashboard mockup for proposal slides", font=load_font(22), fill=MUTED)

    metric_cards = [
        ("Trip score", "62", NAVY),
        ("Short TTC", "5", ORANGE),
        ("Compound risk", "2", CRIT),
        ("Coachable events", "7", BLUE),
    ]
    x = 360
    for title, value, color in metric_cards:
        draw_round_rect(draw, (x, 200, x + 265, 345), fill=PANEL, outline="#D5DDED", width=3, radius=22)
        draw.text((x + 26, 228), title, font=load_font(22, bold=True), fill=MUTED)
        draw.text((x + 26, 266), value, font=load_font(54, bold=True), fill=color)
        x += 290

    draw_round_rect(draw, (360, 390, 965, 810), fill=PANEL, outline="#D5DDED", width=3, radius=24)
    draw.text((390, 422), "Risk timeline", font=load_font(28, bold=True), fill=INK)

    points = [(420, 700), (500, 650), (580, 610), (660, 590), (740, 500), (820, 560), (900, 470)]
    draw.line(points, fill=ORANGE, width=8)
    for px, py in points:
        draw.ellipse((px - 8, py - 8, px + 8, py + 8), fill=ORANGE)
    draw.line((420, 745, 920, 745), fill=GRID, width=4)
    for idx, label in enumerate(["0s", "8s", "16s", "24s", "32s", "40s", "48s"]):
        tx = 405 + idx * 82
        draw.text((tx, 760), label, font=load_font(16), fill=MUTED)

    draw.text((390, 510), "Driver state", font=load_font(20, bold=True), fill=INK)
    state_blocks = [("#D7EAFE", 420, 540, 140), ("#FDE68A", 570, 540, 120), ("#FCA5A5", 700, 540, 130), ("#D7EAFE", 840, 540, 90)]
    for fill, x0, y0, w in state_blocks:
        draw.rounded_rectangle((x0, y0, x0 + w, y0 + 28), radius=14, fill=fill)

    draw_round_rect(draw, (1010, 390, 1515, 600), fill=PANEL, outline="#D5DDED", width=3, radius=24)
    draw.text((1040, 422), "Event log", font=load_font(28, bold=True), fill=INK)
    events = [
        ("00:14", "TTC 1.8s | lead vehicle", WARN),
        ("00:21", "Near miss | brake late", CRIT),
        ("00:23", "Distracted + short TTC", ORANGE),
    ]
    for idx, (ts, label, color) in enumerate(events):
        top = 470 + idx * 42
        draw.ellipse((1045, top, 1065, top + 20), fill=color)
        draw.text((1090, top - 4), ts, font=load_font(18, bold=True), fill=INK)
        draw.text((1170, top - 4), label, font=load_font(18), fill=MUTED)

    draw_round_rect(draw, (1010, 630, 1515, 810), fill=PANEL, outline="#D5DDED", width=3, radius=24)
    draw.text((1040, 662), "Evidence panel", font=load_font(28, bold=True), fill=INK)
    draw_round_rect(draw, (1045, 710, 1270, 780), fill="#0B122F", radius=16)
    draw.rectangle((1065, 725, 1250, 770), outline=ORANGE, width=4)
    draw.text((1295, 720), "TTC: 1.2s", font=load_font(22, bold=True), fill=CRIT)
    draw.text((1295, 752), "Confidence: 0.86", font=load_font(18), fill=MUTED)

    image.save(ASSET_DIR / "dashboard-preview.png")


def draw_icon(path: Path, label: str, accent: str, kind: str) -> None:
    size = 512
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((24, 24, 488, 488), radius=96, fill=WHITE, outline=accent, width=18)

    if kind == "road":
        draw.rectangle((220, 110, 292, 165), fill=accent)
        draw.polygon([(180, 205), (255, 125), (332, 205)], fill=accent)
        draw.line((120, 410, 240, 230), fill=NAVY, width=18)
        draw.line((392, 410, 272, 230), fill=NAVY, width=18)
        draw.line((256, 270, 256, 390), fill=ORANGE, width=14)
        draw.line((256, 340, 256, 390), fill=WHITE, width=14)
    elif kind == "driver":
        draw.ellipse((178, 118, 334, 274), outline=accent, width=18)
        draw.arc((120, 180, 392, 410), start=205, end=335, fill=NAVY, width=18)
        draw.line((150, 380, 210, 320), fill=NAVY, width=18)
        draw.line((362, 380, 302, 320), fill=NAVY, width=18)
        draw.rectangle((205, 262, 306, 338), outline=ORANGE, width=14)
    elif kind == "fusion":
        draw.ellipse((86, 190, 186, 290), fill=BLUE)
        draw.ellipse((206, 106, 306, 206), fill=ORANGE)
        draw.ellipse((326, 190, 426, 290), fill=NAVY)
        draw.line((186, 240, 206, 156), fill=accent, width=16)
        draw.line((306, 156, 326, 240), fill=accent, width=16)
        draw.line((186, 240, 326, 240), fill=accent, width=16)
        draw.rounded_rectangle((200, 300, 312, 388), radius=22, fill=WHITE, outline=accent, width=12)
    elif kind == "dashboard":
        draw.rounded_rectangle((110, 120, 402, 360), radius=24, outline=accent, width=18)
        draw.line((160, 190, 352, 190), fill=ORANGE, width=18)
        draw.line((160, 250, 270, 250), fill=BLUE, width=18)
        draw.line((160, 308, 320, 308), fill=NAVY, width=18)
        draw.rounded_rectangle((140, 384, 374, 424), radius=16, fill=accent)
    else:
        draw.polygon([(256, 108), (292, 206), (398, 214), (316, 280), (342, 384), (256, 324), (170, 384), (196, 280), (114, 214), (220, 206)], fill=accent)

    font = fit_font(draw, label, 380, 28, bold=True)
    draw_center_text(draw, (64, 420, 448, 474), label, font, NAVY)
    image.save(path)


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    draw_team_composition()
    draw_dashboard_preview()
    draw_icon(ASSET_DIR / "icon-road.png", "Road Camera", BLUE, "road")
    draw_icon(ASSET_DIR / "icon-driver.png", "Driver State", ORANGE, "driver")
    draw_icon(ASSET_DIR / "icon-fusion.png", "Fusion", NAVY, "fusion")
    draw_icon(ASSET_DIR / "icon-dashboard.png", "Dashboard", ORANGE, "dashboard")
    draw_icon(ASSET_DIR / "icon-insight.png", "Core Insight", ORANGE, "idea")


if __name__ == "__main__":
    main()
