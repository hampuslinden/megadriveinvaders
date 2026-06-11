# Rebuilds sprites.bmp (player) at 2/3 size, anchored in the top-left of the
# 32x32 sprite cell. SNES sprites can't scale in hardware, so we shrink the art
# itself and pad the rest of the cell with the transparent index (0).
#
# The original 32x32 art is backed up once to tools/sprites_src.bmp and always
# read from there, so re-running never double-shrinks.
$W = 32; $H = 32
$dataOffset = 54 + 256 * 4
$rowSize = $W
$SCALE = 21                              # 32 * 2/3 ~= 21

$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$dst  = Join-Path $root 'sprites.bmp'
$src  = Join-Path $PSScriptRoot 'sprites_src.bmp'

if (-not (Test-Path -LiteralPath $src)) {
    Copy-Item -LiteralPath $dst -Destination $src      # preserve pristine original
}

$bytes = [System.IO.File]::ReadAllBytes($src)

# Read source pixel indices (BMP is stored bottom-up); g[y,x] with y=0 at top.
$g = New-Object 'byte[,]' $H, $W
for ($y = 0; $y -lt $H; $y++) {
    $srcY = $H - 1 - $y
    for ($x = 0; $x -lt $W; $x++) {
        $g[$y, $x] = $bytes[$dataOffset + $srcY * $rowSize + $x]
    }
}

# Nearest-neighbour downscale into the top-left, rest transparent (0).
$o = New-Object 'byte[,]' $H, $W
for ($dy = 0; $dy -lt $SCALE; $dy++) {
    $sy = [int][math]::Floor($dy * $H / $SCALE)
    for ($dx = 0; $dx -lt $SCALE; $dx++) {
        $sx = [int][math]::Floor($dx * $W / $SCALE)
        $o[$dy, $dx] = $g[$sy, $sx]
    }
}

# Write pixels back into the byte buffer (bottom-up); header + palette untouched.
for ($y = 0; $y -lt $H; $y++) {
    $srcY = $H - 1 - $y
    for ($x = 0; $x -lt $W; $x++) {
        $bytes[$dataOffset + $y * $rowSize + $x] = $o[$srcY, $x]
    }
}

[System.IO.File]::WriteAllBytes($dst, $bytes)
Write-Output "Wrote sprites.bmp (player art scaled to ${SCALE}x${SCALE}, top-left of 32x32 cell)"
