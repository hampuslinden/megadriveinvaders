#!/usr/bin/env python3
# Generates tac2.bmp - a 32x32, 8bpp "tougher enemy" sprite shaped like a
# Suncom TAC-2 arcade joystick: a red ball-top stick on a chrome shaft rising
# from a chunky black base with a red fire button.
#
# Like enemy.bmp, the art is drawn in the TOP-LEFT 21x21 of the 32x32 cell so it
# lines up with main.c's ENEMY_SIZE (21) hit-box; the rest of the cell is
# transparent (palette index 0 = magenta, matching the other sprite sheets).
import os

from snesbmp import Canvas, save_bmp

W = H = 32
c = Canvas(W, H)

# ---- Base: chunky black slab with a chrome top edge, rows 13..20 ----
c.rect(1, 14, 19, 20, 1)          # black base body
c.rect(1, 13, 19, 13, 3)          # chrome top lip
c.rect(1, 20, 19, 20, 2)          # bottom shadow line
# round the base corners
c.px(1, 13, 0); c.px(19, 13, 0); c.px(1, 20, 0); c.px(19, 20, 0)

# ---- Fire button: red dome on the left of the base ----
c.disc(5, 16, 2, 4)
c.px(4, 15, 6)                    # button highlight (white)
c.px(5, 17, 5)                    # button shading (dark red)

# ---- Shaft: chrome stick rising from base centre, rows 7..13 ----
c.rect(9, 7, 11, 13, 3)           # silver shaft
c.rect(11, 7, 11, 13, 2)          # right-side shading
c.rect(9, 7, 9, 13, 6)            # left-edge highlight

# ---- Ball top: red knob, centred at (10,4) ----
c.disc(10, 4, 3, 4)               # red ball
c.px(8, 2, 6); c.px(9, 2, 6)      # upper-left specular highlight (white)
c.px(12, 5, 5); c.px(11, 6, 5)    # lower-right shading (dark red)

pal = [
    (248, 0, 248),    # 0 transparent (magenta)
    (16, 16, 18),     # 1 black base
    (40, 40, 44),     # 2 dark grey shadow
    (170, 174, 182),  # 3 chrome / silver
    (220, 40, 36),    # 4 red
    (130, 18, 16),    # 5 dark red shading
    (245, 245, 245),  # 6 white highlight
]

out = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "tac2.bmp"))
size = save_bmp(out, c, pal)
print(f"Wrote tac2.bmp ({size} bytes)")
