.include "hdr.asm"

; --- Console font (text) ---
.section ".rodata1" superfree

tilfont:
.incbin "pvsneslibfont.pic"

palfont:
.incbin "pvsneslibfont.pal"

.ends

; --- Sprite graphics (generated from sprites.bmp by gfx4snes) ---
.section ".rosprite" superfree

.include "sprites_data.as"

.ends

; --- Sega Genesis enemy graphics (generated from enemy.bmp by gfx4snes) ---
.section ".roenemy" superfree

enemy_til:
.incbin "enemy.pic"
enemy_tilend:

enemy_pal:
.incbin "enemy.pal"
enemy_palend:

.ends

; --- Player bullet graphics (generated from bullet.bmp by gfx4snes) ---
.section ".robullet" superfree

bullet_til:
.incbin "bullet.pic"
bullet_tilend:

bullet_pal:
.incbin "bullet.pal"
bullet_palend:

.ends
