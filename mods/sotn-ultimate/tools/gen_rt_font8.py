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
CLUTS = 0x40000  # 256 CLUTs of 16 colours (VRAM CLUT 0x100 + n)
FLAT_CLUTS = (0x5D, 0x5E)


def tile(page, t):
    """the 8 rows (4 bytes each) of tile t in a 0x2000-byte font page"""
    return [page[((t >> 4) * 8 + y) * 64 + (t & 15) * 4:][:4] for y in range(8)]


def put(buf, t, rows):
    for y, r in enumerate(rows):
        o = PAGE + ((t >> 4) * 8 + y) * 64 + (t & 15) * 4
        buf[o:o + 4] = r


def main():
    us = bytearray(open(US, "rb").read())
    us_page = bytes(us[PAGE:PAGE + 0x2000])
    # the US "・" also at US_DOT_TILE (game_mod.h MOD_US_DOT_TILE: the
    # System screen's locked rows use it in every build)
    put(us, text_rt.US_DOT_TILE, tile(us_page, 0x65))
    if not text_rt.rt8_on():
        if os.path.exists(OUT2):
            f2 = bytearray(open(OUT2, "rb").read())
            put(f2, text_rt.US_DOT_TILE, tile(us_page, 0x65))
            open(OUT2, "wb").write(f2)
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
    if bytes(f2[PAGE:PAGE + 0x2000]) != us_page:
        sys.exit("rt font8: F_GAME2.BIN's font page is not F_GAME.BIN's")
    put(f2, text_rt.US_DOT_TILE, tile(us_page, 0x65))
    jp_page = jp[PAGE:PAGE + 0x2000]
    tab = text_rt.rt8_table()
    for c, (t, _) in enumerate(tab):
        rows = tile(us_page, c) if t is None else tile(jp_page, t)
        for buf in (us, f2):
            put(buf, text_rt.RT8_TILE0 + c, rows)
    # the element symbols: the patch's 12 px glyphs with ModRtText's shadow
    # (right and below), the 8 rows with the most body pixels
    widths, glyphs = text_rt.rt_font()
    for k, code in enumerate(text_rt.RT_ICON_CODES):
        g = glyphs[12 * (code - 0x20):][:12]
        img, prev = [], 0
        for r in range(13):
            m = g[r] << 8 if r < 12 else 0
            sh = ((m | prev) >> 1) | prev
            prev = m
            img.append([6 if m & (0x8000 >> x) else 1 if sh & (0x8000 >> x) else 0 for x in range(8)])
        s = max(range(6), key=lambda s: (sum(v == 6 for row in img[s:s + 8] for v in row),
                                         sum(v == 1 for row in img[s:s + 8] for v in row)))
        rows = [bytes(row[2 * i] | row[2 * i + 1] << 4 for i in range(4)) for row in img[s:s + 8]]
        for buf in (us, f2):
            put(buf, text_rt.RT_ICON_TILE0 + k, rows)
    # the patch's glyphs have a shadow (colour 1; the body is colour 6, as
    # the US glyphs). The menu's one-colour CLUTs for dimmed and marked text
    # (menu.c MenuDrawImg: 0x15D red, 0x15E black = the files' CLUTs 0x5D /
    # 0x5E) would paint it like the body, a blot: their colour 1 becomes
    # transparent (the US glyphs have no colour 1)
    for buf in (us, f2):
        for clut in FLAT_CLUTS:
            o = CLUTS + clut * 32 + 2
            assert buf[o:o + 2] == buf[o + 2:o + 4], "CLUT 0x%X is not one colour" % clut
            buf[o:o + 2] = b"\0\0"
    open(OUT, "wb").write(us)
    open(OUT2, "wb").write(f2)
    n = sum(1 for t, _ in tab if t is not None)
    print("rt font8: %d of %d tiles from the patched disc's font, from tile 0x%02X of "
          "F_GAME.BIN / F_GAME2.BIN" % (n, len(tab), text_rt.RT8_TILE0))


if __name__ == "__main__":
    main()
