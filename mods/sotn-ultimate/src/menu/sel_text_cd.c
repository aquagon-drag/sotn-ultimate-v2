// SPDX-License-Identifier: AGPL-3.0-or-later
// SOTN Ultimate: SEL's reader of the retranslation's text pack
// (SD/TXT_RT.BIN), ModTextReady. It runs from SEL's dead config copy
// (src/st/sel/config_us.c, MOD_TEXT_CD_AREA bytes after the PSP staff roll):
// mods/sotn-ultimate/tools/gen_sel_text_cd.sh compiles this file with SEL's
// cc1 and flags into src/st/sel/mod_text_cd.inc, which config_us.c
// assembles there (this cc1 ignores section attributes); build_disc.sh
// fails if the .inc is not this file's output. SEL had no room left for it.
// Its state is in the same copy (.data: the copy is read from the disc
// with SEL, so it starts at 0 on every visit; SEL's BSS is not cleared).
//
// Called by 2C048.c every frame of the fade into a game (Upd_Eng_18 new
// game, Upd_Eng_260 loaded game) once the fade is done and the music has
// stopped (func_801ACEC0: func_80131F68() == 0); the fade's end waits for 1.
// With Script = Retrans the RT pack is read chunk by chunk through DRA's
// CdFile_DemoKey (g_LoadOvlIdx = MOD_TEXT_RT_CD_IDX + chunk, 4 sectors to
// DEMO_KEY_PTR, as the System popup does, sysopt.c) and applied.
// - A read starts only when the CD and DRA's CD sound commands are idle:
//   no load (g_CdStep, g_IsUsingCd), no XA command queued or running
//   (MOD_CD_SND_QUEUE_POS / MOD_CD_SND_BUSY: CdFadeOut1/2's CdlPause or
//   CdSoundCommand6's Setloc + ReadN would take the drive from the read).
// - A read that has not ended MOD_TEXT_CD_WAIT vblanks after it started
//   is stopped (MOD_TEXT_CD_STOP, text_pack.h) and the chunk read again,
//   MOD_TEXT_CD_TRIES reads in all.
// - A chunk that fails its check, or the last try timing out: the dub's
//   text instead (ModTextSelDub: the restore pack undoes the chunks
//   applied, then the dub's pack, both from SEL's own copy), and the game
//   starts. g_ModTextCdFail (below) says which (tester aid).
#include "sel.h"
#include <disk.h>

#define TEXT_CD_BUF ((const u8*)0x801E8000) // DEMO_KEY_PTR
// (main's CD functions by address: gen_sel_text_cd.sh)
#define CdInit ((int (*)(void))SEL_CD_INIT)
#define CdReadyCallback ((void* (*)(void*))SEL_CD_READY_CB)
#define CdDataCallback ((void* (*)(void*))SEL_CD_DATA_CB)
#define MOD_TEXT_PROTOS
#include "text_pack.h"
void ModTextSelDub(void);             // 2C048_mod_player_select.h
extern const s32 g_ModTextRtCdIdx;   // SEL's rodata (check_text_packs.py)
// (words defined by gen_sel_text_cd.sh after the code)
extern s32 g_ModTextCd;     // 1 + the chunk on its way (0: none)
extern s32 g_ModTextCdOvl;  // g_LoadOvlIdx before the read
extern s32 g_ModTextCdT0;   // VSync(-1) when it started
extern s32 g_ModTextCdTry;  // reads of this chunk that timed out
extern s32 g_ModTextCdNext; // the next chunk to read
extern s32 g_ModTextCdGate; // frames the reads waited for the XA commands
extern s32 g_ModTextCdFail; // 1: a chunk failed its check, 2: timeouts

s32 ModTextReady(void) {
    const u8* b = TEXT_CD_BUF;
    s32 c;

    if (!MOD_SCRIPT_RETRANS() ||
        MOD_DUB_STATE->textPack == MOD_TEXT_TAG(MOD_TEXT_PACK_RT)) {
        return 1;
    }
    c = g_ModTextCd - 1;
    if (g_CdStep != CdStep_None || g_IsUsingCd) {
        // ours, past its time: stop it (the next idle frame reads it again)
        if (c >= 0 && VSync(-1) - g_ModTextCdT0 > MOD_TEXT_CD_WAIT) {
            MOD_TEXT_CD_STOP();
            g_LoadOvlIdx = g_ModTextCdOvl;
            g_ModTextCd = 0;
            if (++g_ModTextCdTry >= MOD_TEXT_CD_TRIES) {
                g_ModTextCdFail = 2;
            }
        }
        return 0;
    }
    if (g_ModTextCdFail) {
        ModTextSelDub();
        return 1;
    }
    if (c >= 0) {
        // chunk c read
        g_ModTextCd = 0;
        g_LoadOvlIdx = g_ModTextCdOvl;
        if (!ModTextChunkOk(b, c)) {
            g_ModTextCdFail = 1;
            ModTextSelDub();
            return 1;
        }
        ModTextRun(b, MOD_TEXT_PACK_RT);
        if (++c >= b[9]) {
            MOD_DUB_STATE->textPack = MOD_TEXT_TAG(MOD_TEXT_PACK_RT);
            return 1;
        }
        g_ModTextCdNext = c;
        g_ModTextCdTry = 0;
    }
    // no XA command queued or running (MOD_TEXT_CD_WAIT frames at most in
    // all: a queue that never empties does not hold the game)
    if ((MOD_CD_SND_QUEUE_POS || MOD_CD_SND_BUSY) &&
        ++g_ModTextCdGate < MOD_TEXT_CD_WAIT) {
        return 0;
    }
    c = g_ModTextCdNext;
    if (!c) {
        MOD_DUB_STATE->textPack = 0; // (until its last chunk is applied)
    }
    g_ModTextCdOvl = g_LoadOvlIdx;
    g_LoadOvlIdx = g_ModTextRtCdIdx + c;
    g_LoadFile = CdFile_DemoKey;
    g_CdStep = CdStep_LoadInit;
    g_ModTextCd = c + 1;
    g_ModTextCdT0 = VSync(-1);
    return 0;
}
