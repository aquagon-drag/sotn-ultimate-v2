#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Script = Retrans: the retranslation font's drawing code
# (mods/sotn-ultimate/src/menu/rt_font.c) -> build/us/mod/rtfont/rtfont.bin,
# linked at MOD_RT_FONT_ADDR (include/game_mod.h) against the built DRA.
# The RT pack (text_packs.py) writes it there with the font's width table and
# glyphs, which come from the builder's patched disc, after it
# (g_ModRtW / g_ModRtGlyph, placed by this linker script). Nothing here is
# from the patch; the code is built whether or not the builder has it.
# Run after DRA's final link (its addresses are rechecked by build_disc.sh).
set -euo pipefail
cd "$(dirname "$0")/../../.."
OUT=build/us/mod/rtfont
mkdir -p "$OUT"
H=mods/sotn-ultimate/include/game_mod.h
ADDR=$(grep -oE "#define MOD_RT_FONT_ADDR 0x[0-9A-Fa-f]+" $H | awk '{print $3}')
END=$(grep -oE "#define MOD_RT_FONT_END 0x[0-9A-Fa-f]+" $H | awk '{print $3}')
NG=$(grep -oE "#define MOD_RT_GLYPHS [0-9]+" $H | awk '{print $3}')
ADDR8=$(grep -oE "#define MOD_RT8_ADDR 0x[0-9A-Fa-f]+" $H | awk '{print $3}')
NC8=$(grep -oE "#define MOD_RT8_CHARS 0x[0-9A-Fa-f]+" $H | awk '{print $3}')
nm_of() {
    mipsel-linux-gnu-nm "$1" | awk -v s="$2" '$3==s{print "0x" $1}'
}
# DRA calls ModRtText at the address config/undefined_syms.us.txt gives it
sym=$(grep -oE "^ModRtText = 0x[0-9A-Fa-f]+;" config/undefined_syms.us.txt | grep -oE "0x[0-9A-Fa-f]+")
if [ $((sym)) -ne $((ADDR)) ]; then
    echo "FAIL rtfont: config/undefined_syms.us.txt ModRtText $sym, MOD_RT_FONT_ADDR $ADDR"; exit 1
fi
# the room: from DRA's BSS end to the player file at MOD_RT_FONT_END
bss_end=$(nm_of build/us/dra.elf dra_BSS_END)
if [ $((bss_end)) -gt $((ADDR)) ]; then
    echo "FAIL rtfont: DRA's BSS ends at $bss_end, past MOD_RT_FONT_ADDR $ADDR"; exit 1
fi
if [ $((END)) -ne $((0x8013C000)) ]; then
    echo "FAIL rtfont: MOD_RT_FONT_END is not the player file's address"; exit 1
fi

cc() { # cc <source> <object>
VERSION=us mipsel-linux-gnu-cpp -Iinclude -Iinclude/psxsdk -Isrc/dra -lang-c \
    -undef -Wall -fno-builtin -Dmips -D__GNUC__=2 -D__OPTIMIZE__ -D__mips__ -D__mips \
    -Dpsx -D__psx__ -D__psx -D_PSYQ -D__EXTENSIONS__ -D_MIPSEL -D_LANGUAGE_C \
    -DLANGUAGE_C -DNO_LOGS -DHACKS -DUSE_INCLUDE_ASM -D_internal_version_us -DSOTN_STR \
    "$1" | tools/sotn_str/target/release/sotn_str process |
    iconv --from-code=UTF-8 --to-code=Shift-JIS |
    bin/cc1-psx-26 -G0 -w -funsigned-char -fpeephole -ffunction-cse \
        -fpcc-struct-return -fcommon -fverbose-asm -msoft-float -g -quiet \
        -mcpu=3000 -fgnu-linker -mgas -gcoff -O2 |
    python3 tools/maspsx/maspsx.py --expand-div --aspsx-version=2.34 |
    mipsel-linux-gnu-as -Iinclude -march=r3000 -mtune=r3000 -no-pad-sections \
        -O1 -G0 -o "$2"
}
cc mods/sotn-ultimate/src/menu/rt_font.c "$OUT/rtfont.o"
# the 8 px font's code (rt_font8.c), at MOD_RT8_ADDR in the same room
cc mods/sotn-ultimate/src/menu/rt_font8.c "$OUT/rtfont8.o"

a=$(nm_of build/us/dra.elf D_8013794C)
if [ -z "$a" ]; then
    echo "FAIL rtfont: D_8013794C not in dra.elf"; exit 1
fi
echo "D_8013794C = $a;" > "$OUT/syms.txt"
a=$(nm_of build/us/dra.elf MenuDrawChar)
if [ -z "$a" ]; then
    echo "FAIL rtfont: MenuDrawChar not in dra.elf"; exit 1
fi
echo "MenuDrawChar = $a;" >> "$OUT/syms.txt"
cat > "$OUT/rtfont.ld" <<EOF
SECTIONS {
    . = $ADDR;
    .text : { *rtfont.o(.text) }
    .rodata : { *rtfont.o(.rodata*) *rtfont.o(.rdata) }
    .data : { *(.data) *(.sdata) }
    .bss : { *(.bss) *(.sbss) *(COMMON) }
    . = ALIGN(4);
    g_ModRtW = .;
    g_ModRtGlyph = g_ModRtW + $NG;
    g_ModRtEnd = g_ModRtGlyph + $NG * 12;
    . = $ADDR8;
    .text8 : { *rtfont8.o(.text) *rtfont8.o(.rodata*) *rtfont8.o(.rdata) }
    g_ModRt8End = .;
    g_ModRtW8 = $END - $NC8;
    /DISCARD/ : { *(.reginfo) *(.pdr) *(.mdebug*) *(.comment) *(.gnu*) *(.MIPS*) }
}
EOF
mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map "$OUT/rtfont.map" \
    -T "$OUT/rtfont.ld" -T "$OUT/syms.txt" -o "$OUT/rtfont.elf" "$OUT/rtfont.o" "$OUT/rtfont8.o"
for s in .data .bss; do
    sz=$(mipsel-linux-gnu-objdump -h "$OUT/rtfont.elf" | awk -v s=$s '$2==s{print $3}')
    if [ -n "$sz" ] && [ $((16#$sz)) -ne 0 ]; then
        echo "FAIL rtfont: $s is not empty (the pack writes code and constants only)"; exit 1
    fi
done
if [ "$(nm_of "$OUT/rtfont.elf" ModRtText)" != "$(printf 0x%08x $ADDR)" ]; then
    echo "FAIL rtfont: ModRtText is not first (at $(nm_of "$OUT/rtfont.elf" ModRtText))"; exit 1
fi
endr=$(nm_of "$OUT/rtfont.elf" g_ModRtEnd)
if [ $((endr)) -gt $((ADDR8)) ]; then
    echo "FAIL rtfont: code + font end at $endr, past MOD_RT8_ADDR $ADDR8"; exit 1
fi
# the 8 px font's code: ModRt8Char at MOD_RT8_ADDR (DRA calls it there:
# config/undefined_syms.us.txt), ending before its width table
sym8=$(grep -oE "^ModRt8Char = 0x[0-9A-Fa-f]+;" config/undefined_syms.us.txt | grep -oE "0x[0-9A-Fa-f]+")
if [ $((sym8)) -ne $((ADDR8)) ] || [ "$(nm_of "$OUT/rtfont.elf" ModRt8Char)" != "$(printf 0x%08x $ADDR8)" ]; then
    echo "FAIL rtfont: ModRt8Char is not at MOD_RT8_ADDR $ADDR8 (undefined_syms $sym8)"; exit 1
fi
end8=$(nm_of "$OUT/rtfont.elf" g_ModRt8End)
w8=$(nm_of "$OUT/rtfont.elf" g_ModRtW8)
if [ $((end8)) -gt $((w8)) ]; then
    echo "FAIL rtfont: the 8 px font's code ends at $end8, past its width table $w8"; exit 1
fi
mipsel-linux-gnu-objcopy -O binary -j .text8 "$OUT/rtfont.elf" "$OUT/rtfont8.bin"
mipsel-linux-gnu-objcopy -O binary -j .text -j .rodata "$OUT/rtfont.elf" "$OUT/rtfont.bin"
code=$(stat -c %s "$OUT/rtfont.bin")
w=$(nm_of "$OUT/rtfont.elf" g_ModRtW)
if [ $((ADDR + code)) -gt $((w)) ] || [ $((w - ADDR - code)) -ge 4 ]; then
    echo "FAIL rtfont: the code ($code B) does not end where g_ModRtW starts"; exit 1
fi
echo "rtfont: code $code B at $ADDR, font tables $w-$endr; 8 px font: code $(stat -c %s "$OUT/rtfont8.bin") B at $ADDR8, $((w8 - end8)) B left before its widths at $w8"
