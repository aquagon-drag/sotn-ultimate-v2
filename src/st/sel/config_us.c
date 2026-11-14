// SPDX-License-Identifier: AGPL-3.0-or-later
#include "game.h"
#if defined(MOD_SATURN)
// Saturn port: SEL links its own copy of DRA's config tables (equipment,
// relics, spells, enemies...), but no SEL code or data refers to them. The
// mod keeps their data bytes (the retail ones, so SEL's data section and
// every address after it stay retail) and drops their strings, ~15 KB of
// rodata: room for the PSP dub toggle (the ending's PSP script copy, the
// select screen's dub row)
//
// Its first MOD_CREDITS_PSP_AREA bytes hold the staff roll of Ending = PSP
// (cutscene_credits_psp, build/us/credits_psp.bin from gen_credits_psp.py);
// the next MOD_TEXT_CD_AREA bytes SEL's text pack reader (ModTextReady and
// its state: mod_text_cd.inc, made by mods/sotn-ultimate/tools/
// gen_sel_text_cd.sh from mods/sotn-ultimate/src/menu/sel_text_cd.c; code
// runs from here as from SEL's .text); the rest are the retail bytes, and
// the text packs go in after the link at file offset 0x3000 (text_packs.py)
#define STR2(x) #x
#define STR(x) STR2(x)
__asm__(".pushsection .data\n"
        ".balign 4\n"
        ".global cutscene_credits_psp\n"
        "cutscene_credits_psp:\n"
        ".incbin \"build/us/credits_psp.bin\"\n"
        ".if . - cutscene_credits_psp > " STR(MOD_CREDITS_PSP_AREA) "\n"
        ".error \"credits_psp.bin outgrew MOD_CREDITS_PSP_AREA\"\n"
        ".endif\n"
        ".space " STR(MOD_CREDITS_PSP_AREA) " - (. - cutscene_credits_psp)\n"
        ".global g_ModTextCdArea\n"
        "g_ModTextCdArea:\n"
#include "mod_text_cd.inc"
        // (the code's size is known after relaxation only: .org, which
        // fails if it outgrew MOD_TEXT_CD_AREA, "moving .org backwards")
        ".org g_ModTextCdArea + " STR(MOD_TEXT_CD_AREA) "\n"
        ".incbin \"disks/us/ST/SEL/SEL.BIN\", 0x25FC + " STR(
            MOD_CREDITS_PSP_AREA) " + " STR(MOD_TEXT_CD_AREA) ", 0x7F10 - " STR(
            MOD_CREDITS_PSP_AREA) " - " STR(MOD_TEXT_CD_AREA) "\n"
        ".popsection");
#else
#include "../../config_us.h"
#endif
