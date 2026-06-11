# Generates enemy.bmp - a 32x32, 8bpp Sega Genesis console sprite
# Palette: index 0 = magenta (transparent, matches player sheet convention)
$W = 32; $H = 32
$g = New-Object 'byte[,]' $H, $W   # [y,x], initialised to 0 (transparent)

function Rect($x0, $y0, $x1, $y1, $c) {
    for ($y = $y0; $y -le $y1; $y++) {
        for ($x = $x0; $x -le $x1; $x++) {
            if ($x -ge 0 -and $x -lt $W -and $y -ge 0 -and $y -lt $H) { $g[$y, $x] = $c }
        }
    }
}
function Px($x, $y, $c) { if ($x -ge 0 -and $x -lt $W -and $y -ge 0 -and $y -lt $H) { $g[$y, $x] = $c } }

# ---- Console body (black box, rows 3..28) ----
Rect 3 3 28 28 1
# round the corners
Px 3 3 0; Px 4 3 0; Px 3 4 0
Px 28 3 0; Px 27 3 0; Px 28 4 0
Px 3 28 0; Px 4 28 0; Px 3 27 0
Px 28 28 0; Px 27 28 0; Px 28 27 0

# ---- Top surface (3/4 view), mid grey ----
Rect 5 4 26 11 3
Rect 5 4 26 4 4            # top highlight edge
# cartridge slot (recessed)
Rect 7 6 17 10 2
Rect 8 7 16 9 1
# power switch (white) + red reset, top right
Rect 20 6 23 8 5
Rect 24 6 25 7 6
Px 21 10 8                 # power LED (blue)

# ---- Front face ----
# red signature stripe
Rect 4 14 27 16 6
Rect 4 15 27 15 7         # darker red shading line
# SEGA-style badge, front left
Rect 5 19 12 21 4
Rect 6 20 11 20 5
# vents/expansion lines, front right
Rect 16 19 26 19 3
Rect 16 21 26 21 3
Rect 16 23 26 23 3
# controller ports, bottom
Rect 6 24 11 26 2
Rect 7 25 10 25 1
Rect 20 24 25 26 2
Rect 21 25 24 25 1
# bottom shadow
Rect 4 27 27 27 2

# ---- Palette (RGB) ----
$pal = @(
    @(248, 0, 248),   # 0 transparent (magenta)
    @(16, 16, 16),    # 1 near-black
    @(44, 44, 48),    # 2 dark grey
    @(90, 92, 96),    # 3 mid grey
    @(150, 152, 156), # 4 light grey
    @(235, 235, 235), # 5 white
    @(210, 30, 30),   # 6 red
    @(120, 16, 16),   # 7 dark red
    @(30, 60, 140)    # 8 blue LED
)

# ---- Write 8bpp BMP (bottom-up) ----
$dataOffset = 54 + 256 * 4
$rowSize = $W                      # 32 -> already 4-byte aligned
$imgSize = $rowSize * $H
$fileSize = $dataOffset + $imgSize
$bytes = New-Object 'byte[]' $fileSize

function PutI32($arr, $off, $val) {
    $arr[$off]   = $val -band 0xFF
    $arr[$off+1] = ($val -shr 8) -band 0xFF
    $arr[$off+2] = ($val -shr 16) -band 0xFF
    $arr[$off+3] = ($val -shr 24) -band 0xFF
}

$bytes[0] = [byte][char]'B'; $bytes[1] = [byte][char]'M'
PutI32 $bytes 2 $fileSize
PutI32 $bytes 10 $dataOffset
PutI32 $bytes 14 40           # DIB header size
PutI32 $bytes 18 $W
PutI32 $bytes 22 $H
$bytes[26] = 1; $bytes[27] = 0           # planes
$bytes[28] = 8; $bytes[29] = 0           # bpp
PutI32 $bytes 34 $imgSize

# palette (BGRA), 256 entries
for ($i = 0; $i -lt 256; $i++) {
    $o = 54 + $i * 4
    if ($i -lt $pal.Count) {
        $bytes[$o]   = [byte]$pal[$i][2]   # B
        $bytes[$o+1] = [byte]$pal[$i][1]   # G
        $bytes[$o+2] = [byte]$pal[$i][0]   # R
    }
    $bytes[$o+3] = 0
}

# ---- Downscale art to 2/3 size, anchored top-left (sprite stays a 32x32 cell) ----
$DST = 21                              # 32 * 2/3 ~= 21
$o = New-Object 'byte[,]' $H, $W       # transparent (index 0) padding
for ($dy = 0; $dy -lt $DST; $dy++) {
    $sy = [int][math]::Floor($dy * $H / $DST)
    for ($dx = 0; $dx -lt $DST; $dx++) {
        $sx = [int][math]::Floor($dx * $W / $DST)
        $o[$dy, $dx] = $g[$sy, $sx]
    }
}

# pixels, bottom-up
for ($y = 0; $y -lt $H; $y++) {
    $srcY = $H - 1 - $y
    for ($x = 0; $x -lt $W; $x++) {
        $bytes[$dataOffset + $y * $rowSize + $x] = $o[$srcY, $x]
    }
}

$out = Join-Path $PSScriptRoot '..\enemy.bmp'
[System.IO.File]::WriteAllBytes((Resolve-Path -LiteralPath (Split-Path $out)).Path + '\enemy.bmp', $bytes)
Write-Output "Wrote enemy.bmp ($fileSize bytes)"
