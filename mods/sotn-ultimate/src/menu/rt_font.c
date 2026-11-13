// SPDX-License-Identifier: AGPL-3.0-or-later
// Script = Retrans: the fan retranslation's 12 px proportional font for
// everything DRA draws with the BIOS font (src/dra/menu.c func_800F99B8:
// descriptions and help lines on the info bar, relic and spell names, the
// save point's messages).
//
// Where it lives: the 2,400 B between DRA's BSS end and 0x8013C000
// (include/game_mod.h MOD_RT_FONT_ADDR; DRA.BIN's first sound bank, sent to
// the SPU once at boot, then dead; the player files load from 0x8013C000).
// Nothing is on the disc for it but the retranslation pack: this code, the
// patch's width table and its glyphs are one copy record of the RT pack
// (SD/TXT_RT.BIN, mods/sotn-ultimate/tools/text_packs.py), so they are in
// RAM exactly when g_ModDub.textPack says the RT pack is applied (the tag is
// written after its last chunk), which is what DRA checks before calling
// in. The glyphs and widths come from the builder's own patched disc
// (disks/jpre/DRA.BIN, text_rt.py rt_font); this repository has neither.
// Built by mods/sotn-ultimate/tools/build_rtfont.sh: linked at
// MOD_RT_FONT_ADDR, ModRtText first; g_ModRtW / g_ModRtGlyph follow the
// code (the linker script places them).
//
// The strings keep the US BIOS renderer's encoding (ASCII letters and space,
// anything else a Shift-JIS pair; a "”" pair is followed by a second one,
// which is skipped): stage overlays and the Librarian draw the same strings
// with their own BIOS-font code. A string with a character the font lacks
// is left to the BIOS font (ModRtText returns 0 before drawing anything).
//
// Drawing, as the patch's VWF12_DrawChar (JP DRA 0x801068B4) does: each
// glyph is 8x12, 1 bit per pixel (bit 7 = left), ORed into the 4 bpp line at
// the pen's pixel; its body is colour 7, its shadow (one pixel right, below,
// and right-below) colour 1, so a body over a shadow stays a body; glyph
// row 0 is the line's row 2 (the patch uploads its cells 2 rows down); the
// pen advances by the glyph's width. Columns past the line are cut, as the
// BIOS font's are. tools/text_rt.py rt_draw mirrors this pixel for pixel
// (the fit report and the preview use it).
#include <game.h>

#define RT_ROW0 2   // the line's row of glyph row 0
#define RT_BODY 7   // CLUT 0x1A1: (28,28,28), the patch's body colour
#define RT_SHADOW 1 // CLUT 0x1A1: (8,8,8)

// (the linker script: right after this code, from the retranslation pack)
extern const u8 g_ModRtW[];
extern const u8 g_ModRtGlyph[][12];
// DRA's (menu.c, static): the line func_800F99B8 has cleared for the string
extern u8* D_8013794C;

static s32 ModRtNext(const u8** ps);

// str: the BIOS renderer's string, drawn into its cleared 16-row texture
// line at D_8013794C, w bytes (2 pixels each) a row. 1: drawn; 0: not (a
// character the font lacks: the BIOS font draws it)
s32 ModRtText(const u8* str, s32 w) {
    const u8* s;
    u8* d;
    s32 g, pen, r, x, end;
    u32 m, prev, sh, bit;

    s = str;
    while ((g = ModRtNext(&s)) >= 0) {
    }
    if (g != -1) {
        return 0;
    }
    end = w * 2;
    pen = 0;
    s = str;
    while ((g = ModRtNext(&s)) >= 0) {
        prev = 0;
        d = D_8013794C + RT_ROW0 * w;
        for (r = 0; r < 13; r++, d += w) {
            // bits 15..7: the glyph's columns 0..8 (8: its shadow only)
            m = r < 12 ? g_ModRtGlyph[g][r] << 8 : 0;
            sh = ((m | prev) >> 1) | prev;
            prev = m;
            for (bit = 0x8000, x = pen; bit > 0x40; bit >>= 1, x++) {
                if (x >= end) {
                    break;
                }
                if (m & bit) {
                    d[x >> 1] |= RT_BODY << ((x & 1) * 4);
                } else if (sh & bit) {
                    d[x >> 1] |= RT_SHADOW << ((x & 1) * 4);
                }
            }
        }
        pen += g_ModRtW[g];
    }
    return 1;
}

// Shift-JIS 0x81xx -> glyph (text_rt.py reads this table): the patch's
// punctuation, the brackets as its parentheses
static const u8 g_ModRtSjis81[][2] = {
    {0x40, 0},  {0x43, 5},  {0x44, 17}, {0x46, 14}, {0x48, 15}, {0x49, 1},
    {0x5F, 85}, {0x65, 6},  {0x66, 6},  {0x68, 2},  {0x69, 3},  {0x6A, 4},
    {0x6D, 3},  {0x6E, 4},  {0x7B, 80}, {0x7C, 16}, {0x93, 87}, {0xA8, 84},
    {0xAA, 83}, {0xAB, 82},
};

// the glyph of the next character at *ps (moved past it): -1 at the end,
// -2 when the font has none
static s32 ModRtNext(const u8** ps) {
    const u8* s = *ps;
    u32 c = *s++;
    s32 g;
    s32 i;

    if (c == 0) {
        return -1;
    }
    if (c == ' ') {
        g = 0;
    } else if (c - 'A' < 26) {
        g = c - 'A' + 28;
    } else if (c - 'a' < 26) {
        g = c - 'a' + 54;
    } else {
        c = (c << 8) | *s++;
        if (c == 0x8168) {
            s += 2;
        }
        if (c - 0x824F < 10) {
            g = c - 0x824F + 18;
        } else if (c - 0x8260 < 26) {
            g = c - 0x8260 + 28;
        } else if (c - 0x8281 < 26) {
            g = c - 0x8281 + 54;
        } else {
            g = -2;
            for (i = 0; i < LEN(g_ModRtSjis81); i++) {
                if (c == 0x8100 + g_ModRtSjis81[i][0]) {
                    g = g_ModRtSjis81[i][1];
                }
            }
        }
    }
    *ps = s;
    return g;
}
