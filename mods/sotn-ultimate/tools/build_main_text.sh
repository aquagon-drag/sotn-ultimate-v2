#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SOTN Ultimate (step 6b): the stages' shared text code
# (mods/sotn-ultimate/src/menu/main_text.c) -> the boot executable's debug
# font arrays (src/main/psxsdk/libgpu/font.c includes the two headers this
# writes: kanjiclut, 0x200 bytes, and D_8002BA18, 0x800, at
# MOD_MAIN_TEXT_ADDR). Fixed addresses only (g_api, the graphics globals, the
# RT font room): run it before main.exe's compile (build_disc.sh does).
set -euo pipefail
cd "$(dirname "$0")/../../.."
OUT=build/us/mod/main_text
mkdir -p "$OUT"
ADDR=$(grep -hoE "#define MOD_MAIN_TEXT_ADDR 0x[0-9A-Fa-f]+" mods/sotn-ultimate/include/game_mod.h | awk '{print $3}')
LEN=$(grep -hoE "#define MOD_MAIN_TEXT_LEN 0x[0-9A-Fa-f]+" mods/sotn-ultimate/include/game_mod.h | awk '{print $3}')

VERSION=us mipsel-linux-gnu-cpp -Iinclude -Iinclude/psxsdk -Isrc/dra -lang-c \
    -undef -Wall -fno-builtin -Dmips -D__GNUC__=2 -D__OPTIMIZE__ -D__mips__ -D__mips \
    -Dpsx -D__psx__ -D__psx -D_PSYQ -D__EXTENSIONS__ -D_MIPSEL -D_LANGUAGE_C \
    -DLANGUAGE_C -DNO_LOGS -DHACKS -DUSE_INCLUDE_ASM -D_internal_version_us -DSOTN_STR \
    mods/sotn-ultimate/src/menu/main_text.c | tools/sotn_str/target/release/sotn_str process |
    iconv --from-code=UTF-8 --to-code=Shift-JIS |
    bin/cc1-psx-26 -G0 -w -funsigned-char -fpeephole -ffunction-cse \
        -fpcc-struct-return -fcommon -fverbose-asm -msoft-float -g -quiet \
        -mcpu=3000 -fgnu-linker -mgas -gcoff -O2 |
    python3 tools/maspsx/maspsx.py --expand-div --aspsx-version=2.34 |
    mipsel-linux-gnu-as -Iinclude -march=r3000 -mtune=r3000 -no-pad-sections \
        -O1 -G0 -o "$OUT/main_text.o"

: > "$OUT/syms.txt"
for s in g_PrimBuf; do
    a=$(awk -v s="$s" '$1==s{sub(/;/,"",$3); sub(/^0x/,"",$3); print $3}' config/symbols.us.txt)
    if [ -z "$a" ] || [ "$(echo "$a" | wc -l)" != 1 ]; then
        echo "FAIL main_text: $s not in config/symbols.us.txt (or not once)"; exit 1
    fi
    echo "$s = 0x$a;" >> "$OUT/syms.txt"
done
cat > "$OUT/main_text.ld" <<LDEOF
SECTIONS {
    . = $ADDR;
    .text : { *(.text) }
    .rodata : { *(.rodata*) *(.rdata) }
    .data : { *(.data) *(.sdata) }
    .bss : { *(.bss) *(.sbss) *(COMMON) }
    /DISCARD/ : { *(.reginfo) *(.pdr) *(.mdebug*) *(.comment) *(.gnu*) *(.MIPS*) }
}
LDEOF
mipsel-linux-gnu-ld -nostdlib --no-check-sections -Map "$OUT/main_text.map" \
    -T "$OUT/main_text.ld" -T config/undefined_syms.us.txt -T "$OUT/syms.txt" \
    -o "$OUT/main_text.elf" "$OUT/main_text.o"
sz=$(mipsel-linux-gnu-objdump -h "$OUT/main_text.elf" | awk '$2==".bss"{print $3}')
if [ -n "$sz" ] && [ $((16#$sz)) -ne 0 ]; then
    echo "FAIL main_text: .bss is not empty"; exit 1
fi
mipsel-linux-gnu-objcopy -O binary -j .text -j .rodata -j .data "$OUT/main_text.elf" "$OUT/main_text.bin"
python3 - "$OUT" "$ADDR" "$LEN" <<'PYEOF'
import struct, subprocess, sys
out, addr, ln = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
b = open(out + "/main_text.bin", "rb").read()
if len(b) > ln:
    sys.exit("FAIL main_text: %d bytes, %d past MOD_MAIN_TEXT_LEN" % (len(b), len(b) - ln))
syms = {}
for l in subprocess.run(["mipsel-linux-gnu-nm", out + "/main_text.elf"], capture_output=True,
                        text=True, check=True).stdout.splitlines():
    p = l.split()
    if len(p) == 3:
        syms[p[2]] = int(p[0], 16)
want = [syms[n] for n in ("ModTxtBlitChar", "ModTxtRelic", "ModTxtBox", "ModTxtCorner")]
if list(struct.unpack_from("<4I", b)) != want:
    sys.exit("FAIL main_text: the entry table is not first")
b = b + bytes(ln - len(b))
open(out + "/kanjiclut.h", "w").write(
    "".join("0x%04X,\n" % v for v in struct.unpack_from("<256H", b, 0)))
open(out + "/D_8002BA18.h", "w").write("".join("0x%02X,\n" % v for v in b[0x200:]))
print("main_text: %d bytes at 0x%08X, %d free (the boot executable's debug font)" % (
    len(b.rstrip(b"\0")), addr, ln - len(b.rstrip(b"\0"))))
PYEOF
