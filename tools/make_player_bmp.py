#!/usr/bin/env python3
# Rebuilds sprites.bmp (player) at 2/3 size, anchored in the top-left of the
# 32x32 sprite cell. SNES sprites can't scale in hardware, so we shrink the art
# itself and pad the rest of the cell with the transparent index (0).
#
# The original 32x32 art is backed up once to tools/sprites_src.bmp and always
# read from there, so re-running never double-shrinks.
import os
import shutil

from snesbmp import read_indexed_bmp, save_bmp

SCALE = 21                              # 32 * 2/3 ~= 21

here = os.path.dirname(__file__)
dst = os.path.normpath(os.path.join(here, "..", "sprites.bmp"))
src = os.path.join(here, "sprites_src.bmp")

if not os.path.exists(src):
    shutil.copyfile(dst, src)           # preserve the pristine original

w, h, palette, canvas = read_indexed_bmp(src)
canvas.downscale_into(SCALE)            # nearest-neighbour into the top-left
save_bmp(dst, canvas, palette)

print(f"Wrote sprites.bmp (player art scaled to {SCALE}x{SCALE}, top-left of 32x32 cell)")
