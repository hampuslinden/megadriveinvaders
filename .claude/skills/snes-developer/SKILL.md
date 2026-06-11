---
name: snes-developer
description: Develop Super Nintendo (SNES) games in C with PVSnesLib, compiling under MSYS2 and running the resulting ROM in the ZSNES emulator. Use for any SNES homebrew task — writing game code, building/linking ROMs, working with graphics/tiles/sprites/sound, the PVSnesLib API, makefiles, or emulator testing in this project.
---

# SNES Developer

You are a Super Nintendo Entertainment System (SNES) homebrew developer. Games are written in **C** (with some 65816 ASM where needed) using the **PVSnesLib** SDK, built with the PVSnesLib toolchain under **MSYS2**, and run in emulation via **ZSNES**.

## Environment

| Thing | Location / Value |
|-------|------------------|
| MSYS2 | `C:/msys64` |
| PVSnesLib | `C:/tools/pvsneslib` (`/c/tools/pvsneslib` inside MSYS2) — set as `PVSNESLIB_HOME` |
| Toolchain | `$PVSNESLIB_HOME/devkitsnes/bin` (`816-tcc`, `wla-65816`, `wla-spc700`, `wlalink`, gfx tools) |
| Emulator | ZSNES at `C:/games/zsnes/SUPERZSNES.exe` — run the built `.sfc`/`.smc` ROM |

**Always confirm `PVSNESLIB_HOME` is set before building.** Inside an MSYS2 shell:
```sh
echo $PVSNESLIB_HOME
export PVSNESLIB_HOME=/c/tools/pvsneslib   # if unset
export PATH=$PVSNESLIB_HOME/devkitsnes/bin:$PVSNESLIB_HOME/devkitsnes/tools:$PATH
```

## Building

PVSnesLib projects use a `Makefile` that includes the SDK's `snes_rules`. From an MSYS2 shell in the project dir:
```sh
make            # compile + link -> produces the ROM (.sfc)
make clean      # remove build artifacts
```

`PVSNESLIB_HOME` is **not** set persistently in the MSYS2 login shell, so it must be exported before `make`. This project includes [build.sh](../../../build.sh) which does that — invoke it from PowerShell (verified working):
```powershell
& C:/msys64/usr/bin/bash.exe -lc "sh /c/dev/snesgame2/build.sh"        # build
& C:/msys64/usr/bin/bash.exe -lc "sh /c/dev/snesgame2/build.sh clean"  # clean
```
Or inline, if not using the script:
```powershell
& C:/msys64/usr/bin/bash.exe -lc "export PVSNESLIB_HOME=/c/tools/pvsneslib; export PATH=\$PVSNESLIB_HOME/devkitsnes/bin:\$PVSNESLIB_HOME/devkitsnes/tools:\$PATH; cd /c/dev/snesgame2 && make"
```
A clean build ends with `Build finished successfully !`. The `Label ... was defined more than once` and `Section ... was discarded` lines from `wlalink` are normal PVSnesLib library noise, not errors.

A minimal PVSnesLib `Makefile`:
```make
ifeq ($(strip $(PVSNESLIB_HOME)),)
$(error PVSNESLIB_HOME is not set)
endif
include $(PVSNESLIB_HOME)/devkitsnes/snes_rules

.PHONY: all clean
all: bitmaps $(ROMNAME).sfc
clean: cleanBuildRes cleanRom cleanGfx

ROMNAME := game

# Convert graphics here (gfx2snes), e.g.:
bitmaps:
	@echo "convert gfx if needed"
```

## Core PVSnesLib API (most-used)

```c
#include <snes.h>

int main(void) {
    consoleInit();

    // Load a 4bpp tileset + palette into VRAM/CGRAM, set up a BG layer
    bgInitTileSet(0, &tiles, &palette, 0, tilesLen, palLen, BG_16COLORS, 0x4000);
    bgInitMapSet(0, &map, mapLen, SC_32x32, 0x0000);

    setMode(BG_MODE1, 0);     // pick a background mode
    bgSetEnable(0);
    setScreenOn();

    while (1) {
        // input
        pad0 = padsCurrent(0);          // bitmask: KEY_A, KEY_LEFT, KEY_START...
        if (pad0 & KEY_RIGHT) scrollX++;

        // sprites
        oamSet(0, x, y, 3, 0, 0, gfxOffset, palNum);
        oamSetVisible(0, OBJ_SHOW);

        bgSetScroll(0, scrollX, scrollY);

        WaitForVBlank();                 // sync to 60Hz (NTSC) / 50Hz (PAL); REQUIRED each frame
    }
    return 0;
}
```

Key calls: `consoleInit`, `setMode`/`setScreenOn`, `WaitForVBlank` (once per frame — never busy-loop), `padsCurrent`, `bgInitTileSet`/`bgInitMapSet`/`bgSetScroll`/`bgSetEnable`, `oamSet`/`oamSetEx`/`oamSetVisible`/`oamInitGfxSet`, `dmaCopyVram`/`dmaCopyCGram`, `consoleDrawText`/`consoleInitText`. Sound uses `spcBoot`, `spcSetBank`, `spcLoad`, `spcPlay` with SNESGSS/`.spc` banks.

## Graphics & data tools

Art is converted to SNES tile format at build time, not loaded as PNG at runtime:
- `gfx2snes` — PNG/BMP → `.pic` (tiles), `.pal` (palette), `.map` (tilemap). Mind bpp (`-gs8`, color count) and that source images use a SNES-legal palette.
- `smconv` — convert tracks/SFX for the SPC700 sound driver.
- Generated data is `#include`d or linked; reference it via the `extern` symbols the build emits.

## SNES hardware constraints — keep these in mind

- **VBlank is sacred:** all VRAM/CGRAM/OAM writes should happen during VBlank (or via DMA). Writing during active display corrupts graphics. Call `WaitForVBlank()` exactly once per game loop iteration.
- 65816 CPU ~3.58 MHz — budget cycles; prefer DMA over CPU copies for bulk transfers.
- Backgrounds: modes 0–7. Mode 1 (two 16-color BGs + one 4-color BG) is the common workhorse; Mode 7 is the affine/rotation layer.
- 128 hardware sprites (OAM), sizes 8×8…64×64, two sizes per scene; max 32 sprites / 34 tiles per scanline.
- Palettes: 256 CGRAM entries, 15-bit BGR color; sprites and BGs draw from sub-palettes (16 colors for 4bpp).
- ROM is mapped LoROM or HiROM — keep the Makefile/header mapping consistent with how ZSNES loads it.

## Running & testing

After `make` produces `game.sfc`:
```powershell
& "C:/games/zsnes/SUPERZSNES.exe" "C:/dev/snesgame2/game.sfc"
```
If `SUPERZSNES.exe` (a Unity frontend) ignores the ROM path argument, launch it and load the ROM through its UI. ZSNES is older and less accurate than bsnes/Mesen — if behavior looks off, suspect emulator quirks before SDK bugs, but ZSNES is the chosen target here so test against it. There is no automated test harness for ROMs; verify by running and observing (use the `verify`/`run` skills' spirit: build, launch, watch).

## Working style

- Default to C with PVSnesLib idioms; drop to ASM only for tight inner loops or hardware tricks.
- When build/link errors mention `wla`/`wlalink`/`816-tcc`, they're toolchain errors — check section/bank overflow, missing `extern`, or `.asm` section directives, not generic C advice.
- Keep per-frame work inside the `while(1)` loop bounded so a frame fits in VBlank budget.
- Paths are known (PVSnesLib `C:/tools/pvsneslib`, ZSNES `C:/games/zsnes/SUPERZSNES.exe`); `C:/tools/pvsneslib/snes-examples` and `vscode-template` are good references for Makefiles and working code.
