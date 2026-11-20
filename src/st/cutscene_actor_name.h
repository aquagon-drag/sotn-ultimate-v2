// SPDX-License-Identifier: AGPL-3.0-or-later
#if defined(VERSION_PSP) || defined(VERSION_HD)
#include "cutscene_actor_name_psp.h"
#else
extern const char* actor_names[];

#ifndef DRAW_NAME_ACTOR_INDEX
#define DRAW_NAME_ACTOR_INDEX actorIndex
#endif

#if defined(MOD_CUT_REPICK)
// SOTN Ultimate: the Script or Dub row changed in the System screen after
// the room loaded (SetCutsceneScript chose the copy then): at the first name
// tag the copy is chosen again, and the script goes on in the new one right
// after its first SET_PORTRAIT, as here (mod_psp_script.h ModCutOff;
// psp_script.py repick_offs). Anything else: the copy plays on as before
static void ModCutRepick(void) {
    u8* s;
    u32 a;
    u32 b;
#if defined(MOD_RT_CUTSCENE)
    u8 rt = g_ModRtCutScript;
#endif

    if (!g_ModCutFirst) {
        return;
    }
    g_ModCutFirst = 0;
    s = ModPspScriptPick(g_ModCutOrig);
    if (s != g_ModCutPicked) {
        a = ModCutOff(g_ModCutPicked);
        b = ModCutOff(s);
        if (a && b && g_Dialogue.scriptCur == g_ModCutPicked + a) {
            g_Dialogue.scriptCur = s + b;
            g_ModCutPicked = s;
            return;
        }
    }
#if defined(MOD_RT_CUTSCENE)
    g_ModRtCutScript = rt;
#endif
}
#endif

// Creates primitives for the actor name at the head of the dialogue
static void DrawCutsceneActorName(u16 actorIndex, Entity* self) {
    Primitive* prim;
    s16 primIndex;
    s32 x;
    u16 chCount;
    const char* actorName;
    char ch;
#if defined(MOD_RT_CUTSCENE) && !defined(MOD_RT_CUT_EXT)
    // SOTN Ultimate, Script = Retrans: the retranslation's 8 px font (its
    // tiles from MOD_RT8_TILE0 and advances in the RT font room, as the menus)
    s32 rt = *(u8*)&MOD_DUB_STATE->textPack == MOD_TEXT_PACK_RT;
    const u8* rtW = (const u8*)(MOD_RT_FONT_END - MOD_RT8_CHARS);
#endif

#if defined(MOD_CUT_REPICK)
    ModCutRepick();
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
#ifdef DRAW_NAME_PRIM_Y0
                prim->y0 = DRAW_NAME_PRIM_Y0;
#else
                prim->y0 = g_Dialogue.startY + 6;
#endif
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
    if (g_ModRtCutScript) {
        ((void* (*)(s32, void*))MOD_RT_EXT_ADDR)(MOD_RT_EXT_NAME, (void*)(s32)primIndex);
    }
#endif
}
#endif
