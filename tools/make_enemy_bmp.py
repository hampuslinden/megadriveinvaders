#!/usr/bin/env python3
# Generates enemy.bmp - a 32x32, 8bpp Sega Genesis console sprite.
# Palette: index 0 = magenta (transparent, matches the player sheet convention).
# The detailed art is drawn at full 32x32 then downscaled to ~2/3 (21x21) in the
# top-left of the cell, so it lines up with main.c's ENEMY_SIZE hit-box.
import os

from snesbmp import Canvas, save_bmp

W = H = 32
c = Canvas(W, H)

# ---- Console body (black box, rows 3..28) ----
c.rect(3, 3, 28, 28, 1)
# round the corners
c.px(3, 3, 0); c.px(4, 3, 0); c.px(3, 4, 0)
c.px(28, 3, 0); c.px(27, 3, 0); c.px(28, 4, 0)
c.px(3, 28, 0); c.px(4, 28, 0); c.px(3, 27, 0)
c.px(28, 28, 0); c.px(27, 28, 0); c.px(28, 27, 0)

# ---- Top surface (3/4 view), mid grey ----
c.rect(5, 4, 26, 11, 3)
c.rect(5, 4, 26, 4, 4)            # top highlight edge
# cartridge slot (recessed)
c.rect(7, 6, 17, 10, 2)
c.rect(8, 7, 16, 9, 1)
# power switch (white) + red reset, top right
c.rect(20, 6, 23, 8, 5)
c.rect(24, 6, 25, 7, 6)
c.px(21, 10, 8)                   # power LED (blue)

# ---- Front face ----
# red signature stripe
c.rect(4, 14, 27, 16, 6)
c.rect(4, 15, 27, 15, 7)          # darker red shading line
# SEGA-style badge, front left
c.rect(5, 19, 12, 21, 4)
c.rect(6, 20, 11, 20, 5)
# vents/expansion lines, front right
c.rect(16, 19, 26, 19, 3)
c.rect(16, 21, 26, 21, 3)
c.rect(16, 23, 26, 23, 3)
# controller ports, bottom
c.rect(6, 24, 11, 26, 2)
c.rect(7, 25, 10, 25, 1)
c.rect(20, 24, 25, 26, 2)
c.rect(21, 25, 24, 25, 1)
# bottom shadow
c.rect(4, 27, 27, 27, 2)

pal = [
    (248, 0, 248),    # 0 transparent (magenta)
    (16, 16, 16),     # 1 near-black
    (44, 44, 48),     # 2 dark grey
    (90, 92, 96),     # 3 mid grey
    (150, 152, 156),  # 4 light grey
    (235, 235, 235),  # 5 white
    (210, 30, 30),    # 6 red
    (120, 16, 16),    # 7 dark red
    (30, 60, 140),    # 8 blue LED
]

# ---- Downscale art to 2/3 size, anchored top-left (cell stays 32x32) ----
c.downscale_into(21)              # 32 * 2/3 ~= 21

out = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "enemy.bmp"))
size = save_bmp(out, c, pal)
print(f"Wrote enemy.bmp ({size} bytes)")
