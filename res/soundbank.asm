;************************************************
; snesmod soundbank data                        *
; total size:      24126 bytes                  *
;************************************************

.include "hdr.asm"

.BANK 5
.SECTION "SOUNDBANK" ; need dedicated bank(s)

SOUNDBANK__:
.incbin "res/soundbank.bnk"
.ENDS
