# Generates bullet.bmp - an 8x8, 8bpp energy-shot sprite
# Palette: index 0 = magenta (transparent)
$W = 8; $H = 8
$g = New-Object 'byte[,]' $H, $W

# 1=white core, 2=yellow, 3=orange edge
$art = @(
    '..3333..',
    '.32222 3.'.Replace(' ', ''),
    '3211123',
    '3211123',
    '3211123',
    '3211123',
    '.32223.',
    '..3333..'
)
# Normalise to 8 chars per row
for ($y = 0; $y -lt $H; $y++) {
    $row = $art[$y]
    while ($row.Length -lt $W) { $row += '.' }
    for ($x = 0; $x -lt $W; $x++) {
        $ch = $row[$x]
        switch ($ch) {
            '1' { $g[$y, $x] = 1 }
            '2' { $g[$y, $x] = 2 }
            '3' { $g[$y, $x] = 3 }
            default { $g[$y, $x] = 0 }
        }
    }
}

$pal = @(
    @(248, 0, 248),    # 0 transparent
    @(255, 255, 255),  # 1 white core
    @(255, 230, 40),   # 2 yellow
    @(255, 130, 20)    # 3 orange
)

$dataOffset = 54 + 256 * 4
$rowSize = $W                       # 8 -> 4-byte aligned
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
PutI32 $bytes 14 40
PutI32 $bytes 18 $W
PutI32 $bytes 22 $H
$bytes[26] = 1; $bytes[28] = 8
PutI32 $bytes 34 $imgSize

for ($i = 0; $i -lt 256; $i++) {
    $o = 54 + $i * 4
    if ($i -lt $pal.Count) {
        $bytes[$o]   = [byte]$pal[$i][2]
        $bytes[$o+1] = [byte]$pal[$i][1]
        $bytes[$o+2] = [byte]$pal[$i][0]
    }
}

for ($y = 0; $y -lt $H; $y++) {
    $srcY = $H - 1 - $y
    for ($x = 0; $x -lt $W; $x++) {
        $bytes[$dataOffset + $y * $rowSize + $x] = $g[$srcY, $x]
    }
}

[System.IO.File]::WriteAllBytes('C:\dev\snesgame2\bullet.bmp', $bytes)
Write-Output "Wrote bullet.bmp ($fileSize bytes)"
