"""B50 图片独立测试脚本，调用 utils 模块。"""

import argparse
import asyncio
import importlib.util
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 直接加载 b50_image.py，绕过 __init__.py
_spec = importlib.util.spec_from_file_location(
    "b50_image", os.path.join(_root, "utils", "b50_image.py")
)
_b50 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_b50)
generate_b50_image = _b50.generate

# 注入 mock astrbot，使 prp_api 可独立导入
class _MockLogger:
    def info(self, msg): pass
    def debug(self, msg): pass
    def warning(self, msg): pass

sys.modules["astrbot"] = type(sys)("astrbot")
sys.modules["astrbot"].logger = _MockLogger()

_prp_spec = importlib.util.spec_from_file_location(
    "prp_api", os.path.join(_root, "utils", "prp_api.py")
)
_prp = importlib.util.module_from_spec(_prp_spec)
_prp_spec.loader.exec_module(_prp)
PRPApiClient = _prp.PRPApiClient


def _calc_rating(score: int, level: float) -> float:
    c = level
    if score >= 1009000:
        return 7 + 3 * (1000 * score / 1000000 - 1009) + 10 * c
    elif score >= 1000000:
        return (2000 / 3) * (score / 1000000 - 1) + 10 * c
    else:
        phi = score / 1000000
        if score >= 990000:    penalty = 1
        elif score >= 980000:  penalty = 2
        elif score >= 970000:  penalty = 3
        elif score >= 950000:  penalty = 4
        elif score >= 930000:  penalty = 5
        elif score >= 900000:  penalty = 6
        else:                  penalty = 9
        return max(10 * c * (phi ** 1.5) - penalty, 0)


def generate_mock_data():
    songs = [
        ("Mystical Observer", "massive", 16.8), ("天使光輪", "massive", 16.7),
        ("キミとボクへの葬送歌", "massive", 16.5), ("Rosenkranz", "massive", 16.4),
        ("Re:End of a Dream", "massive", 16.3), ("CO5M1C R4ILR0AD", "massive", 16.2),
        ("Rrhar'il", "massive", 16.1), ("INFiNiTE ENERZY", "massive", 16.0),
        ("Final Hope", "massive", 15.9), ("Goodrage", "massive", 15.9),
        ("Cthugha", "massive", 15.8), ("Destr0yer", "massive", 15.8),
        ("Spasmodic", "massive", 15.7), ("CROSS†SOUL", "massive", 15.7),
        ("Distorted Fate", "massive", 15.6), ("Lucent Historia", "massive", 15.6),
        ("Eltaw", "invaded", 15.5), ("Désive", "invaded", 15.5),
        ("Distorted Fate", "invaded", 15.4), ("Temporal Shifting", "massive", 15.4),
        ("Horizon Blue", "massive", 15.3), ("Re:End of a Dream", "invaded", 15.3),
        ("Stasis", "massive", 15.2), ("Chronomia", "massive", 15.2),
        ("Lucent Historia", "invaded", 15.1), ("Le Porteur d'Ombre", "massive", 15.1),
        ("αterlβus", "massive", 15.0), ("Benga Fureak", "massive", 15.0),
        ("Eltaw", "massive", 14.9), ("祈りの記憶", "massive", 14.9),
        ("Désive", "massive", 14.8), ("Abstr[A]ct", "massive", 14.8),
        ("Daybreaker", "massive", 14.7), ("イニシャライザブル", "massive", 14.7),
        ("水晶世界", "massive", 14.6), ("!nterroban(,", "massive", 15.8),
        ("Colorless Coldness", "massive", 15.0), ("Recollect Lines", "massive", 14.5),
        ("Halcyon", "massive", 14.5), ("Rrhar'il", "invaded", 14.4),
        ("Seventh Heaven", "massive", 14.4), ("Λzure Vixen", "massive", 14.3),
        ("Nhelv", "massive", 14.3), ("Altale", "massive", 14.2),
        ("Stasis", "invaded", 14.2), ("Paradigm", "reboot", 14.1),
        ("零の位相", "massive", 14.1), ("Singularity", "massive", 14.0),
        ("Fragmenta", "detected", 14.0), ("Chronologika", "massive", 14.0),
    ]
    records = []
    for i, (title, diff, level) in enumerate(songs[:50]):
        score = int(1020000 - i * 1000 + (hash(title) % 3000)) if i < 35 \
           else int(1010000 - (i - 35) * 2000 + (hash(title) % 5000))
        score = max(850000, min(score, 1010000))
        records.append({"title": title, "difficulty": diff, "level": level,
                        "score": score, "rating": _calc_rating(score, level)})
    records.sort(key=lambda x: x["rating"], reverse=True)
    return records


async def fetch_real_data(username: str, access_token: str):
    client = PRPApiClient()
    try:
        return await client.get_b50_records(username, access_token)
    finally:
        await client.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", action="store_true")
    parser.add_argument("--username", default="aunnno")
    parser.add_argument("--token", default="")
    parser.add_argument("--background", default=None)
    parser.add_argument("-o", "--output", default="b50_sample.png")
    args = parser.parse_args()

    if args.real and args.token:
        records = asyncio.run(fetch_real_data(args.username, args.token))
        print(f"API 获取 {len(records)} 条记录")
    else:
        if args.real:
            print("⚠ 需要 --token 参数，使用模拟数据")
        records = generate_mock_data()
        print(f"模拟 {len(records)} 条记录")

    img = generate_b50_image(records, username=args.username)
    img.save(args.output)
    print(f"已生成: {args.output} ({img.width}×{img.height})")


if __name__ == "__main__":
    main()
