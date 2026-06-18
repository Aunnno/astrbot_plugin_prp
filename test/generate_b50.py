"""
B50 成绩图片生成脚本

布局: 用户信息卡 + B35 区块 (7×5) + B15 区块 (3×5)

用法: python generate_b50.py [--real]
"""

import argparse
import os
from typing import List, Dict, Any

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
USER_CARD_Y = MARGIN

THUMB_SIZE = 64
THUMB_PAD_X = 8
THUMB_PAD_Y = (CARD_H - THUMB_SIZE) // 2

GRID_W = COLS * CARD_W + (COLS - 1) * GAP_X
CANVAS_W = MARGIN * 2 + GRID_W


def _section_h(rows: int) -> int:
    return TITLE_H + 8 + rows * CARD_H + (rows - 1) * GAP_Y


# 画布: 用户卡 + 间距 + B35 区块 + 间距 + B15 区块
CONTENT_TOP = MARGIN + USER_CARD_H + 20
CANVAS_H = CONTENT_TOP + _section_h(B35_ROWS) + SECTION_GAP + _section_h(B15_ROWS) + MARGIN

# 难度配色
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


# ── 模拟数据 ───────────────────────────────────────────
def _calc_rating(score: int, level: float) -> float:
    """根据公式计算单曲 Rating (API 返回的是此值 ×100 的整数)"""
    c = level
    if score >= 1009000:
        # INF+ 公式 (简化: 忽略 1.35 次幂，用线性近似)
        phi = score / 1000000.0
        return 7 + 3 * (1000 * phi - 1009) + 10 * c
    elif score >= 1000000:
        # INF 公式
        phi = score / 1000000.0
        return (2000.0 / 3.0) * (phi - 1) + 10 * c
    else:
        # 非 INF 公式
        phi = score / 1000000.0
        # 评级惩罚 (简化: 基于 score)
        if score >= 990000:
            penalty = 1
        elif score >= 980000:
            penalty = 2
        elif score >= 970000:
            penalty = 3
        elif score >= 950000:
            penalty = 4
        elif score >= 930000:
            penalty = 5
        elif score >= 900000:
            penalty = 6
        else:
            penalty = 9
        return max(10 * c * (phi ** 1.5) - penalty, 0)


def generate_mock_data() -> List[Dict[str, Any]]:
    mock_songs = [
        ("Mystical Observer", "massive", 16.8),
        ("天使光輪", "massive", 16.7),
        ("キミとボクへの葬送歌", "massive", 16.5),
        ("Rosenkranz", "massive", 16.4),
        ("Re:End of a Dream", "massive", 16.3),
        ("CO5M1C R4ILR0AD", "massive", 16.2),
        ("Rrhar'il", "massive", 16.1),
        ("INFiNiTE ENERZY", "massive", 16.0),
        ("Final Hope", "massive", 15.9),
        ("Goodrage", "massive", 15.9),
        ("Cthugha", "massive", 15.8),
        ("Destr0yer", "massive", 15.8),
        ("Spasmodic", "massive", 15.7),
        ("CROSS†SOUL", "massive", 15.7),
        ("Distorted Fate", "massive", 15.6),
        ("Lucent Historia", "massive", 15.6),
        ("Eltaw", "invaded", 15.5),
        ("Désive", "invaded", 15.5),
        ("Distorted Fate", "invaded", 15.4),
        ("Temporal Shifting", "massive", 15.4),
        ("Horizon Blue", "massive", 15.3),
        ("Re:End of a Dream", "invaded", 15.3),
        ("Stasis", "massive", 15.2),
        ("Chronomia", "massive", 15.2),
        ("Lucent Historia", "invaded", 15.1),
        ("Le Porteur d'Ombre", "massive", 15.1),
        ("αterlβus", "massive", 15.0),
        ("Benga Fureak", "massive", 15.0),
        ("Eltaw", "massive", 14.9),
        ("祈りの記憶", "massive", 14.9),
        ("Désive", "massive", 14.8),
        ("Abstr[A]ct", "massive", 14.8),
        ("Daybreaker", "massive", 14.7),
        ("イニシャライザブル", "massive", 14.7),
        ("水晶世界", "massive", 14.6),
        ("!nterroban(,", "massive", 15.8),
        ("Colorless Coldness", "massive", 15.0),
        ("Recollect Lines", "massive", 14.5),
        ("Halcyon", "massive", 14.5),
        ("Rrhar'il", "invaded", 14.4),
        ("Seventh Heaven", "massive", 14.4),
        ("Λzure Vixen", "massive", 14.3),
        ("Nhelv", "massive", 14.3),
        ("Altale", "massive", 14.2),
        ("Stasis", "invaded", 14.2),
        ("Paradigm", "reboot", 14.1),
        ("零の位相", "massive", 14.1),
        ("Singularity", "massive", 14.0),
        ("Fragmenta", "detected", 14.0),
        ("Chronologika", "massive", 14.0),
    ]

    records = []
    for i, (title, diff, level) in enumerate(mock_songs[:50]):
        # B35 部分高分 (INF 附近), B15 部分略低分
        if i < 35:
            score = int(1020000 - i * 1000 + (hash(title) % 3000))
        else:
            score = int(1010000 - (i - 35) * 2000 + (hash(title) % 5000))
        score = max(850000, min(score, 1010000))
        r = _calc_rating(score, level)
        records.append({
            "title": title,
            "difficulty": diff,
            "level": level,
            "score": score,
            "rating": r,
        })
    # 按 rating 降序排列
    records.sort(key=lambda x: x["rating"], reverse=True)
    return records


# ── 字体 ───────────────────────────────────────────────
def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
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
def load_background(bg) -> Image.Image:
    if bg is None:
        return Image.new("RGB", (CANVAS_W, CANVAS_H), "#0d0d1a")
    if isinstance(bg, str):
        if os.path.exists(bg):
            img = Image.open(bg).convert("RGB")
            return img.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
        return Image.new("RGB", (CANVAS_W, CANVAS_H), bg)
    if isinstance(bg, Image.Image):
        return bg.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
    return Image.new("RGB", (CANVAS_W, CANVAS_H), "#0d0d1a")


# ── 用户信息卡 ─────────────────────────────────────────
def draw_user_card(draw: ImageDraw.Draw, username: str, records: List[dict]):
    b35 = records[:35]
    b15 = records[35:50]
    b35_avg = sum(r["rating"] for r in b35) / len(b35) if b35 else 0
    b15_avg = sum(r["rating"] for r in b15) / len(b15) if b15 else 0
    # 玩家 Rating = (B35总和 + B15总和) / 50
    player_rating = (sum(r["rating"] for r in b35) + sum(r["rating"] for r in b15)) / 50.0

    x = MARGIN
    y = USER_CARD_Y
    w = USER_CARD_W
    h = USER_CARD_H

    draw.rounded_rectangle(
        [x, y, x + w, y + h], radius=6, fill=USER_BG, outline=BORDER_COLOR, width=1,
    )

    font_name = get_font(18, bold=True)
    font_stat = get_font(13)
    font_val = get_font(20, bold=True)

    draw.text((x + 16, y + 10), username, fill=TEXT_WHITE, font=font_name)

    col_w = (w - 32) // 3
    stats = [
        ("B35 avg", f"{b35_avg:.2f}"),
        ("B15 avg", f"{b15_avg:.2f}"),
        ("Rating", f"{player_rating:.4f}"),
    ]
    for i, (label, value) in enumerate(stats):
        cx = x + 16 + i * col_w
        draw.text((cx, y + 38), label, fill=TEXT_DIM, font=font_stat)
        draw.text((cx, y + 54), value, fill=TEXT_WHITE, font=font_val)


# ── 歌曲卡片 ──────────────────────────────────────────
def _card_x(col: int) -> int:
    return MARGIN + col * (CARD_W + GAP_X)


def _card_y(base_y: int, row: int) -> int:
    return base_y + row * (CARD_H + GAP_Y)


def draw_card(draw: ImageDraw.Draw, x: int, y: int, record: dict, is_b35: bool):
    diff = record["difficulty"]
    level = record["level"]
    score = record["score"]
    rating = record["rating"]
    title = record["title"]

    bg = B35_BG if is_b35 else B15_BG
    diff_color = DIFF_COLORS.get(diff, "#888888")

    draw.rounded_rectangle(
        [x, y, x + CARD_W, y + CARD_H], radius=4,
        fill=bg, outline=BORDER_COLOR, width=1,
    )

    # 左侧: 曲绘占位
    thumb_x = x + THUMB_PAD_X
    thumb_y = y + THUMB_PAD_Y
    draw.rectangle(
        [thumb_x, thumb_y, thumb_x + THUMB_SIZE, thumb_y + THUMB_SIZE],
        fill="#2a2a3a", outline="#444466",
    )

    text_x = thumb_x + THUMB_SIZE + 12

    font_title = get_font(13)
    font_diff = get_font(13, bold=True)
    font_score = get_font(16, bold=True)
    font_rating = get_font(12)

    # 第1行: 歌曲名
    draw.text((text_x, y + 8), title, fill=TEXT_WHITE, font=font_title)

    # 第2行: [难度] 定数
    draw.text((text_x, y + 28), f"[{diff.upper()}]  {level}", fill=diff_color, font=font_diff)

    # 第3行: 分数 + 单曲Rating
    draw.text((text_x, y + 48), f"{score:,}", fill=TEXT_WHITE, font=font_score)
    draw.text((text_x + 120, y + 51), f"★ {rating:.2f}", fill=TEXT_DIM, font=font_rating)


# ── 区块绘制 ──────────────────────────────────────────
def draw_section_title(draw: ImageDraw.Draw, y: int, text: str):
    font = get_font(16, bold=True)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (CANVAS_W - tw) // 2
    draw.text((x, y), text, fill=TITLE_COLOR, font=font)


def draw_section(draw: ImageDraw.Draw, start_y: int, title: str,
                 records: list, is_b35: bool):
    draw_section_title(draw, start_y, title)
    cards_y = start_y + TITLE_H + 8

    for i, record in enumerate(records):
        row = i // COLS
        col = i % COLS
        x = _card_x(col)
        y = _card_y(cards_y, row)
        draw_card(draw, x, y, record, is_b35)


# ── 主生成函数 ────────────────────────────────────────
def generate_image(records: List[dict], output_path: str = "b50_sample.png",
                   background=None, username: str = "") -> Image.Image:
    # B35 前 35 条，剩余为 B15
    b35 = records[:35]
    b15 = records[35:50]

    img = load_background(background)
    draw = ImageDraw.Draw(img)

    # 用户信息卡
    draw_user_card(draw, username or "Player", records)

    # B35
    draw_section(draw, CONTENT_TOP, "B35 (旧赛季)", b35, is_b35=True)

    # B15
    b15_y = CONTENT_TOP + _section_h(B35_ROWS) + SECTION_GAP
    draw_section(draw, b15_y, "B15 (新赛季)", b15, is_b35=False)

    img.save(output_path)
    print(f"已生成: {output_path} ({CANVAS_W}×{CANVAS_H})")


# ── 真实 API ───────────────────────────────────────────
async def fetch_real_data(username: str, access_token: str) -> List[Dict[str, Any]]:
    import aiohttp

    base = "https://api.prp.icel.site/api/v2"
    headers = {"Authorization": f"Bearer {access_token}"}
    all_records = []

    async with aiohttp.ClientSession() as session:
        for b15, limit in [(False, 35), (True, 15)]:
            params = {
                "scope": "b50", "b15": b15, "page_size": limit,
                "sort_by": "rating", "order": "desc",
            }
            async with session.get(
                f"{base}/records/{username}", params=params, headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for r in data.get("records", []):
                        chart = r.get("chart", {})
                        all_records.append({
                            "title": chart.get("title", ""),
                            "difficulty": chart.get("difficulty", ""),
                            "level": chart.get("level", 0),
                            "score": r.get("score", 0),
                            "rating": r.get("rating", 0) / 100.0,  # API ×100 → float
                            "cover": chart.get("cover", ""),
                        })
    return all_records


# ── 入口 ───────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", action="store_true")
    parser.add_argument("--username", default="aunnno")
    parser.add_argument("--token", default="")
    parser.add_argument("--background", default=None, help="背景颜色或图片路径")
    parser.add_argument("-o", "--output", default="b50_sample.png")
    args = parser.parse_args()

    if args.real and args.token:
        import asyncio
        records = asyncio.run(fetch_real_data(args.username, args.token))
        print(f"API 获取 {len(records)} 条记录")
    else:
        if args.real:
            print("⚠ 需要 --token 参数，使用模拟数据")
        records = generate_mock_data()
        print(f"模拟 {len(records)} 条记录")

    generate_image(records, args.output, background=args.background,
                   username=args.username if args.real else "Player")


if __name__ == "__main__":
    main()
