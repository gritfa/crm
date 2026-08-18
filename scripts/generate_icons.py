"""生成 PWA 图标 PNG。

只用标准库，不引入 Pillow。图形用有符号距离场（SDF）计算，边缘按距离做
抗锯齿，因此不需要超采样也能得到平滑边界。

    python scripts/generate_icons.py

输出到 app/static/icons/，改动图标后重新执行并提交生成结果即可。
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path


ICON_DIR = Path(__file__).resolve().parents[1] / "app" / "static" / "icons"

# 与 styles.css 的 .brand-mark 渐变保持一致
GRADIENT_FROM = (0x31, 0x57, 0xD5)
GRADIENT_TO = (0x6D, 0x45, 0xD9)


def _rounded_square(x: float, y: float, half: float, radius: float) -> float:
    """圆角方块的有符号距离，内部为负。"""
    dx = abs(x) - (half - radius)
    dy = abs(y) - (half - radius)
    outside = math.hypot(max(dx, 0.0), max(dy, 0.0))
    inside = min(max(dx, dy), 0.0)
    return outside + inside - radius


def _letter_c(x: float, y: float, radius: float, thickness: float) -> float:
    """字母 C 的有符号距离：圆环挖掉右侧 45° 楔形开口。"""
    ring = abs(math.hypot(x, y) - radius) - thickness / 2
    # 楔形：x > 0 且 |y| < x，内部为负
    wedge = max(-x, abs(y) - x)
    # 差集：从圆环里减去楔形
    return max(ring, -wedge)


def _coverage(distance: float) -> float:
    """把距离换算成 0~1 的覆盖率，实现 1 像素宽的抗锯齿边缘。"""
    return min(max(0.5 - distance, 0.0), 1.0)


def render_icon(size: int, *, padding_ratio: float = 0.0) -> bytes:
    """渲染一张 RGBA 图标，返回逐行拼好的原始像素数据。

    padding_ratio > 0 时图形整体缩小，四周留出安全边距（iOS 图标会被系统
    再裁一次圆角，留边可避免边缘被切掉）。
    """
    rows: list[bytes] = []
    center = (size - 1) / 2
    half = size / 2 * (1 - padding_ratio)
    corner_radius = half * 0.44
    letter_radius = half * 0.46
    letter_thickness = half * 0.235

    for py in range(size):
        row = bytearray()
        y = py - center
        for px in range(size):
            x = px - center
            bg_alpha = _coverage(_rounded_square(x, y, half, corner_radius))
            if bg_alpha <= 0.0:
                row += b"\x00\x00\x00\x00"
                continue

            # 沿对角线的线性渐变，和 CSS 的 135deg 方向一致
            t = min(max((x + y) / (2 * half) + 0.5, 0.0), 1.0)
            r = round(GRADIENT_FROM[0] + (GRADIENT_TO[0] - GRADIENT_FROM[0]) * t)
            g = round(GRADIENT_FROM[1] + (GRADIENT_TO[1] - GRADIENT_FROM[1]) * t)
            b = round(GRADIENT_FROM[2] + (GRADIENT_TO[2] - GRADIENT_FROM[2]) * t)

            letter_alpha = _coverage(_letter_c(x, y, letter_radius, letter_thickness))
            if letter_alpha > 0.0:
                r = round(r + (255 - r) * letter_alpha)
                g = round(g + (255 - g) * letter_alpha)
                b = round(b + (255 - b) * letter_alpha)

            row += bytes((r, g, b, round(bg_alpha * 255)))
        rows.append(bytes(row))
    return b"".join(b"\x00" + row for row in rows)


def write_png(path: Path, size: int, raw: bytes) -> None:
    def chunk(tag: bytes, payload: bytes) -> bytes:
        head = struct.pack(">I", len(payload)) + tag
        return head + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8 位 RGBA
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def main() -> None:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    targets = [
        ("icon-192.png", 192, 0.0),
        ("icon-512.png", 512, 0.0),
        # maskable 图标会被系统裁成圆形，图形需要缩在安全区内
        ("icon-maskable-512.png", 512, 0.18),
        ("apple-touch-icon-180.png", 180, 0.0),
    ]
    for name, size, padding in targets:
        write_png(ICON_DIR / name, size, render_icon(size, padding_ratio=padding))
        print(f"生成 {ICON_DIR / name} ({size}x{size})")


if __name__ == "__main__":
    main()
