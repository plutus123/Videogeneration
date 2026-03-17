"""Renders NotebookLM-style explainer slides programmatically using PIL."""

import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WIDTH = 1920
HEIGHT = 1080

WHITE = (255, 255, 255)
LIGHT_PINK = (252, 235, 243)
ACCENT_PINK = (255, 182, 213)
STRONG_PINK = (236, 150, 192)
HIGHLIGHT_YELLOW = (255, 239, 150)
TEXT_BLACK = (35, 35, 35)
TEXT_GRAY = (110, 110, 110)
TEXT_WHITE = (245, 245, 245)
WARM_GRAY_BG = (245, 244, 242)
DOT_GRAY = (225, 225, 225)
CARD_BG = (255, 255, 255)
CARD_BORDER = (230, 230, 230)
ARROW_PINK = (255, 195, 220)

_FONT_CACHE = {}

if sys.platform == "win32":
    _BOLD_PATHS = [
        ("C:\\Windows\\Fonts\\arialbd.ttf", None),
        ("C:\\Windows\\Fonts\\segoeui.ttf", None),
    ]
    _REG_PATHS = [
        ("C:\\Windows\\Fonts\\arial.ttf", None),
        ("C:\\Windows\\Fonts\\segoeui.ttf", None),
    ]
else:
    _BOLD_PATHS = [
        ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", None),
        ("/Library/Fonts/Arial Bold.ttf", None),
        ("/System/Library/Fonts/Helvetica.ttc", 1),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", None),
    ]
    _REG_PATHS = [
        ("/System/Library/Fonts/Supplemental/Arial.ttf", None),
        ("/Library/Fonts/Arial.ttf", None),
        ("/System/Library/Fonts/Helvetica.ttc", 0),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", None),
    ]


def _font(size, bold=True):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    paths = _BOLD_PATHS if bold else _REG_PATHS
    for path, index in paths:
        if not os.path.exists(path):
            continue
        try:
            kwargs = {"index": index} if index is not None else {}
            f = ImageFont.truetype(path, size, **kwargs)
            _FONT_CACHE[key] = f
            return f
        except Exception:
            continue
    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


def _dot_grid(draw, spacing=40):
    for x in range(spacing, WIDTH, spacing):
        for y in range(spacing, HEIGHT, spacing):
            draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=DOT_GRAY)


def _wrap(draw, text, font, max_w):
    words = text.split()
    if not words:
        return []
    lines = []
    cur = words[0]
    for w in words[1:]:
        test = f"{cur} {w}"
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def _tsize(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def _cx(draw, text, font):
    w, _ = _tsize(draw, text, font)
    return (WIDTH - w) // 2


def _save(img, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    img.convert("RGB").save(path, quality=95)
    return path


def _draw_highlighted_line(draw, words_in_line, highlights, font, x, y, default_color):
    sp_w = draw.textlength(" ", font=font)
    cx = x
    hl_lower = [h.lower() for h in highlights]
    for word in words_in_line:
        w, h = _tsize(draw, word, font)
        clean = word.strip(".,;:!?\"'()[]{}")
        if clean.lower() in hl_lower:
            pad_x = 10
            pad_y = 6
            draw.rounded_rectangle(
                [cx - pad_x, y - pad_y, cx + w + pad_x, y + h + pad_y],
                radius=8, fill=HIGHLIGHT_YELLOW,
            )
            draw.text((cx, y), word, font=font, fill=TEXT_BLACK)
        else:
            draw.text((cx, y), word, font=font, fill=default_color)
        cx += w + sp_w


def render_title(scene, path):
    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)
    _dot_grid(draw)

    draw.rounded_rectangle([(50, 30), (180, 130)], radius=16, fill=LIGHT_PINK)
    draw.rounded_rectangle([(-30, 70), (100, 180)], radius=16, fill=ACCENT_PINK)
    draw.rounded_rectangle([(WIDTH - 110, 200), (WIDTH + 30, 360)], radius=16, fill=ACCENT_PINK)
    draw.ellipse([(55, HEIGHT - 140), (95, HEIGHT - 100)], outline=DOT_GRAY, width=2)
    draw.ellipse([(85, HEIGHT - 115), (115, HEIGHT - 85)], fill=DOT_GRAY)
    draw.rounded_rectangle([(WIDTH - 80, 40), (WIDTH + 10, 110)], radius=12, fill=LIGHT_PINK)

    title = scene.get("title", "Title")
    tf = _font(92, bold=True)
    lines = _wrap(draw, title, tf, WIDTH - 300)
    line_h = 115
    total_h = len(lines) * line_h
    sy = max(80, (HEIGHT // 2 - total_h) // 2 + 20)
    for i, line in enumerate(lines):
        x = _cx(draw, line, tf)
        draw.text((x, sy + i * line_h), line, font=tf, fill=TEXT_BLACK)

    subtitle = scene.get("subtitle", "")
    if subtitle:
        card_y = sy + total_h + 50
        card_h = 200
        card_x = WIDTH // 2 - 420
        card_w = 840
        draw.rounded_rectangle(
            [(card_x, card_y), (card_x + card_w, card_y + card_h)],
            radius=22, fill=WHITE, outline=CARD_BORDER, width=2,
        )
        draw.ellipse(
            [(card_x + 16, card_y + 16), (card_x + 32, card_y + 32)],
            fill=ACCENT_PINK,
        )
        sf = _font(34, bold=False)
        sub_lines = _wrap(draw, subtitle, sf, card_w - 80)
        for j, sl in enumerate(sub_lines):
            sx = card_x + (card_w - int(draw.textlength(sl, font=sf))) // 2
            draw.text((sx, card_y + 55 + j * 45), sl, font=sf, fill=TEXT_GRAY)

    return _save(img, path)


def render_big_number(scene, path):
    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)
    _dot_grid(draw)

    number = scene.get("number", "0")
    label = scene.get("label", "")

    target_w = int(WIDTH * 0.7)
    sz = 500
    nf = _font(sz, bold=True)
    w, h = _tsize(draw, number, nf)
    while w > target_w and sz > 140:
        sz -= 20
        nf = _font(sz, bold=True)
        w, h = _tsize(draw, number, nf)
    while w < target_w * 0.5 and sz < 600:
        sz += 20
        nf = _font(sz, bold=True)
        w, h = _tsize(draw, number, nf)

    shadow_off = max(10, sz // 35)
    stroke_w = max(4, sz // 80)

    bb = draw.textbbox((0, 0), number, font=nf, stroke_width=stroke_w)
    actual_h = bb[3] - bb[1]
    num_x = (WIDTH - w) // 2
    num_y = HEIGHT // 2 - actual_h // 2 - 60

    draw.text((num_x + shadow_off, num_y + shadow_off), number, font=nf, fill=ACCENT_PINK)
    draw.text((num_x, num_y), number, font=nf, fill=WHITE, stroke_width=stroke_w, stroke_fill=TEXT_BLACK)

    visual_bottom = num_y + bb[3] + shadow_off + stroke_w

    if label:
        lf = _font(40, bold=False)
        lbl_lines = _wrap(draw, label, lf, WIDTH - 400)
        _, single_h = _tsize(draw, "Ag", lf)
        lbl_y = visual_bottom + 40
        for li, ll in enumerate(lbl_lines):
            lx = _cx(draw, ll, lf)
            draw.text((lx, lbl_y + li * (single_h + 10)), ll, font=lf, fill=TEXT_GRAY)

    return _save(img, path)


def render_comparison(scene, path):
    img = Image.new("RGB", (WIDTH, HEIGHT), LIGHT_PINK)
    draw = ImageDraw.Draw(img)

    title = scene.get("title", "")
    if title:
        tf = _font(48, bold=True)
        tx = _cx(draw, title, tf)
        draw.text((tx, 50), title, font=tf, fill=TEXT_BLACK)

    card_w = 700
    card_h = 420
    gap = 60
    total_w = card_w * 2 + gap
    lx = (WIDTH - total_w) // 2
    rx = lx + card_w + gap
    cy = (HEIGHT - card_h) // 2 + 30

    sides = [
        (lx, "left_label", "left_value", "left_highlight"),
        (rx, "right_label", "right_value", "right_highlight"),
    ]
    for cx, lk, vk, hk in sides:
        draw.rounded_rectangle(
            [(cx, cy), (cx + card_w, cy + card_h)],
            radius=22, fill=CARD_BG,
        )
        label = scene.get(lk, "")
        value = scene.get(vk, "")
        hl = scene.get(hk, "")

        lf = _font(42, bold=True)
        vf = _font(36, bold=False)

        draw.text((cx + 45, cy + card_h - 140), label, font=lf, fill=TEXT_BLACK)
        if hl and value:
            _draw_highlighted_line(
                draw, value.split(), [hl], vf,
                cx + 45, cy + card_h - 80, TEXT_GRAY,
            )
        else:
            draw.text((cx + 45, cy + card_h - 80), value, font=vf, fill=TEXT_GRAY)

    return _save(img, path)


def render_steps(scene, path):
    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    title = scene.get("title", "Process")
    tf = _font(54, bold=True)
    draw.text((70, 45), title, font=tf, fill=TEXT_BLACK)

    for y in range(155, HEIGHT):
        ratio = min(1.0, (y - 155) / (HEIGHT - 155))
        r = int(255 * (1 - ratio) + LIGHT_PINK[0] * ratio)
        g = int(255 * (1 - ratio) + LIGHT_PINK[1] * ratio)
        b = int(255 * (1 - ratio) + LIGHT_PINK[2] * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    steps = []
    for i in range(1, 6):
        s = scene.get(f"step_{i}", "")
        if s:
            steps.append(s)
    if not steps:
        steps = ["Step 1", "Step 2", "Step 3"]

    n = len(steps)
    card_w = min(380, (WIDTH - 160) // n - 50)
    card_h = 170
    arrow_gap = 70
    total_w = n * card_w + (n - 1) * arrow_gap
    sx = (WIDTH - total_w) // 2
    sy = HEIGHT // 2 - card_h // 2 + 30

    sf = _font(30, bold=True)
    df = _font(24, bold=False)

    for i, step in enumerate(steps):
        cx = sx + i * (card_w + arrow_gap)
        draw.rounded_rectangle(
            [(cx, sy), (cx + card_w, sy + card_h)],
            radius=16, fill=CARD_BG, outline=CARD_BORDER, width=1,
        )
        lbl = f"Step {i + 1}"
        draw.text((cx + 28, sy + 28), lbl, font=sf, fill=TEXT_BLACK)
        desc_lines = _wrap(draw, step, df, card_w - 56)
        for j, dl in enumerate(desc_lines):
            draw.text((cx + 28, sy + 72 + j * 32), dl, font=df, fill=TEXT_GRAY)

        if i < n - 1:
            ax = cx + card_w + 8
            ay = sy + card_h // 2
            draw.line([(ax, ay), (ax + arrow_gap - 22, ay)], fill=ARROW_PINK, width=3)
            draw.polygon(
                [
                    (ax + arrow_gap - 22, ay - 9),
                    (ax + arrow_gap - 6, ay),
                    (ax + arrow_gap - 22, ay + 9),
                ],
                fill=ARROW_PINK,
            )

    return _save(img, path)


def render_statement(scene, path):
    img = Image.new("RGB", (WIDTH, HEIGHT), WARM_GRAY_BG)
    draw = ImageDraw.Draw(img)
    _dot_grid(draw, spacing=50)

    draw.rounded_rectangle([(80, 0), (88, HEIGHT)], radius=0, fill=ACCENT_PINK)

    text = scene.get("text", "")
    highlights = []
    for i in range(1, 5):
        h = scene.get(f"highlight_{i}", "")
        if h:
            highlights.append(h)

    font = _font(68, bold=True)
    lines = _wrap(draw, text, font, WIDTH - 400)
    line_h = 95
    total_h = len(lines) * line_h
    start_y = (HEIGHT - total_h) // 2
    start_x = 140

    for i, line in enumerate(lines):
        words = line.split()
        _draw_highlighted_line(
            draw, words, highlights, font,
            start_x, start_y + i * line_h, TEXT_BLACK,
        )

    return _save(img, path)


def render_key_point(scene, path):
    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)
    _dot_grid(draw)

    heading = scene.get("heading", "Key Point")
    hf = _font(62, bold=True)
    draw.text((130, 90), heading, font=hf, fill=TEXT_BLACK)

    draw.rounded_rectangle([(130, 175), (430, 184)], radius=4, fill=ACCENT_PINK)

    pf = _font(42, bold=False)
    y = 230
    for i in range(1, 7):
        pt = scene.get(f"point_{i}", "")
        if not pt:
            continue
        draw.ellipse([(140, y + 14), (158, y + 32)], fill=ACCENT_PINK)
        pt_lines = _wrap(draw, pt, pf, WIDTH - 380)
        for j, pl in enumerate(pt_lines):
            draw.text((180, y + j * 55), pl, font=pf, fill=TEXT_BLACK)
        y += len(pt_lines) * 55 + 30

    return _save(img, path)


RENDERERS = {
    "title": render_title,
    "big_number": render_big_number,
    "comparison": render_comparison,
    "steps": render_steps,
    "statement": render_statement,
    "key_point": render_key_point,
}


def render_scene(scene, output_path):
    scene_type = scene.get("scene_type", "statement")
    renderer = RENDERERS.get(scene_type, render_statement)
    return renderer(scene, output_path)


def _remove_white_bg(icon, threshold=235):
    icon = icon.convert("RGBA")
    pixels = icon.load()
    w, h = icon.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r > threshold and g > threshold and b > threshold:
                pixels[x, y] = (r, g, b, 0)
    return icon


ICON_POSITIONS = {
    "title": (WIDTH - 380, HEIGHT - 380, 260),
    "big_number": (WIDTH - 280, HEIGHT - 280, 180),
    "comparison": None,
    "steps": None,
    "statement": (WIDTH - 300, 80, 200),
    "key_point": (WIDTH - 340, 120, 240),
}


def composite_icon(slide_path, icon_path, scene_type):
    pos = ICON_POSITIONS.get(scene_type)
    if pos is None or not os.path.exists(icon_path):
        return slide_path
    ix, iy, icon_sz = pos
    slide = Image.open(slide_path).convert("RGBA")
    icon = Image.open(icon_path).convert("RGBA")
    icon = icon.resize((icon_sz, icon_sz), Image.LANCZOS)
    icon = _remove_white_bg(icon)
    slide.paste(icon, (ix, iy), icon)
    slide.convert("RGB").save(slide_path, quality=95)
    return slide_path
