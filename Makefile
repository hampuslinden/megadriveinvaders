ifeq ($(strip $(PVSNESLIB_HOME)),)
$(error "Please create an environment variable PVSNESLIB_HOME pointing at /c/tools/pvsneslib")
endif

# BEFORE including snes_rules:
# list every .it file (effects first, then any music) in AUDIOFILES so smconv
# builds the soundbank, and point SOUNDBANK at where to emit it.
AUDIOFILES := res/sfx.it
export SOUNDBANK := res/soundbank

include ${PVSNESLIB_HOME}/devkitsnes/snes_rules

# snes_rules' Windows lib-path math mangles the dir into a broken "C::\..."
# (double colon) under MSYS, so the standard library objects get dropped from
# the linkfile and the link fails. Point it straight at the forward-slash lib
# dir, which both `ls` and wlalink.exe accept.
LIBDIRSOBJSW := $(LIBDIRSOBJS)

.PHONY: bitmaps musics brrsound all

#---------------------------------------------------------------------------------
# ROMNAME is used in snes_rules file
export ROMNAME := snesgame2

# smconv flags: -s strip, -o output, -V verbose, -b 5 = place the bank in ROM bank 5
SMCONVFLAGS := -s -o $(SOUNDBANK) -V -b 5
musics: $(SOUNDBANK).obj

all: musics brrsound bitmaps $(ROMNAME).sfc

clean: cleanBuildRes cleanRom cleanGfx cleanAudio

#---------------------------------------------------------------------------------
# Convert the bundled console font (8x8 tiles) -> .pic + .pal
pvsneslibfont.pic: pvsneslibfont.png
	@echo convert font ... $(notdir $@)
	$(GFXCONV) -s 8 -o 16 -u 16 -p -e 0 -i $<

# Convert the 32x32 sprite sheet -> .pic + .pal (+ .inc / _data.as)
sprites.pic: sprites.bmp
	@echo convert sprite ... $(notdir $@)
	$(GFXCONV) -s 32 -o 16 -u 16 -t bmp -i $<

# Convert the 32x32 Sega Genesis enemy -> .pic + .pal
enemy.pic: enemy.bmp
	@echo convert enemy ... $(notdir $@)
	$(GFXCONV) -s 32 -o 16 -u 16 -t bmp -i $<

# Convert the 8x8 player bullet -> .pic + .pal
bullet.pic: bullet.bmp
	@echo convert bullet ... $(notdir $@)
	$(GFXCONV) -s 8 -o 16 -u 16 -t bmp -i $<

bitmaps: pvsneslibfont.pic sprites.pic enemy.pic bullet.pic

#---------------------------------------------------------------------------------
# Gun-fire effect: snesbrr-encode the synthesized WAV into a BRR sample.
# res/gunshot.wav is produced by tools/make_gunshot.js (Node) -- regenerate it
# with `node tools/make_gunshot.js` when tweaking the sound; the build itself
# only needs snesbrr so it has no Node dependency.
res/gunshot.brr: res/gunshot.wav
	@echo convert gunshot wav -> brr ... $(notdir $@)
	$(BRCONV) -e $< $@

brrsound: res/gunshot.brr
