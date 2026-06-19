"""B50 成绩图片生成模块。"""

import os
from io import BytesIO
from typing import List
from urllib.request import urlopen, Request

from PIL import Image, ImageDraw, ImageFont

# ── 布局常量 ──────────────────────────────────────────
COLS = 5
CARD_W = 360
CARD_H = 86
GAP_X = 16
GAP_Y = 14
MARGIN = 24

B35_ROWS = 7
B15_ROWS = 3
TITLE_H = 40
SECTION_GAP = 36

USER_CARD_W = 360
USER_CARD_H = 86

THUMB_SIZE = 64
THUMB_PAD_X = 8
THUMB_PAD_Y = (CARD_H - THUMB_SIZE) // 2

GRID_W = COLS * CARD_W + (COLS - 1) * GAP_X
CANVAS_W = MARGIN * 2 + GRID_W
USER_CARD_Y = MARGIN


def _section_h(rows: int) -> int:
    return TITLE_H + 8 + rows * CARD_H + (rows - 1) * GAP_Y


CONTENT_TOP = MARGIN + USER_CARD_H + 20
CANVAS_H = CONTENT_TOP + _section_h(B35_ROWS) + SECTION_GAP + _section_h(B15_ROWS) + MARGIN

# 配色
DIFF_COLORS = {
    "massive": "#E74C3C",
    "invaded": "#9B59B6",
    "detected": "#3498DB",
    "reboot": "#E67E22",
}
B35_BG = "#1a1a2e"
B15_BG = "#16213e"
USER_BG = "#0f0f23"
BORDER_COLOR = "#3a3a5a"
TEXT_WHITE = "#eeeeee"
TEXT_DIM = "#aaaaaa"
TITLE_COLOR = "#cccccc"

COVER_BASE = "https://prp.icel.site/cover"
_cover_cache: dict = {}


# ── 字体 ───────────────────────────────────────────────
def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    font_paths = [
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ── 背景 ──────────────────────────────────────────────
def load_background(bg=None) -> Image.Image:
    if bg is None:
        return Image.new("RGB", (CANVAS_W, CANVAS_H), "#0d0d1a")
    if isinstance(bg, str):
        if os.path.exists(bg):
            return Image.open(bg).convert("RGB").resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
        return Image.new("RGB", (CANVAS_W, CANVAS_H), bg)
    if isinstance(bg, Image.Image):
        return bg.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
    return Image.new("RGB", (CANVAS_W, CANVAS_H), "#0d0d1a")


# ── 曲绘 ──────────────────────────────────────────────
def _cover_url(filename: str) -> str:
    if not filename:
        return ""
    if filename.startswith("http"):
        return filename
    name, _, ext = filename.rpartition(".")
    return f"{COVER_BASE}/{name}_thumb.{ext}"


def _load_cover(filename: str) -> Image.Image | None:
    if not filename:
        return None
    if filename in _cover_cache:
        return _cover_cache[filename]

    url = _cover_url(filename)
    try:
        req = Request(url, headers={"User-Agent": "PRPQQBot/1.0"})
        with urlopen(req, timeout=5) as resp:
            img = Image.open(BytesIO(resp.read())).convert("RGBA")
            img = img.resize((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
            _cover_cache[filename] = img
            return img
    except Exception:
        _cover_cache[filename] = None
        return None


# ── 用户信息卡 ─────────────────────────────────────────
def _draw_user_card(draw: ImageDraw.Draw, username: str, records: List[dict]):
    b35 = records[:35]
    b15 = records[35:50]
    b35_avg = sum(r["rating"] for r in b35) / len(b35) if b35 else 0
    b15_avg = sum(r["rating"] for r in b15) / len(b15) if b15 else 0
    player_rating = (sum(r["rating"] for r in b35) + sum(r["rating"] for r in b15)) / 50.0

    x, y, w, h = MARGIN, USER_CARD_Y, USER_CARD_W, USER_CARD_H
    draw.rounded_rectangle(
        [x, y, x + w, y + h], radius=6, fill=USER_BG, outline=BORDER_COLOR, width=1,
    )

    font_name = _get_font(18, bold=True)
    font_stat = _get_font(13)
    font_val = _get_font(20, bold=True)

    draw.text((x + 16, y + 10), username, fill=TEXT_WHITE, font=font_name)

    col_w = (w - 32) // 3
    for i, (label, value) in enumerate([
        ("B35 avg", f"{b35_avg:.2f}"),
        ("B15 avg", f"{b15_avg:.2f}"),
        ("Rating", f"{player_rating:.4f}"),
    ]):
        cx = x + 16 + i * col_w
        draw.text((cx, y + 38), label, fill=TEXT_DIM, font=font_stat)
        draw.text((cx, y + 54), value, fill=TEXT_WHITE, font=font_val)


# ── 歌曲卡片 ──────────────────────────────────────────
def _card_x(col: int) -> int:
    return MARGIN + col * (CARD_W + GAP_X)


def _card_y(base_y: int, row: int) -> int:
    return base_y + row * (CARD_H + GAP_Y)


def _draw_card(draw: ImageDraw.Draw, img: Image.Image,
               x: int, y: int, record: dict, is_b35: bool):
    diff = record["difficulty"]
    level = record["level"]
    score = record["score"]
    rating = record["rating"]
    title = record["title"]

    card_bg = B35_BG if is_b35 else B15_BG
    diff_color = DIFF_COLORS.get(diff, "#888888")

    draw.rounded_rectangle(
        [x, y, x + CARD_W, y + CARD_H], radius=4,
        fill=card_bg, outline=BORDER_COLOR, width=1,
    )

    # 曲绘
    thumb_x = x + THUMB_PAD_X
    thumb_y = y + THUMB_PAD_Y
    cover = record.get("cover_img") or _load_cover(record.get("cover", ""))
    if cover:
        rgb = tuple(int(card_bg[i+1:i+3], 16) for i in (1, 3, 5))
        bg = Image.new("RGBA", (THUMB_SIZE, THUMB_SIZE), rgb + (255,))
        bg.paste(cover, (0, 0), cover)
        img.paste(bg.convert("RGB"), (thumb_x, thumb_y))
    else:
        draw.rectangle(
            [thumb_x, thumb_y, thumb_x + THUMB_SIZE, thumb_y + THUMB_SIZE],
            fill="#2a2a3a", outline="#444466",
        )

    text_x = thumb_x + THUMB_SIZE + 12

    draw.text((text_x, y + 8), title, fill=TEXT_WHITE, font=_get_font(13))
    draw.text((text_x, y + 28), f"[{diff.upper()}]  {level}",
              fill=diff_color, font=_get_font(13, bold=True))
    draw.text((text_x, y + 48), f"{score:,}", fill=TEXT_WHITE, font=_get_font(16, bold=True))
    draw.text((text_x + 120, y + 51), f"★ {rating:.2f}",
              fill=TEXT_DIM, font=_get_font(12))


def _draw_section_title(draw: ImageDraw.Draw, y: int, text: str):
    font = _get_font(16, bold=True)
    tw = draw.textbbox((0, 0), text, font=font)[2]
    draw.text(((CANVAS_W - tw) // 2, y), text, fill=TITLE_COLOR, font=font)


def _draw_section(draw: ImageDraw.Draw, img: Image.Image, start_y: int,
                  title: str, records: list, is_b35: bool):
    _draw_section_title(draw, start_y, title)
    cards_y = start_y + TITLE_H + 8
    for i, record in enumerate(records):
        x = _card_x(i % COLS)
        y = _card_y(cards_y, i // COLS)
        _draw_card(draw, img, x, y, record, is_b35)


# ── 主入口 ────────────────────────────────────────────
def generate(records: List[dict], username: str = "",
             background=None) -> Image.Image:
    """生成 B50 图片，返回 PIL Image。"""
    b35 = records[:35]
    b15 = records[35:50]

    img = load_background(background)
    draw = ImageDraw.Draw(img)

    _draw_user_card(draw, username, records)
    _draw_section(draw, img, CONTENT_TOP, "B35 (旧赛季)", b35, is_b35=True)

    b15_y = CONTENT_TOP + _section_h(B35_ROWS) + SECTION_GAP
    _draw_section(draw, img, b15_y, "B15 (新赛季)", b15, is_b35=False)

    return img
