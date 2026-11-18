// SPDX-License-Identifier: AGPL-3.0-or-later
#if defined(VERSION_PSP) || defined(VERSION_HD)
#include "cutscene_actor_name_psp.h"
#else
extern const char* actor_names[];

#ifndef DRAW_NAME_ACTOR_INDEX
#define DRAW_NAME_ACTOR_INDEX actorIndex
#endif

// Creates primitives for the actor name at the head of the dialogue
static void DrawCutsceneActorName(u16 actorIndex, Entity* self) {
    Primitive* prim;
    s16 primIndex;
    s32 x;
    u16 chCount;
    const char* actorName;
    char ch;
#if defined(MOD_RT_CUTSCENE)
    // SOTN Ultimate, Script = Retrans: the retranslation's 8 px font (its
    // tiles from MOD_RT8_TILE0 and advances in the RT font room, as the menus)
    s32 rt = *(u8*)&MOD_DUB_STATE->textPack == MOD_TEXT_PACK_RT;
#if !defined(MOD_RT_CUT_EXT)
    const u8* rtW = (const u8*)(MOD_RT_FONT_END - MOD_RT8_CHARS);
#endif
#endif

    actorName = actor_names[DRAW_NAME_ACTOR_INDEX];
    chCount = 0;
    while (true) {
        ch = *actorName++;
        if (ch == DIAG_EOL) {
            ch = *actorName++;
            if (ch == DIAG_EOS) {
                break;
            }
        }
        if (ch == CH(' ')) {
            continue;
        }
        chCount++;
    }

    // Create chCount amount of sprites based on the actor name's letter count
    primIndex = g_api.AllocPrimitives(PRIM_SPRT, chCount);
    if (primIndex == -1) {
        DestroyEntity(self);
        return;
    }

    // Fill prims to render the actor name on screen
    prim = &g_PrimBuf[primIndex];
    g_Dialogue.primIndex[1] = primIndex;
    actorName = actor_names[DRAW_NAME_ACTOR_INDEX];
    x = 0x38;
    while (prim != NULL) {
        ch = *actorName++;
#if defined(MOD_RT_CUTSCENE) && !defined(MOD_RT_CUT_EXT)
        if (rt && (u8)ch < MOD_RT8_CHARS) {
            if (ch != CH(' ')) {
                prim->type = PRIM_SPRT;
                prim->tpage = 0x1E;
                prim->clut = PAL_UNK_196;
                prim->u0 = ((ch + MOD_RT8_TILE0) & 0x0F) * FONT_W;
                prim->v0 = ((ch + MOD_RT8_TILE0) & 0xF0) / (FONT_H / 4);
                prim->v1 = FONT_H;
                prim->u1 = FONT_W;
                prim->priority = 0x1FF;
                prim->drawMode = DRAW_HIDE;
                prim->x0 = x;
                prim->y0 = g_Dialogue.startY + 6;
                prim = prim->next;
            }
            x += rtW[(u8)ch];
            continue;
        }
#endif
        if (ch == CH(' ')) {
            x += FONT_SPACE;
        } else {
            prim->type = PRIM_SPRT;
            prim->tpage = 0x1E;
            prim->clut = PAL_UNK_196;
            prim->u0 = (ch & 0x0F) * FONT_W;
            prim->v0 = (ch & 0xF0) / (FONT_H / 4);
            prim->v1 = FONT_H;
            prim->u1 = FONT_W;
            prim->priority = 0x1FF;
            prim->drawMode = DRAW_HIDE;
            prim->x0 = x;
#ifdef DRAW_NAME_PRIM_Y0
            prim->y0 = DRAW_NAME_PRIM_Y0;
#else
            prim->y0 = g_Dialogue.startY + 6;
#endif
            prim = prim->next;
            x += FONT_GAP;
        }
    }
#if defined(MOD_RT_CUT_EXT)
    // (SEL: no room for the branch above; the same, done on the US sprites
    // by rt_ext.c in main.exe's free 8 KB)
    if (rt) {
        ((void (*)(s32, const void*, void*))MOD_RT_EXT_ADDR)(
            MOD_RT_EXT_NAME, actor_names[DRAW_NAME_ACTOR_INDEX],
            &g_PrimBuf[primIndex]);
    }
#endif
}
#endif
