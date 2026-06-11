ifeq ($(strip $(PVSNESLIB_HOME)),)
$(error "Please create an environment variable PVSNESLIB_HOME pointing at /c/tools/pvsneslib")
endif

include ${PVSNESLIB_HOME}/devkitsnes/snes_rules

.PHONY: bitmaps all

#---------------------------------------------------------------------------------
# ROMNAME is used in snes_rules file
export ROMNAME := snesgame2

all: bitmaps $(ROMNAME).sfc

clean: cleanBuildRes cleanRom cleanGfx

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
