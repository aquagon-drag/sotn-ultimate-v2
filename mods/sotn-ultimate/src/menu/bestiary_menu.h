// SPDX-License-Identifier: AGPL-3.0-or-later
// SOTN Ultimate: included by mods/sotn-ultimate/src/menu/sysopt.c (step 7)
// The pause menu's sixth row, "Bestiary" (Alucard games, from the start):
// the Librarian's monster list (the Saturn's order and bits,
// src/st/lib/mod_bestiary.h) on a pause menu screen, in the Familiars box's
// window (MENU_DG_FAMILIARS, 0 24 360 200). Names come from the enemy table
// (the RT pack's under Retrans, drawn with its 8 px font by MenuDrawStr);
// an enemy not defeated yet shows dashes, as in the Librarian.
// DRA calls in through three stubs (src/config_us.h, header entries 16, 20
// and 24): ModBestMain draws the main box's rows plus this one, ModBestInput
// is the main box's input (six rows; X on Bestiary enters MOD_STEP_BEST),
// ModBestDraw draws the screen (or the Familiars one) and takes its input.
// MOD_STEP_BEST has no MenuHandle case (between the Familiars steps 0x70 /
// 0x71 and System's 0x100): it must be at least MENU_STEP_OPENED, else
// MenuHandle does not call MenuDraw (nothing drawn, no input: a freeze, the
// first 7a build). Start closes the menu from it as from any screen.
#include "../../../../src/st/lib/mod_bestiary.h"

void func_800F8754(MenuContext* ctx, s32 x, s32 y);
void MenuFamiliarsDraw(MenuContext* ctx);
void MenuDrawInt(s32 number, s32 x, s32 y, MenuContext* ctx);
void MenuDrawRect(MenuContext* ctx, s32 posX, s32 posY, s32 width, s32 height,
                  s32 r, s32 g, s32 b);
extern MenuNavigation g_MenuNavigation;
#define MENU_DG_MAIN 0
#define MENU_DG_BG 1
#define MENU_DG_FAMILIARS 15
#define MENU_STEP_OPENED 0x10
#define MOD_STEP_BEST 0x7F
#define BEST_ROW 5 // the main box's sixth row
#define BEST_X0 28 // the list's two columns
#define BEST_DX 172
#define BEST_Y0 60 // its first row
#define BEST_DY 12
#define BEST_ROWS 12 // rows shown
#define BEST_CELLS MOD_LIB_NUM_ENEMIES
#define BEST_LINES ((BEST_CELLS + 1) / 2)

static const char g_BestName[] = _S("Bestiary");
static const char g_BestNone[] = _S("--------------");
static const char g_BestNo[] = _S("No.");
// the list's cursor and first row shown (loaded with the file)
static s32 g_BestCur = 0;
static s32 g_BestTop = 0;

#define BEST_RT() (*(u8*)&MOD_DUB_STATE->textPack == MOD_TEXT_PACK_RT)
// a menu string's width: the RT 8 px font's advances under Retrans
static s32 BestWidth(const u8* s) {
    const u8* w = (const u8*)(MOD_RT_FONT_END - MOD_RT8_CHARS);
    s32 n = 0;

    for (; *s != 0xFF; s++) {
        n += (BEST_RT() && *s < MOD_RT8_CHARS) ? w[*s] : 8;
    }
    return n;
}

void ModBestMain(MenuContext* ctx, s32 x, s32 y) {
    func_800F8754(ctx, x, y);
    D_8013784C = 0;
    // centred in the 76 px box, as the other rows
    MenuDrawStr(g_BestName, x + 38 - BestWidth(g_BestName) / 2, y + 84, ctx);
}

void ModBestInput(s32* nav, u8 nOptions, u32 type) {
    MenuContext* box = &g_Menus[MENU_DG_FAMILIARS];

    MenuHandleCursorInput(nav, BEST_ROW + 1, type);
    // X: the screen (MENU_STEP_OPENED then hides the main box and plays the
    // confirm sound, as it does for a changed step)
    if (*nav == BEST_ROW && (g_pads[0].tapped & PAD_CROSS)) {
        box->unk1C = 3; // MenuShow
        box->unk1D = 0;
        g_MenuStep = MOD_STEP_BEST;
    }
}

static void BestInput(void) {
    s32 cur = g_BestCur;
    u16 rep = g_pads[0].repeat;
    s32 row;

    if (g_pads[0].tapped & PAD_TRIANGLE) {
        g_Menus[MENU_DG_FAMILIARS].unk1C = 1; // MenuHide
        g_Menus[MENU_DG_FAMILIARS].unk1D = 0;
        g_Menus[MENU_DG_MAIN].unk1C = 3; // MenuShow
        g_Menus[MENU_DG_MAIN].unk1D = 0;
        g_Menus[MENU_DG_BG].unk1C = 3;
        g_Menus[MENU_DG_BG].unk1D = 0;
        g_MenuStep = MENU_STEP_OPENED;
        return;
    }
    if (g_pads[0].tapped & PAD_CROSS) {
        g_api.PlaySfx(SFX_UI_ERROR); // the detail page comes next (step 7b)
    }
    if (rep & PAD_UP) {
        cur -= 2;
    } else if (rep & PAD_DOWN) {
        cur += 2;
    } else if (rep & (PAD_LEFT | PAD_RIGHT)) {
        cur ^= 1;
    } else if (rep & PAD_L1) {
        cur -= BEST_ROWS * 2;
    } else if (rep & PAD_R1) {
        cur += BEST_ROWS * 2;
    }
    if (cur < 0) {
        cur = g_BestCur & 1;
    }
    if (cur >= BEST_CELLS) {
        if (rep & (PAD_DOWN | PAD_R1)) {
            // the last row, same column (or the cell left of a blank one)
            cur = (BEST_LINES - 1) * 2 + (g_BestCur & 1);
            if (cur >= BEST_CELLS) {
                cur = BEST_CELLS - 1;
            }
        } else {
            cur = g_BestCur;
        }
    }
    if (cur != g_BestCur) {
        g_api.PlaySfx(SFX_UI_MOVE);
        g_BestCur = cur;
    }
    row = g_BestCur / 2;
    if (row < g_BestTop) {
        g_BestTop = row;
    }
    if (row >= g_BestTop + BEST_ROWS) {
        g_BestTop = row - BEST_ROWS + 1;
    }
}

void ModBestDraw(MenuContext* ctx) {
    s32 i, e, x, y, bit, r;
    u16 enemy;

    if (g_MenuStep != MOD_STEP_BEST) {
        MenuFamiliarsDraw(ctx);
        return;
    }
    if (g_BestCur >= BEST_CELLS) {
        g_BestCur = 0; // (a list of another size)
        g_BestTop = 0;
    }
    if (ctx->unk1C == 0) {
        BestInput(); // (fully open)
    }
    D_8013784C = 0;
    MenuDrawStr(g_BestName, 180 - BestWidth(g_BestName) / 2, 40, ctx);
    MenuDrawStr(g_BestNo, 284, 40, ctx);
    MenuDrawInt(g_BestCur + 1, 332, 40, ctx);
    for (i = 0; i < BEST_ROWS * 2; i++) {
        e = g_BestTop * 2 + i;
        if (e >= BEST_CELLS) {
            break;
        }
        x = BEST_X0 + (i & 1) * BEST_DX;
        y = BEST_Y0 + (i / 2) * BEST_DY;
        bit = g_ModLibBit[e];
        enemy = g_ModLibEnemy[bit];
        if (enemy == 0xFFFF) {
            continue;
        }
        if (g_CastleFlags[(bit >> 3) + ENEMY_LIST_190] & (1 << (bit & 7))) {
            MenuDrawStr(g_api.enemyDefs[enemy].name, x, y, ctx);
        } else {
            MenuDrawStr(g_BestNone, x, y, ctx);
        }
        if (e == g_BestCur) {
            r = g_Timer & 0x20 ? 0x40 + (g_Timer & 0x1F)
                               : 0x5F - (g_Timer & 0x1F);
            MenuDrawRect(ctx, x - 4, y - 2, BEST_DX - 8, BEST_DY, r, 0, 0);
        }
    }
}
