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
// (VRAM y 0x180 + 12 * line; the band shows 12 rows: the shadow's 13th is
// cut). A half-typed Shift-JIS character fails ModRtText's check: no upload
// that frame. g_Dialogue.nextCharX only marks the line's start here.
#if defined(MOD_RT_CUTSCENE)
#define MOD_RT_CUT_BUF ((u8*)0x801E8000) // DEMO_KEY_PTR: idle in cutscenes
#define MOD_RT_CUT_ROW 96
#define MOD_RT_CUT_MAX 80

static u8 g_ModRtCutLine[MOD_RT_CUT_MAX + 4];
static s32 g_ModRtCutLen;

static void ModRtCutChar(u8 ch) {
    RECT rect;
    u8* old;
    s32 i;

    if (g_Dialogue.nextCharX == g_Dialogue.nextLineX) {
        g_ModRtCutLen = 0;
        for (i = 0; i < LEN(g_ModRtCutLine); i++) {
            g_ModRtCutLine[i] = 0;
        }
    }
    g_Dialogue.nextCharX++;
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
        rect.y = g_Dialogue.nextCharY * 12 + 0x180;
        rect.w = MOD_RT_CUT_ROW / 2;
        rect.h = 12;
        LoadImage(&rect, (u_long*)(MOD_RT_CUT_BUF + 2 * MOD_RT_CUT_ROW));
        DrawSync(0);
    }
    *(u8**)0x8013794C = old;
}
#define MOD_RT_CUT_ON()                                                        \
    (*(u8*)&MOD_DUB_STATE->textPack == MOD_TEXT_PACK_RT)
#endif
