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
// ModRtExt(op, a):
// - op >= 0: byte op of the dialogue being typed, a = SEL's g_Dialogue
//   (src/st/cutscene_mod_rt.h ModRtCutChar's work): add it to the line (a
//   new line at nextLineX), draw the whole line with ModRtText into the
//   strip at DEMO_KEY_PTR, load its 12 rows into the text texture;
// - MOD_RT_EXT_SCRIPT: SEL's ModPspScript is starting the RT copy: copy it
//   to MOD_RT_EXT_RUN (a script's jumps reach 0x801xxxxx only);
// - MOD_RT_EXT_NAME: a = the actor name, b = its first sprite, as SEL's
//   DrawCutsceneActorName (src/st/cutscene_actor_name.h) just made them in
//   the US 8x8 font: tiles and x of the RT 8 px font instead (as its
//   MOD_RT_CUTSCENE branch).
#include <game.h>
#include <cutscene.h>

#define EXT_STRIP ((u8*)0x801E8000) // DEMO_KEY_PTR: idle in cutscenes
#define EXT_ROW 96                  // 192 px, 4 bpp
#define EXT_MAX 80
#define EXT_VY 0x180 // SEL's text texture top
#define EXT_LINE ((u8*)MOD_RT_EXT_LINE)
#define EXT_LEN (*(s32*)(MOD_RT_EXT_LINE + 84))

void ModRtExt(s32 op, void* a, void* b) {
    Dialogue* dlg;
    Primitive* prim;
    const u8* name;
    const u8* rtW;
    RECT rect;
    u8* old;
    u8* src;
    u8* dst;
    s32 i;
    s32 n;
    s32 x;
    u8 ch;

    if (op == MOD_RT_EXT_SCRIPT) {
        n = *(s32*)MOD_RT_EXT_COPY;
        src = (u8*)(MOD_RT_EXT_COPY + 4);
        dst = (u8*)MOD_RT_EXT_RUN;
        for (i = 0; i < n; i++) {
            dst[i] = src[i];
        }
        return;
    }
    if (op == MOD_RT_EXT_NAME) {
        name = a;
        rtW = (const u8*)(MOD_RT_FONT_END - MOD_RT8_CHARS);
        x = 0x38;
        for (prim = b; prim != NULL;) {
            ch = *name++;
            if (ch >= MOD_RT8_CHARS) { // (the US glyph, as the C branch)
                prim->x0 = x;
                prim = prim->next;
                x += FONT_GAP;
                continue;
            }
            if (ch != CH(' ')) {
                prim->u0 = ((ch + MOD_RT8_TILE0) & 0x0F) * FONT_W;
                prim->v0 = ((ch + MOD_RT8_TILE0) & 0xF0) / (FONT_H / 4);
                prim->x0 = x;
                prim = prim->next;
            }
            x += rtW[ch];
        }
        return;
    }
    dlg = a;
    if (dlg->nextCharX == dlg->nextLineX) {
        EXT_LEN = 0;
        for (i = 0; i < 84; i++) {
            EXT_LINE[i] = 0;
        }
    }
    dlg->nextCharX++;
    if (EXT_LEN < EXT_MAX) {
        EXT_LINE[EXT_LEN++] = op;
    }
    for (i = 0; i < EXT_ROW * 15; i++) {
        EXT_STRIP[i] = 0;
    }
    old = *(u8**)0x8013794C; // DRA menu.c D_8013794C, ModRtText's line
    *(u8**)0x8013794C = EXT_STRIP;
    if (((s32(*)(const u8*, s32))MOD_RT_FONT_ADDR)(EXT_LINE, EXT_ROW)) {
        rect.x = dlg->nextLineX;
        rect.y = dlg->nextCharY * 12 + EXT_VY;
        rect.w = EXT_ROW / 2;
        rect.h = 12;
        // LoadImage and DrawSync: main's (config/symbols.us.txt)
        ((int (*)(RECT*, u_long*))0x80012B24)(
            &rect, (u_long*)(EXT_STRIP + 2 * EXT_ROW));
        ((int (*)(int))0x8001290C)(0);
    }
    *(u8**)0x8013794C = old;
}
