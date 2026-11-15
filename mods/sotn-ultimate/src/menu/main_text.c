// SPDX-License-Identifier: AGPL-3.0-or-later
// SOTN Ultimate (step 6b): the stages' shared text code, in the boot
// executable (main.exe = SLUS_000.67) over libgpu's debug font (kanjiclut and
// its glyphs, 0x8002B818-0x8002C218: only FntLoad reads them and nothing calls
// FntLoad). Built by mods/sotn-ultimate/tools/build_main_text.sh, linked at
// MOD_MAIN_TEXT_ADDR and taken in by src/main/psxsdk/libgpu/font.c. As the
// retranslation patch does (its VWF8 / VWF12 in the same place), every
// stage's own BlitChar (src/st/blit_char.h, 0x2B0 bytes), BottomCornerText
// (src/st/popup.h) and the two BlitChar loops of src/st/e_collect.h call in
// here through the table that starts the blob (include/game_mod.h
// MOD_MAIN_TEXT_*), which leaves room in every stage overlay.
// Script = Retrans (the RT pack's tag in g_ModDub): the relic's "Obtained X"
// line and the stages' message boxes are drawn with the retranslation's 12 px
// font (ModRtText, in DRA's RT font room), the bottom corner's item name with
// its 8 px font (tiles MOD_RT8_TILE0.., the room's advances); else the US
// code, unchanged.
#include "game.h"
#include "palettes.h"

#define MT_RT() (*(u8*)&MOD_DUB_STATE->textPack == MOD_TEXT_PACK_RT)
#define MT_RT8_W ((const u8*)(MOD_RT_FONT_END - MOD_RT8_CHARS))
#define MT_RT_TEXT ((s32(*)(const u8*, s32))MOD_RT_FONT_ADDR)
#define MT_RT_LINE (*(u8**)0x8013794C) // DRA menu.c's line pointer

const char* ModTxtBlitChar(const char* str, u16* xOffset, u8* pix, u16 stride);
s32 ModTxtRelic(const char* pre, const char* name, u8* pix);
void ModTxtBox(const char* str, u8* pix, s32 width);
void ModTxtCorner(u8* str, u8 leftAlign);

// the table (MOD_MAIN_TEXT_BLIT / _RELIC / _BOX / _CORNER: its entries)
__asm__(".text\n"
        ".word ModTxtBlitChar\n"
        ".word ModTxtRelic\n"
        ".word ModTxtBox\n"
        ".word ModTxtCorner\n");

// src/st/blit_char.h's BlitChar (US), unchanged
const char* ModTxtBlitChar(
    const char* str, u16* xOffset, u8* pix, u16 stride) {
    const u16 DOUBLE_SPACE = 0x8140;
    const u16 RIGHT_DOUBLE_QUOTATION_MARK = 0x8168;
    const int FontWidth = 12;
    const int FontHeight = 16;
    const int FontStride = FontWidth / 2;
    u16 ch;
    s32 chSize;
    s32 i, j;
    s32 letterWidth;
    u8* chPix;
    u8* ptr;

    ch = *str++;
    chSize = 0;
    if (ch >= 'a' && ch <= 'z') {
        ch += 0x8220;
    } else if (ch >= 'A' && ch <= 'Z') {
        ch += 0x821F;
    } else {
        if (ch == ' ') {
            ch = DOUBLE_SPACE;
            chSize = 2;
        } else {
            ch = *str++ | (ch << 8);
            if (ch == DOUBLE_SPACE) {
                chSize = 2;
            }
        }
    }
    if (ch == RIGHT_DOUBLE_QUOTATION_MARK) {
        str += 2;
    }
    chPix = g_api.func_80106A28(ch, 1);
    while (true) {
        if (ch == DOUBLE_SPACE) {
            break;
        }
        for (i = 0; i < FontHeight; i++) {
            if (chPix[i * FontStride]) {
                break;
            }
        }
        if (i != FontHeight) {
            break;
        }
        for (i = 0; i < FontHeight; i++) {
            ptr = &chPix[i * FontStride];
            for (j = 0; j < 5; j++) {
                ptr[0] = ptr[1];
                ptr++;
            }
            *ptr = 0;
        }
    }
    for (i = 0, letterWidth = 0; i < FontHeight; i++) {
        for (j = 0; j < FontStride; j++) {
            if (chPix[i * FontStride + j] && letterWidth < j) {
                letterWidth = j;
            }
        }
    }
    for (i = 0; i < FontHeight; i++) {
        if (chPix[letterWidth + i * FontStride] & 0xF0) {
            break;
        }
    }
    if (i != FontHeight) {
        letterWidth++;
    }
    if (letterWidth < FontStride) {
        letterWidth++;
    }
    for (i = 0; i < FontHeight; i++) {
        ptr = &pix[*xOffset + i * stride];
        *ptr++ = *chPix++;
        *ptr++ = *chPix++;
        *ptr++ = *chPix++;
        *ptr++ = *chPix++;
        *ptr++ = *chPix++;
        *ptr++ = *chPix++;
    }
    *xOffset += letterWidth + chSize;
    return str;
}

// one line of str (to a byte < 2 or its end) with the RT 12 px font into the
// 16 rows at pix, stride bytes a row; its width in bytes (2 px), 0 when the
// font lacks a character (nothing drawn)
static s32 MtRtLine(const char* str, u8* pix, s32 stride) {
    u8 line[128];
    u8* old = MT_RT_LINE;
    s32 n, w;

    for (n = 0; (u8)*str >= 2 && n < LEN(line) - 1;) {
        line[n++] = *str++;
    }
    line[n] = 0;
    MT_RT_LINE = pix;
    w = MT_RT_TEXT(line, stride);
    MT_RT_LINE = old;
    return w ? (w - 1 + 1) / 2 : 0;
}

// src/st/e_collect.h EntityRelicOrb, step 6 (US): pre + name ("Obtained "
// + the relic's name) into pix (0xC0 bytes a row, 16 rows); the line's
// width in bytes (its half-width in px: the box is centred with it)
s32 ModTxtRelic(const char* pre, const char* name, u8* pix) {
    u8 both[96];
    const char* s;
    u16 len = 0;
    s32 i;

    for (i = 0; i < 0xC00; i++) {
        pix[i] = 0;
    }
    if (MT_RT()) {
        for (i = 0, s = pre; *s && i < LEN(both) - 1;) {
            both[i++] = *s++;
        }
        for (s = name; *s && i < LEN(both) - 1;) {
            both[i++] = *s++;
        }
        both[i] = 0;
        i = MtRtLine((const char*)both, pix, 0xC0);
        if (i) {
            return i;
        }
    }
    for (s = pre; *s;) {
        s = ModTxtBlitChar(s, &len, pix, 0xC0);
    }
    for (s = name; *s;) {
        s = ModTxtBlitChar(s, &len, pix, 0xC0);
    }
    return len;
}

// src/st/e_collect.h EntityMessageBox (US): str (1: next line) into pix,
// width px wide (width / 2 bytes a row), 16 rows a line; pix already clear
void ModTxtBox(const char* str, u8* pix, s32 width) {
    u16 xOffset = 0;
    u8* chPix = pix;

    if (MT_RT()) {
        if (MtRtLine(str, pix, width >> 1)) {
            while ((u8)*str >= 2) {
                str++;
            }
            if (*str != 1 || MtRtLine(str + 1, &pix[width * 8], width >> 1)) {
                return;
            }
        }
        // (a character the font lacks: the US way)
        for (xOffset = 0; xOffset < width * 16; xOffset++) {
            pix[xOffset] = 0;
        }
        xOffset = 0;
    }
    while (*str) {
        if (*str == 1) {
            str++;
            xOffset = 0;
            chPix = &pix[width * 8];
        } else {
            str = ModTxtBlitChar(str, &xOffset, chPix, width >> 1);
        }
    }
}

// src/st/popup.h BottomCornerText (US); Retrans: the RT 8 px font's tiles
// and advances for the characters it has
void ModTxtCorner(u8* str, u8 leftAlign) {
    u8 toPrint[64];
    Primitive* prim;
    s32 i;
    u8 ch;
    u8* chIdx;
    u16 textWidth;
    u16 xPos;
    s16 xPos2;
    s32 rt = MT_RT();

    chIdx = (u8*)&toPrint;
    xPos = textWidth = 0;
    for (i = 0; i < 64; i++) {
        *chIdx++ = 0;
    }
    chIdx = (u8*)&toPrint;
    while (true) {
        ch = *str++;
        if (ch == 0xFF) {
            ch = *str++;
            if (ch == 0) {
                break;
            }
        }
        *chIdx++ = ch;
        if (ch) {
            xPos++;
        }
        if (rt && ch < MOD_RT8_CHARS) {
            textWidth += MT_RT8_W[ch];
        } else if (ch) {
            textWidth += 8;
        } else {
            textWidth += 4;
        }
    }
    g_unkGraphicsStruct.BottomCornerTextPrims =
        g_api.AllocPrimitives(PRIM_SPRT, xPos + 4);
    if (g_unkGraphicsStruct.BottomCornerTextPrims == -1) {
        return;
    }
    prim = &g_PrimBuf[g_unkGraphicsStruct.BottomCornerTextPrims];
    prim->type = PRIM_G4;
    PRED(prim) = 0;
    PGRN(prim) = 0;
    PBLU(prim) = 0;
    if (leftAlign) {
        prim->b0 = prim->b1 = 0xAF;
    } else {
        prim->g0 = prim->g1 = 0x5F;
    }
    if (leftAlign) {
        textWidth += 4;
    }
    if (leftAlign) {
        xPos = 7;
    } else {
        xPos = 0xD4 - textWidth;
    }
    prim->x0 = prim->x2 = xPos;
    prim->x1 = prim->x3 = xPos + textWidth + 0x20;
    prim->y0 = prim->y1 = 0xD0;
    prim->y2 = prim->y3 = 0xDF;
    prim->priority = 0x1EE;
    prim->drawMode = DRAW_TPAGE | DRAW_TRANSP;
    prim = prim->next;

    prim->tpage = 0x1F;
    prim->clut = PAL_UNK_197;
    prim->x0 = xPos - 6;
    prim->y0 = 0xCB;
    prim->u0 = 0x80;
    prim->v0 = 0;
    prim->u1 = 0x10;
    prim->v1 = 0x18;
    prim->priority = 0x1EF;
    prim->drawMode = DRAW_DEFAULT;
    prim = prim->next;

    prim->tpage = 0x1F;
    prim->clut = PAL_UNK_197;
    prim->x0 = xPos + textWidth + 0x16;
    prim->y0 = 0xCB;
    prim->u0 = 0xA8;
    prim->v0 = 0;
    prim->u1 = 0x10;
    prim->v1 = 0x18;
    prim->priority = 0x1EF;
    prim->drawMode = DRAW_DEFAULT;
    prim = prim->next;

    prim->type = PRIM_GT4;
    prim->tpage = 0x1F;
    prim->clut = PAL_UNK_197;
    prim->x0 = prim->x2 = xPos + 0xA;
    prim->x1 = prim->x3 = xPos + textWidth + 0x18;
    prim->y0 = prim->y1 = 0xCD;
    prim->y2 = prim->y3 = 0xE1;
    prim->u0 = prim->u2 = 0x98;
    prim->u1 = prim->u3 = 0x9C;
    prim->v0 = prim->v1 = 2;
    prim->v2 = prim->v3 = 0x16;
    prim->priority = 0x1EF;
    prim->drawMode = DRAW_DEFAULT;
    prim = prim->next;

    xPos2 = xPos + 0x10;
    chIdx = (u8*)&toPrint;
    while (prim != NULL) {
        ch = *chIdx++;
        if (ch) {
            prim->tpage = 0x1E;
            prim->clut = PAL_UNK_196;
            i = rt && ch < MOD_RT8_CHARS ? ch + MOD_RT8_TILE0 : ch;
            prim->u0 = (s8)((i & 0x0F) << 3);
            prim->v0 = (s8)((i & 0xF0) >> 1);
            prim->u1 = prim->v1 = 8;
            prim->priority = 0x1F0;
            prim->drawMode = DRAW_DEFAULT;
            prim->x0 = xPos2;
            prim->y0 = 0xD4;
            prim = prim->next;
        }
        if (rt && ch < MOD_RT8_CHARS) {
            xPos2 += MT_RT8_W[ch];
        } else if (ch) {
            xPos2 += 8;
        } else {
            xPos2 += 4;
        }
    }
    g_unkGraphicsStruct.BottomCornerTextTimer = 0x130;
}
