"""Shared helpers for the tools/ art generators.

The SNES build's source sprites are authored as 8bpp (256-colour) BMPs whose
palette index 0 is magenta = transparent, matching gfx4snes' convention. These
generators build a grid of palette indices and write a minimal 8bpp BMP by hand
(no image-library dependency); this module holds the drawing canvas and the BMP
read/write plumbing that every generator shares.

Pure standard library, so it runs unchanged on Windows, Linux and WSL.
"""
import struct

# 14-byte BITMAPFILEHEADER + 40-byte BITMAPINFOHEADER, then a full 256-entry
# palette (4 bytes each), then the pixel data.
_HEADER_SIZE = 54
_PALETTE_ENTRIES = 256
DATA_OFFSET = _HEADER_SIZE + _PALETTE_ENTRIES * 4   # 1078


def _row_size(w):
    """BMP rows are padded to a 4-byte boundary."""
    return (w + 3) & ~3


class Canvas:
    """A width x height grid of palette indices, addressed [y][x], origin top-left.

    Starts filled with index 0 (transparent). Drawing ops are bounds-checked, so
    off-canvas pixels are silently dropped (matching the .ps1 Px/Rect guards).
    """

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.g = [[0] * w for _ in range(h)]

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = c

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px(x, y, c)

    def disc(self, cx, cy, r, c):
        """Filled disc, centre (cx, cy), radius r."""
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                dx = x - cx
                dy = y - cy
                if dx * dx + dy * dy <= r * r:
                    self.px(x, y, c)

    def downscale_into(self, scale):
        """Nearest-neighbour shrink of the whole grid into the top-left
        scale x scale region; the rest of the cell becomes transparent (0).

        Uses integer floor division to match PowerShell's [math]::Floor.
        """
        out = [[0] * self.w for _ in range(self.h)]
        for dy in range(scale):
            sy = (dy * self.h) // scale
            for dx in range(scale):
                sx = (dx * self.w) // scale
                out[dy][dx] = self.g[sy][sx]
        self.g = out


def save_bmp(path, canvas, palette):
    """Write a Canvas as an 8bpp BMP.

    palette is a list of (r, g, b) tuples; entries beyond its length are left
    black. Pixel rows are stored bottom-up, as BMP requires.
    """
    w, h = canvas.w, canvas.h
    row_size = _row_size(w)
    img_size = row_size * h
    file_size = DATA_OFFSET + img_size

    b = bytearray(file_size)
    b[0:2] = b"BM"
    struct.pack_into("<I", b, 2, file_size)
    struct.pack_into("<I", b, 10, DATA_OFFSET)
    struct.pack_into("<I", b, 14, 40)          # DIB header size
    struct.pack_into("<i", b, 18, w)
    struct.pack_into("<i", b, 22, h)
    struct.pack_into("<H", b, 26, 1)           # planes
    struct.pack_into("<H", b, 28, 8)           # bits per pixel
    struct.pack_into("<I", b, 34, img_size)

    # Palette: stored BGRA, 256 entries.
    for i, (r, g, bl) in enumerate(palette):
        o = _HEADER_SIZE + i * 4
        b[o] = bl
        b[o + 1] = g
        b[o + 2] = r

    # Pixels, bottom-up.
    for y in range(h):
        src_y = h - 1 - y
        base = DATA_OFFSET + y * row_size
        for x in range(w):
            b[base + x] = canvas.g[src_y][x]

    with open(path, "wb") as f:
        f.write(b)
    return file_size


def read_indexed_bmp(path):
    """Read an 8bpp BMP. Returns (w, h, palette, canvas).

    palette is a list of 256 (r, g, b) tuples; canvas is a Canvas holding the
    pixel indices. Lets a generator load pristine source art, transform it, and
    re-save it byte-for-byte through save_bmp.
    """
    with open(path, "rb") as f:
        b = f.read()

    data_offset = struct.unpack_from("<I", b, 10)[0]
    w = struct.unpack_from("<i", b, 18)[0]
    h = struct.unpack_from("<i", b, 22)[0]
    row_size = _row_size(w)

    palette = []
    for i in range(_PALETTE_ENTRIES):
        o = _HEADER_SIZE + i * 4
        bl, g, r = b[o], b[o + 1], b[o + 2]
        palette.append((r, g, bl))

    canvas = Canvas(w, h)
    for y in range(h):
        src_y = h - 1 - y
        base = data_offset + src_y * row_size
        for x in range(w):
            canvas.g[y][x] = b[base + x]

    return w, h, palette, canvas
