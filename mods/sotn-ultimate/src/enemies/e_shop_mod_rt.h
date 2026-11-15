// SPDX-License-Identifier: AGPL-3.0-or-later
// SOTN Ultimate: included by src/st/lib/e_shop.c (at file scope, in place)
// Script = Retrans in the Librarian's shop (step 6b). The RT pack puts the
// retranslation's fonts in DRA's RT font room (game_mod.h MOD_RT_FONT_ADDR),
// so they are there exactly when g_ModDub.textPack is the RT pack's tag:
//  - func_us_801B1064 (the 8x8 names: enemy list, tactics, sound test)
//    draws the 8 px font's tiles (MOD_RT8_TILE0..) with their advances (the
//    room's last MOD_RT8_CHARS bytes), as DRA's ModRt8Char;
//  - func_us_801B0C40 (the BIOS-font lines: descriptions) draws each line
//    with ModRtText, pointed at the Librarian's own line;
//  - the Librarian's own text: mod_lib_rt.h, made before the compile by
//    mods/sotn-ultimate/tools/text_packs.py --header (gitignored: the
//    retranslation's bestiary descriptions and menu words; the sound test
//    titles are the title screen's Sound Mode ones).
#include "../../../../src/st/lib/mod_lib_rt.h"

#define MOD_LIB_RT()                                                           \
    (MOD_LIB_RT_ON &&                                                          \
     *(u8*)&MOD_DUB_STATE->textPack == MOD_TEXT_PACK_RT)
#define MOD_LIB_RT8_W ((const u8*)(MOD_RT_FONT_END - MOD_RT8_CHARS))
// menu.c's line pointer (static there, at a fixed address: ModRtText draws
// into the line it points at)
#define MOD_LIB_RT_LINE (*(u8**)0x8013794C)

// str's lines ("@" or a byte < 8 ends one, 0 the string) into pix (two lines
// of 16 rows, size bytes a row), each sent to VRAM at x, y + 16 * line as
// func_us_801B0C40 does. 1: drawn; 0: the font lacks a character of a line
// (ModRtText draws none of that line: the BIOS font draws the string again)
static s32 ModLibRtText(u8* pix, const char* str, s32 x, s32 y, s32 size) {
    u8 line[64];
    const u8* s;
    u8* old;
    u8* row;
    s32 i, n, ok;

    old = MOD_LIB_RT_LINE;
    ok = 1;
    for (i = 0; i < size * 32; i++) {
        pix[i] = 0;
    }
    s = (const u8*)str;
    for (i = 0; ok && i < 2; i++) {
        for (n = 0; *s >= 8 && *s != '@' && n < LEN(line) - 3;) {
            if (*s >= 0x80) {
                line[n++] = *s++;
            }
            line[n++] = *s++;
        }
        line[n] = 0;
        row = &pix[i * 16 * size];
        MOD_LIB_RT_LINE = row;
        ok = ((s32(*)(const u8*, s32))MOD_RT_FONT_ADDR)(line, size);
        if (ok) {
            LoadTPage((u_long*)row, 0, 0, x, y + i * 16, size * 2, 0x10);
        }
        if (!*s) {
            break;
        }
        s++;
    }
    MOD_LIB_RT_LINE = old;
    return ok;
}
