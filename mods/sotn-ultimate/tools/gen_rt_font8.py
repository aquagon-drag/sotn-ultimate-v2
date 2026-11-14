#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Script = Retrans: the retranslation's 8 px proportional glyphs for DRA's
menu font (mods/sotn-ultimate/src/menu/rt_font8.c).

The font page of BIN/F_GAME.BIN and BIN/F_GAME2.BIN (file 0x30000: 128x128
pixels, 4 bits each, 16x16 tiles of 8x8; VRAM tpage 0x1E) has the US glyphs
in tiles 0x00-0x5F and, on the US disc, unused kana from 0x60. With the
builder's own patched Japanese disc (disks/jpre, as text_rt.py: DRA.BIN and
BIN/F_GAME.BIN, both checked by SHA-1), the patch's glyph of each US
character goes to tile 0x60 + its US code (text_rt.py rt8_table; a character
the patch has no glyph for keeps the US one), where ModRt8Char finds it
while the RT pack is applied. Default never draws those tiles.

Output: build/us/F_GAME.BIN, and build/us/F_GAME2.BIN in place (after
gen_mar_hud.py; make disk takes both over disks/us/BIN's). Without
disks/jpre: build/us/F_GAME.BIN is the US file and F_GAME2.BIN is left
alone, so nothing of the patch's font is on the disc (make_release.sh)."""
import hashlib
import os
import sys

import text_rt

ROOT = text_rt.ROOT
US = os.path.join(ROOT, "disks/us/BIN/F_GAME.BIN")
OUT = os.path.join(ROOT, "build/us/F_GAME.BIN")
OUT2 = os.path.join(ROOT, "build/us/F_GAME2.BIN")
PAGE = text_rt.FONT8_PAGE


def tile(page, t):
    """the 8 rows (4 bytes each) of tile t in a 0x2000-byte font page"""
    return [page[((t >> 4) * 8 + y) * 64 + (t & 15) * 4:][:4] for y in range(8)]


def put(buf, t, rows):
    for y, r in enumerate(rows):
        o = PAGE + ((t >> 4) * 8 + y) * 64 + (t & 15) * 4
        buf[o:o + 4] = r


def main():
    us = bytearray(open(US, "rb").read())
    if not text_rt.rt8_on():
        open(OUT, "wb").write(us)
        print("rt font8: no disks/jpre: F_GAME.BIN is the US file")
        return
    if not os.path.exists(text_rt.JP_FGAME):
        sys.exit("rt font8: %s is missing (the patched disc's BIN/F_GAME.BIN; "
                 "DRA.BIN is there)" % text_rt.JP_FGAME)
    jp = open(text_rt.JP_FGAME, "rb").read()
    h = hashlib.sha1(jp).hexdigest()
    if h != text_rt.JP_FGAME_SHA1:
        sys.exit("rt font8: %s is not the patched disc's file (SHA-1 %s, expected %s)"
                 % (text_rt.JP_FGAME, h, text_rt.JP_FGAME_SHA1))
    f2 = bytearray(open(OUT2, "rb").read())
    us_page = bytes(us[PAGE:PAGE + 0x2000])
    if bytes(f2[PAGE:PAGE + 0x2000]) != us_page:
        sys.exit("rt font8: F_GAME2.BIN's font page is not F_GAME.BIN's")
    jp_page = jp[PAGE:PAGE + 0x2000]
    tab = text_rt.rt8_table()
    for c, (t, _) in enumerate(tab):
        rows = tile(us_page, c) if t is None else tile(jp_page, t)
        for buf in (us, f2):
            put(buf, text_rt.RT8_TILE0 + c, rows)
    open(OUT, "wb").write(us)
    open(OUT2, "wb").write(f2)
    n = sum(1 for t, _ in tab if t is not None)
    print("rt font8: %d of %d tiles from the patched disc's font, from tile 0x%02X of "
          "F_GAME.BIN / F_GAME2.BIN" % (n, len(tab), text_rt.RT8_TILE0))


if __name__ == "__main__":
    main()
