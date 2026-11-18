// SPDX-License-Identifier: AGPL-3.0-or-later
// Script = Retrans: the endings' (SEL's) 12 px dialogue drawing, which does
// not fit in SEL. src/st/cutscene_mod_rt.h does the same in the other
// overlays (it is the same code, with the line kept in the reserve).
//
// Where it lives: main.exe's free 8 KB at MOD_RT_EXT_ADDR (include/
// game_mod.h). Like rt_font.c, this code is one copy record of the RT pack
// (mods/sotn-ultimate/tools/text_packs.py) with the endings' RT copy after
// it (MOD_RT_EXT_COPY), so both are in RAM exactly when the RT pack's tag
// is set, which SEL checks before calling in. Built by build_rtfont.sh:
// linked at MOD_RT_EXT_ADDR, ModRtExt first, no data or BSS (the line is
// kept at MOD_RT_EXT_LINE, past the copy).
//
// ModRtExt(ch, start, lineX, vy):
// - ch < 0: SEL's ModPspScript is starting the RT copy: copy it to
//   MOD_RT_EXT_RUN (a script's jumps reach 0x801xxxxx only);
// - else: add byte ch to the line (a new line when start), draw the whole
//   line with ModRtText into the strip at DEMO_KEY_PTR and load its 12 rows
//   into the text texture at (lineX, vy).
#include <game.h>

#define EXT_STRIP ((u8*)0x801E8000) // DEMO_KEY_PTR: idle in cutscenes
#define EXT_ROW 96                  // 192 px, 4 bpp
#define EXT_MAX 80
#define EXT_LINE ((u8*)MOD_RT_EXT_LINE)
#define EXT_LEN (*(s32*)(MOD_RT_EXT_LINE + 84))

void ModRtExt(s32 ch, s32 start, s32 lineX, s32 vy) {
    RECT rect;
    u8* old;
    u8* src;
    u8* dst;
    s32 i;
    s32 n;

    if (ch < 0) {
        n = *(s32*)MOD_RT_EXT_COPY;
        src = (u8*)(MOD_RT_EXT_COPY + 4);
        dst = (u8*)MOD_RT_EXT_RUN;
        for (i = 0; i < n; i++) {
            dst[i] = src[i];
        }
        return;
    }
    if (start) {
        EXT_LEN = 0;
        for (i = 0; i < 84; i++) {
            EXT_LINE[i] = 0;
        }
    }
    if (EXT_LEN < EXT_MAX) {
        EXT_LINE[EXT_LEN++] = ch;
    }
    for (i = 0; i < EXT_ROW * 15; i++) {
        EXT_STRIP[i] = 0;
    }
    old = *(u8**)0x8013794C; // DRA menu.c D_8013794C, ModRtText's line
    *(u8**)0x8013794C = EXT_STRIP;
    if (((s32(*)(const u8*, s32))MOD_RT_FONT_ADDR)(EXT_LINE, EXT_ROW)) {
        rect.x = lineX;
        rect.y = vy;
        rect.w = EXT_ROW / 2;
        rect.h = 12;
        // LoadImage and DrawSync: main's (config/symbols.us.txt)
        ((int (*)(RECT*, u_long*))0x80012B24)(
            &rect, (u_long*)(EXT_STRIP + 2 * EXT_ROW));
        ((int (*)(int))0x8001290C)(0);
    }
    *(u8**)0x8013794C = old;
}
