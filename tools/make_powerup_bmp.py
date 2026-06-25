#!/usr/bin/env python3
# Generates powerup.bmp - a 32x32, 8bpp "bomb" pickup sprite.
# Palette index 0 = magenta (transparent), like the other sprites.
# The bomb is drawn at HALF size (a 16x16 figure in the top-left of the 32x32
# cell) so it reads as a small pickup on screen; main.c's POWERUP_SIZE hit-box
# matches that upper-left 16x16. A round dark bomb body with a highlight + shine,
# a metal cap, and a lit fuse spark on top.
import os

from snesbmp import Canvas, save_bmp

W = H = 32
c = Canvas(W, H)

# --- Body: filled circle, centre (7,9) radius 5 -> color 1 (dark body) ---
cx, cy, r = 7, 9, 5
for y in range(16):
    for x in range(16):
        dx = x - cx
        dy = y - cy
        d2 = dx * dx + dy * dy
        if d2 <= r * r:
            c.px(x, y, 1)
        # Soft highlight arc on the upper-left quadrant -> color 2
        if d2 <= (r - 1) * (r - 1) and d2 >= (r - 3) * (r - 3) and dx < 0 and dy < 0:
            c.px(x, y, 2)

# --- Specular shine: a small bright blob on the upper-left -> color 5 (white) ---
for y, x in ((6, 5), (6, 6), (7, 5)):
    c.px(x, y, 5)

# --- Metal cap: short stub on top of the body -> color 3 ---
for y in range(3, 5):
    for x in range(6, 9):
        c.px(x, y, 3)

# --- Fuse cord rising from the cap, curling up-right -> color 3 ---
for y, x in ((2, 9), (1, 10), (1, 11)):
    c.px(x, y, 3)

# --- Lit spark at the tip of the fuse -> color 4 (yellow) + 5 (white core) ---
c.px(11, 0, 4); c.px(12, 0, 4); c.px(12, 1, 4); c.px(10, 0, 4)
c.px(11, 0, 5)

pal = [
    (248, 0, 248),    # 0 transparent
    (30, 30, 44),     # 1 dark body
    (80, 80, 110),    # 2 body highlight
    (120, 120, 135),  # 3 metal cap / fuse
    (255, 215, 40),   # 4 spark yellow
    (255, 255, 255),  # 5 white shine
]

out = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "powerup.bmp"))
size = save_bmp(out, c, pal)
print(f"Wrote powerup.bmp ({size} bytes)")
