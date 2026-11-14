// SPDX-License-Identifier: AGPL-3.0-or-later
// Script = Retrans: the fan retranslation's 8 px proportional font for
// everything DRA draws with its 8x8 menu font (src/dra/menu.c MenuDrawChar /
// MenuDrawStr: item, equipment and accessory names, menu words, numbers).
//
// The glyphs: with the builder's own patched disc (disks/jpre), the build
// puts the patch's 8x8 glyphs in the font page's tiles 0x60-0xBF, in the US
// character order (mods/sotn-ultimate/tools/gen_rt_font8.py: F_GAME.BIN and
// F_GAME2.BIN; the US disc has unused kana there), so the tile of a US
// character ch < 0x60 is ch + 0x60. Nothing of that font is in this
// repository, and a build without disks/jpre keeps the US files.
//
// The code: DRA's MenuDrawChar calls ModRt8Char while the RT pack is applied
// (g_ModDub.textPack's tag, as func_800F99B8 does for the 12 px font). This
// file and the patch's advance of each US character (g_ModRtW8, from
// disks/jpre/DRA.BIN) are in the RT font's room, written by the RT pack
// with rt_font.c (include/game_mod.h MOD_RT8_ADDR; build_rtfont.sh links
// both). It draws the tile through MenuDrawChar itself (bit 8 of ch says the
// tile is final) and returns the advance, which MenuDrawStr adds to its pen.
#include <game.h>

// (the linker script: the room's last MOD_RT8_CHARS bytes)
extern const u8 g_ModRtW8[];
s32 MenuDrawChar(u32 ch, s32 x, s32 y, MenuContext* ctx);

s32 ModRt8Char(u32 ch, s32 x, s32 y, MenuContext* ctx) {
    s32 w = 8;

    if (ch < MOD_RT8_CHARS) {
        w = g_ModRtW8[ch];
        ch += MOD_RT8_TILE0;
    }
    MenuDrawChar(ch | MOD_RT8_FINAL, x, y, ctx);
    return w;
}
