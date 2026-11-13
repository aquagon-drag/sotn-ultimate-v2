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

VERSION=us mipsel-linux-gnu-cpp -Iinclude -Iinclude/psxsdk -Isrc/dra -lang-c \
    -undef -Wall -fno-builtin -Dmips -D__GNUC__=2 -D__OPTIMIZE__ -D__mips__ -D__mips \
    -Dpsx -D__psx__ -D__psx -D_PSYQ -D__EXTENSIONS__ -D_MIPSEL -D_LANGUAGE_C \
    -DLANGUAGE_C -DNO_LOGS -DHACKS -DUSE_INCLUDE_ASM -D_internal_version_us -DSOTN_STR \
    mods/sotn-ultimate/src/menu/rt_font.c | tools/sotn_str/target/release/sotn_str process |
    iconv --from-code=UTF-8 --to-code=Shift-JIS |
    bin/cc1-psx-26 -G0 -w -funsigned-char -fpeephole -ffunction-cse \
        -fpcc-struct-return -fcommon -fverbose-asm -msoft-float -g -quiet \
        -mcpu=3000 -fgnu-linker -mgas -gcoff -O2 |
    python3 tools/maspsx/maspsx.py --expand-div --aspsx-version=2.34 |
    mipsel-linux-gnu-as -Iinclude -march=r3000 -mtune=r3000 -no-pad-sections \
        -O1 -G0 -o "$OUT/rtfont.o"

a=$(nm_of build/us/dra.elf D_8013794C)
if [ -z "$a" ]; then
    echo "FAIL rtfont: D_8013794C not in dra.elf"; exit 1
fi
echo "D_8013794C = $a;" > "$OUT/syms.txt"
cat > "$OUT/rtfont.ld" <<EOF
SECTIONS {
    . = $ADDR;
    .text : { *(.text) }
    .rodata : { *(.rodata*) *(.rdata) }
    .data : { *(.data) *(.sdata) }
    .bss : { *(.bss) *(.sbss) *(COMMON) }
    . = ALIGN(4);
    g_ModRtW = .;
    g_ModRtGlyph = g_ModRtW + $NG;
    g_ModRtEnd = g_ModRtGlyph + $NG * 12;
    /DISCARD/ : { *(.reginfo) *(.pdr) *(.mdebug*) *(.comment) *(.gnu*) *(.MIPS*) }
}
EOF
mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map "$OUT/rtfont.map" \
    -T "$OUT/rtfont.ld" -T "$OUT/syms.txt" -o "$OUT/rtfont.elf" "$OUT/rtfont.o"
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
if [ $((endr)) -gt $((END)) ]; then
    echo "FAIL rtfont: code + font end at $endr, past $END"; exit 1
fi
mipsel-linux-gnu-objcopy -O binary -j .text -j .rodata "$OUT/rtfont.elf" "$OUT/rtfont.bin"
code=$(stat -c %s "$OUT/rtfont.bin")
w=$(nm_of "$OUT/rtfont.elf" g_ModRtW)
if [ $((ADDR + code)) -gt $((w)) ] || [ $((w - ADDR - code)) -ge 4 ]; then
    echo "FAIL rtfont: the code ($code B) does not end where g_ModRtW starts"; exit 1
fi
echo "rtfont: code $code B at $ADDR, font tables $w-$endr, $((END - endr)) B left before $END"
