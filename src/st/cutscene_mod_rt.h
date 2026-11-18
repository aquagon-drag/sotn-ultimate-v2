// SPDX-License-Identifier: AGPL-3.0-or-later
// SOTN Ultimate (step 6b, cutscenes): Script = Retrans draws the dialogue
// with the retranslation's 12 px font (the RT pack's ModRtText at
// MOD_RT_FONT_ADDR, there exactly while the RT tag is set). Included by an
// overlay's cutscene file after its mod_psp_script.h, when that defines
// MOD_RT_CUTSCENE (mods/sotn-ultimate/tools/psp_script.py RT_OVERLAYS: the
// overlay has RT copies of its scripts, whose text is ASCII letters and
// Shift-JIS punctuation, text_rt.to_bios).
// Each typed byte is added to the line; the whole line is drawn again into a
// RAM strip (192 px, 4 bpp: 96 bytes a row; ModRtText draws the glyphs in
// its rows 2-14) and loaded into the line's band of the text texture
// (VRAM y MOD_RT_CUT_VY + 12 * line; the band shows 12 rows: the shadow's
// 13th is cut). A half-typed Shift-JIS character fails ModRtText's check: no
// upload that frame.
// Only while the playing script is an RT copy (g_ModRtCutScript, set by
// mod_psp_script.h's ModPspScript): any other script keeps the US drawing.
// Two ways in:
// - C cutscenes: the hook in the character branch calls ModRtCutChar
//   (g_Dialogue.nextCharX only marks the line's start there);
// - asm-only bosses (MOD_RT_CUT_ASM): psp_script.py --apply points the
//   character's `jal MoveImage` at ModRtMoveImage, which gets the byte back
//   from the source rect and the spaces from the gaps in nextCharX (the asm
//   adds 2 for a space without drawing, and 2 after each character).
#if defined(MOD_RT_CUTSCENE)
#define MOD_RT_CUT_BUF ((u8*)0x801E8000) // DEMO_KEY_PTR: idle in cutscenes
#define MOD_RT_CUT_ROW 96
#define MOD_RT_CUT_MAX 80
#ifndef MOD_RT_CUT_VY
#define MOD_RT_CUT_VY 0x180 // the text texture's top (NO3: 0x100)
#endif

static u8 g_ModRtCutLine[MOD_RT_CUT_MAX + 4];
static s32 g_ModRtCutLen;

#define MOD_RT_CUT_ON()                                                        \
    (g_ModRtCutScript &&                                                       \
     *(u8*)&MOD_DUB_STATE->textPack == MOD_TEXT_PACK_RT)

static void ModRtCutPut(u8 ch, s32 start) {
    RECT rect;
    u8* old;
    s32 i;

    if (start) {
        g_ModRtCutLen = 0;
        for (i = 0; i < LEN(g_ModRtCutLine); i++) {
            g_ModRtCutLine[i] = 0;
        }
    }
    if (g_ModRtCutLen < MOD_RT_CUT_MAX) {
        g_ModRtCutLine[g_ModRtCutLen++] = ch;
    }
    for (i = 0; i < MOD_RT_CUT_ROW * 15; i++) {
        MOD_RT_CUT_BUF[i] = 0;
    }
    old = *(u8**)0x8013794C; // DRA menu.c D_8013794C, ModRtText's line
    *(u8**)0x8013794C = MOD_RT_CUT_BUF;
    if (((s32(*)(const u8*, s32))MOD_RT_FONT_ADDR)(
            g_ModRtCutLine, MOD_RT_CUT_ROW)) {
        rect.x = g_Dialogue.nextLineX;
        rect.y = g_Dialogue.nextCharY * 12 + MOD_RT_CUT_VY;
        rect.w = MOD_RT_CUT_ROW / 2;
        rect.h = 12;
        LoadImage(&rect, (u_long*)(MOD_RT_CUT_BUF + 2 * MOD_RT_CUT_ROW));
        // (DrawSync: main's, config/symbols.us.txt; the stages' link
        // lists do not name it) the strip is cleared for the next byte
        ((int (*)(int))0x8001290C)(0);
    }
    *(u8**)0x8013794C = old;
}

#if defined(MOD_RT_CUT_ASM)
static s32 g_ModRtCutX; // nextCharX after the last character
static s32 g_ModRtCutY; // its band (MoveImage's y)

// (called by the asm's patched jal; MoveImage's arguments)
void ModRtMoveImage(RECT* src, s32 x, s32 y) {
    s32 i;
    u8 ch;

    if (!MOD_RT_CUT_ON() || src->w != 2 || src->h != 8) {
        MoveImage(src, x, y);
        return;
    }
    // the asm's source: x = (ch & 0xF) * 2 + 0x380, y = (ch & 0xF0) / 2 + 0xF0
    ch = ((src->x - 0x380) >> 1) | ((src->y - 0xF0) << 1);
    // a new line: at its start, in another band, or back to the left (a
    // line that starts with spaces)
    if (x == g_Dialogue.nextLineX || y != g_ModRtCutY || x < g_ModRtCutX) {
        g_ModRtCutLen = 0;
        for (i = 0; i < LEN(g_ModRtCutLine); i++) {
            g_ModRtCutLine[i] = 0;
        }
        g_ModRtCutX = g_Dialogue.nextLineX;
        g_ModRtCutY = y;
    }
    for (; g_ModRtCutX < x && g_ModRtCutLen < MOD_RT_CUT_MAX; g_ModRtCutX += 2) {
        g_ModRtCutLine[g_ModRtCutLen++] = ' ';
    }
    g_ModRtCutX = x + 2;
    ModRtCutPut(ch, 0);
}
#else
static void ModRtCutChar(u8 ch) {
    s32 start = g_Dialogue.nextCharX == g_Dialogue.nextLineX;

    g_Dialogue.nextCharX++;
    ModRtCutPut(ch, start);
}
#endif
#endif
