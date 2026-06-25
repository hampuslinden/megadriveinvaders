#!/usr/bin/env python3
# Generates bullet.bmp - an 8x8, 8bpp energy-shot sprite.
# Palette: index 0 = magenta (transparent).
import os

from snesbmp import Canvas, save_bmp

W = H = 8

# 1=white core, 2=yellow, 3=orange edge
art = [
    "..3333..",
    ".32222 3.".replace(" ", ""),
    "3211123",
    "3211123",
    "3211123",
    "3211123",
    ".32223.",
    "..3333..",
]

c = Canvas(W, H)
for y in range(H):
    row = art[y]
    row += "." * (W - len(row))     # normalise to 8 chars per row
    for x in range(W):
        ch = row[x]
        c.px(x, y, int(ch) if ch in "123" else 0)

pal = [
    (248, 0, 248),     # 0 transparent
    (255, 255, 255),   # 1 white core
    (255, 230, 40),    # 2 yellow
    (255, 130, 20),    # 3 orange
]

out = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "bullet.bmp"))
size = save_bmp(out, c, pal)
print(f"Wrote bullet.bmp ({size} bytes)")
