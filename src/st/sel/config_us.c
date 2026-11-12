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
// the rest are the retail bytes, and the text packs go in after the link at
// file offset 0x3000 (text_packs.py)
#define STR2(x) #x
#define STR(x) STR2(x)
#if defined(MOD_TEST_ENDING_SHORTCUT)
// Test aid (game_mod.h; test branch only): the file menu's load jumps to the
// Dracula fight when L1+R1 are held from choosing the file (2C048.c calls
// ModTestEnding(false) when the file is chosen, (true) when its load is done).
// This cc1 does not honour a function's section attribute, so the function
// is hand-embedded as the cc1 -O2 output of the C below (#if 0), written
// into the first MOD_TEST_BYTES of the dead copy that follows: the object's
// .data stays 0x7F10 bytes and SEL's layout is unchanged.
#define MOD_TEST_BYTES 0x160 // the latch word + the code (build_disc checks)
// (step 5: the hook follows the staff roll table of Ending = PSP, which owns
// the first MOD_CREDITS_PSP_AREA bytes of the dead copy; the text packs start
// at 0x3000, past the hook)
#if 0
static s32 g_ModTestArm;
void ModTestEnding(s32 apply) {
    s32 i;
    EnemyDef* dracula;

    if (!apply) {
        g_ModTestArm =
            (g_pads[0].pressed & (PAD_L1 | PAD_R1)) == (PAD_L1 | PAD_R1);
        return;
    }
    if (!g_ModTestArm || g_PlayableCharacter != PLAYER_ALUCARD) {
        return;
    }
    g_ModTestArm = 0;
    // the arrival of teleport 0x08 (RCEN -> Dracula): RBO6 room 2 (31,30)
    g_StageId = STAGE_RBO6;
    g_Tilemap.left = 0x1F;
    g_Tilemap.top = 0x1E;
    // the good route's state (Richter freed, inverted castle open)
    g_CastleFlags[SHAFT_ORB_DEFEATED] = 1;
    g_CastleFlags[INVERTED_CASTLE_UNLOCKED] = 1;
    // max stats
    g_Status.hp = g_Status.hpMax = 9999;
    g_Status.mp = g_Status.mpMax = 99;
    g_Status.hearts = g_Status.heartsMax = 999;
    g_Status.level = 99;
    g_Status.exp = 99999999;
    for (i = 0; i < 4; i++) {
        g_Status.statsBase[i] = 99;
        g_Status.statsTotal[i] = 99 + g_Status.statsEquip[i];
    }
    // Dracula dies on the first hit that lands
    dracula = &g_api.enemyDefs[ENEMY_DRACULA_LV98];
    dracula->hitPoints = 1;
    dracula->defense = 0;
}
#endif
__asm__(".pushsection .data\n"
        ".balign 4\n"
        ".global cutscene_credits_psp\n"
        "cutscene_credits_psp:\n"
        ".incbin \"build/us/credits_psp.bin\"\n"
        ".if . - cutscene_credits_psp > " STR(MOD_CREDITS_PSP_AREA) "\n"
        ".error \"credits_psp.bin outgrew MOD_CREDITS_PSP_AREA\"\n"
        ".endif\n"
        ".space " STR(MOD_CREDITS_PSP_AREA) " - (. - cutscene_credits_psp)\n"
        "g_ModTestArm:\n"
        "\t.word 0\n"
        "\t.globl ModTestEnding\n"
        "ModTestEnding:\n"
        "\tbne\t$4,$0,.Lmt2\n"
        "\tlhu\t$2,g_pads\n"
        "\tandi\t$2,$2,0x000c\n"
        "\txori\t$2,$2,0x000c\n"
        "\tsltu\t$2,$2,1\n"
        "\tsw\t$2,g_ModTestArm\n"
        "\tj\t.Lmt1\n"
        ".Lmt2:\n"
        "\tlw\t$2,g_ModTestArm\n"
        "\tbeq\t$2,$0,.Lmt1\n"
        "\tlw\t$2,g_PlayableCharacter\n"
        "\t.set\tnoreorder\n"
        "\t.set\tnomacro\n"
        "\tbne\t$2,$0,.Lmt1\n"
        "\tli\t$4,0x05f50000\n"
        "\t.set\tmacro\n"
        "\t.set\treorder\n"
        "\tori\t$4,$4,0xe0ff\n"
        "\tmove\t$8,$0\n"
        "\tli\t$9,0x00000063\n"
        "\tla\t$3,g_Status+592\n"
        "\taddu\t$7,$3,56\n"
        "\taddu\t$6,$3,40\n"
        "\taddu\t$5,$3,24\n"
        "\tli\t$2,0x00000038\n"
        "\tsw\t$2,g_StageId\n"
        "\tli\t$2,0x0000001f\n"
        "\tsw\t$2,g_Tilemap+44\n"
        "\tli\t$2,0x0000001e\n"
        "\tsw\t$2,g_Tilemap+48\n"
        "\tli\t$2,0x00000001\n"
        "\tsb\t$2,g_CastleFlags+149\n"
        "\tsb\t$2,g_CastleFlags+150\n"
        "\tli\t$2,0x0000270f\n"
        "\tsw\t$2,g_Status+596\n"
        "\tsw\t$2,0($3)\n"
        "\tli\t$3,0x00000063\n"
        "\tli\t$2,0x000003e7\n"
        "\tsw\t$0,g_ModTestArm\n"
        "\tsw\t$3,g_Status+612\n"
        "\tsw\t$3,g_Status+608\n"
        "\tsw\t$2,g_Status+604\n"
        "\tsw\t$2,g_Status+600\n"
        "\tsw\t$3,g_Status+664\n"
        "\tsw\t$4,g_Status+668\n"
        ".Lmt8:\n"
        "\tsw\t$9,0($5)\n"
        "\tlw\t$2,0($6)\n"
        "\taddu\t$6,$6,4\n"
        "\taddu\t$5,$5,4\n"
        "\taddu\t$8,$8,1\n"
        "\taddu\t$2,$2,99\n"
        "\tsw\t$2,0($7)\n"
        "\tslt\t$2,$8,4\n"
        "\t.set\tnoreorder\n"
        "\t.set\tnomacro\n"
        "\tbne\t$2,$0,.Lmt8\n"
        "\taddu\t$7,$7,4\n"
        "\t.set\tmacro\n"
        "\t.set\treorder\n"
        "\tlw\t$3,g_api+148\n"
        "\tli\t$2,0x00000001\n"
        "\tsh\t$2,15164($3)\n"
        "\tsh\t$0,15170($3)\n"
        ".Lmt1:\n"
        "\tj\t$31\n"
        "ModTestEnd:\n"
        ".incbin \"disks/us/ST/SEL/SEL.BIN\", 0x25FC + " STR(
            MOD_CREDITS_PSP_AREA) " + 0x160, 0x7F10 - " STR(
            MOD_CREDITS_PSP_AREA) " - 0x160\n"
        ".popsection");
#else
__asm__(".pushsection .data\n"
        ".balign 4\n"
        ".global cutscene_credits_psp\n"
        "cutscene_credits_psp:\n"
        ".incbin \"build/us/credits_psp.bin\"\n"
        ".if . - cutscene_credits_psp > " STR(MOD_CREDITS_PSP_AREA) "\n"
        ".error \"credits_psp.bin outgrew MOD_CREDITS_PSP_AREA\"\n"
        ".endif\n"
        ".space " STR(MOD_CREDITS_PSP_AREA) " - (. - cutscene_credits_psp)\n"
        ".incbin \"disks/us/ST/SEL/SEL.BIN\", 0x25FC + " STR(
            MOD_CREDITS_PSP_AREA) ", 0x7F10 - " STR(MOD_CREDITS_PSP_AREA) "\n"
        ".popsection");
#endif
#else
#include "../../config_us.h"
#endif
