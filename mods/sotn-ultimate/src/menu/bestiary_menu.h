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
// X on a defeated enemy opens its page (7b): name, level, HP, Exp, the
// elements (the patch's symbols under Retrans), drops, the Librarian's
// picture and description. The description is read from LIB.BIN on the
// disc (its tables: the Librarian's, the RT one under Retrans) through
// DRA's CdFile_DemoKey (8 KB chunks at 0x801E8000, as the text packs), then
// drawn as two menu text lines (func_800F99B8: slots 0x80 / 0x81, VRAM x
// 0x180 y 48-79, the Spells screen's); the picture is the Librarian's
// (LoadMonsterLibrarianPreview), sent by BestPicCb instead of DRA's
// callback to VRAM x 0x180 y 0x80 (16 bpp, 96x112: the menu's text page,
// which the Relics / Spells screens draw again when they open) and not to
// the Librarian's place (x 0x20 y 0x100, the stage's VRAM).
// MOD_STEP_BEST has no MenuHandle case (between the Familiars steps 0x70 /
// 0x71 and System's 0x100): it must be at least MENU_STEP_OPENED, else
// MenuHandle does not call MenuDraw (nothing drawn, no input: a freeze, the
// first 7a build). Start closes the menu from it as from any screen.
#define MOD_LIB_NO_DESC // (read from LIB.BIN on the disc, below)
#include "../enemies/e_shop_mod_bestiary.h"

void func_800F8754(MenuContext* ctx, s32 x, s32 y);
void MenuFamiliarsDraw(MenuContext* ctx);
void MenuDrawInt(s32 number, s32 x, s32 y, MenuContext* ctx);
void MenuDrawRect(MenuContext* ctx, s32 posX, s32 posY, s32 width, s32 height,
                  s32 r, s32 g, s32 b);
extern MenuNavigation g_MenuNavigation;
void MenuDrawImg(MenuContext* ctx, s32 x, s32 y, s32 w, u32 h, s32 u, s32 v,
                 s32 clut, s32 tpage, bool disableTexShade, s32 c);
void func_800F99B8(const char* str, u32 y, bool arg2);
extern u8* D_8013794C;
extern u8 D_801EC000[];
extern void (*g_CdCallbacks[])(void);
extern s32 g_Cd[]; // CdThing (src/dra/dra.h): [4] D_80137F70, [5] F74,
                   // [6] F78, [11] overlayBlockCount, [12] its last size
// LIB.BIN's description tables: their addresses in stlib.elf, -D'd by
// build_sysopt.sh (the RT two 0 when the build has no RT text):
// BEST_LIB_DESC D_us_80180FB4 (retail bits), BEST_LIB_DESC_S g_ModLibDesc
// (Saturn bits, the skull), BEST_LIB_DESC_P g_ModLibDescPsp (Maria with the
// PSP / JP dubs: the string), BEST_LIB_RT g_ModLibRtDesc, BEST_LIB_RT_S
// g_ModLibRtDescSat
#define MENU_DG_MAIN 0
#define MENU_DG_BG 1
#define MENU_DG_FAMILIARS 15
#define MENU_STEP_OPENED 0x10
#define MENU_STEP_FAMILIAR_INIT 0x70
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
// (an _S string ends with 0xFF; C adds the 0 only at the end: each needs
// its own)
static const char g_BestLbl[] = // clang-format off
    _S("LV") "\0"
    _S("HP") "\0"
    _S("Exp") "\0"
    _S("Drop Items") "\0"
    _S("Strong VS.") "\0"
    _S("Immune") "\0"
    _S("Weak VS.") "\0"
    _S("Absorb") "\0"
    _S("None") "\0"
    _S("????????"); // clang-format on
static const char g_BestEl[] = _S("HOLDRKFIRTHUICEH2OSTNPSNCURCUTHIT");
// their element bits (1 << n): HOLY DARK FIRE THUNDER ICE WATER STONE
// POISON CURSE CUT HIT
static const u8 g_BestElBit[] = {12, 11, 15, 14, 13, 10, 9, 7, 8, 6, 5};
static s32 g_BestPage = 0; // 1: the detail page
// 1 from the Bestiary's opening to the next Familiars screen: the shared
// window is the Bestiary's while it closes (Triangle, or Start: the exit
// steps still draw it), so the Familiars screen is not drawn in it
static s32 g_BestOwn = 0;
static s32 g_BestLd = 0;   // its loading step (BestLoad)
static s32 g_BestOvl = 0;  // g_LoadOvlIdx before a chunk read
static u32 g_BestAt = 0;   // the LIB.BIN address being read
static s32 g_BestN = 0;    // description bytes copied
// the description read (the end of g_Pix[2]: the picture fills 0x5800
// bytes from g_Pix[0], the two text lines are drawn from g_Pix[0])
#define g_BestDesc (g_Pix[2] + 0x1800)
#define BEST_DESC_LEN 128
#define BEST_PIC_X 0x180
#define BEST_PIC_Y 0x80
#define BEST_CHUNK ((const u8*)0x801E8000)
// the list's cursor and first row shown (loaded with the file)
static s32 g_BestCur = 0;
static s32 g_BestTop = 0;

#define BEST_RT() (*(u8*)&MOD_DUB_STATE->textPack == MOD_TEXT_PACK_RT)
// "Bestiary"'s width: the RT 8 px font's under Retrans (BEST_RT_W,
// build_sysopt.sh from text_rt.py)
#define BEST_NAME_W (BEST_RT() ? BEST_RT_W : 64)

void ModBestMain(MenuContext* ctx, s32 x, s32 y) {
    MenuContext* box = &g_Menus[MENU_DG_FAMILIARS];

    func_800F8754(ctx, x, y);
    D_8013784C = 0;
    // the menu was closed (Start) on the Bestiary: its window is still up
    // when the menu opens again (no exit step hides it)
    if (g_MenuStep == MENU_STEP_OPENED && (box->unk1C == 0 || box->unk1C == 3)) {
        box->unk1C = 2; // (the page resets when the Bestiary opens)
    }
    // centred in the 76 px box, as the other rows
    MenuDrawStr(g_BestName, x + 38 - BEST_NAME_W / 2, y + 84, ctx);
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
        g_BestOwn = 1;
        g_BestPage = 0; // (a page left open by a Start exit)
    }
}

static void BestInput(void) {
    s32 cur = g_BestCur;
    u16 rep = g_pads[0].repeat;
    s32 row;

    if (g_pads[0].tapped & PAD_TRIANGLE) {
        g_BestPage = 0;
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
        row = g_ModLibBit[cur];
        if (g_ModLibEnemy[row] != 0xFFFF &&
            (g_CastleFlags[(row >> 3) + ENEMY_LIST_190] & (1 << (row & 7)))) {
            g_api.PlaySfx(SFX_UI_CONFIRM);
            g_BestPage = 1;
            g_BestLd = 1;
        } else {
            g_api.PlaySfx(SFX_UI_ERROR);
        }
        return;
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

// the n-th of the packed _S labels
static const char* BestLabel(s32 n) {
    const char* s = g_BestLbl;

    while (n--) {
        while (*s++ != 0xFF) {
        }
        s++;
    }
    return s;
}

// the LIB.BIN chunk (CdFile_DemoKey reads 4 sectors at its loc + 4 * idx)
// holding RAM address a, and a's offset in it
static s32 BestChunk(u32 a, s32* off) {
    s32 base = ST_LIB_BIN_OFF - MOD_TEXT_DEMOKEY_LBA;
    s32 sec = base + ((a - 0x80180000) >> 11);
    s32 idx = sec >> 2;

    *off = (a - 0x80180000) - (idx * 4 - base) * 0x800;
    return idx;
}

static s32 BestCdBusy(void) {
    return g_CdStep != CdStep_None || g_IsUsingCd;
}

static void BestRead(u32 a) {
    s32 off;

    g_BestAt = a;
    g_BestOvl = g_LoadOvlIdx;
    g_LoadOvlIdx = BestChunk(a, &off);
    g_LoadFile = CdFile_DemoKey;
    g_CdStep = CdStep_LoadInit;
}

// DRA's CopyMonsterPreviewCallback (src/dra/cd.c), sending the picture to
// the menu's text page instead; puts DRA's back when done
static void (*g_BestPicOld)(void) = (void*)1;
static void BestPicCb(void) {
    s32 len = g_Cd[11] ? 0x800 : g_Cd[12];
    u8* d = g_Pix[0] + g_Cd[5] * 0x800;
    u8* s = D_801EC000 + g_Cd[4] * 0x800;

    while (len--) {
        *d++ = *s++;
    }
    g_Cd[4] = (g_Cd[4] + 1) & 7;
    g_Cd[5]++;
    g_Cd[11]--;
    if (g_Cd[11] < 0 || (g_Cd[11] == 0 && g_Cd[12] == 0)) {
        LoadTPage((u_long*)g_Pix[0], 2, 0, BEST_PIC_X, BEST_PIC_Y, 0x60, 0x70);
        g_Cd[6] = 1;
        g_CdCallbacks[CdCallback_Monster] = g_BestPicOld;
        CdDataCallback(NULL);
    }
}

// the page's loads, one step a frame: the description's pointer, its
// string (and the next chunk if it runs on), the two text lines, the
// picture. 8: all done
static void BestLoad(s32 e) {
    s32 bit = LIB_BIT(e);
    s32 off, start;
    u32 tab;
    u8* s;

    if (BestCdBusy()) {
        return;
    }
    if (g_BestLd >= 2 && g_BestLd <= 4) {
        g_LoadOvlIdx = g_BestOvl; // (the read is done)
        BestChunk(g_BestAt, &off);
    }
    switch (g_BestLd) {
    case 1:
        g_BestN = 0;
        if (!BEST_RT() && bit == MOD_LIB_DESC_PSP_BIT && MOD_PSP_DUB_ON()) {
            BestRead(BEST_LIB_DESC_P); // (the string itself)
            g_BestLd = 3;
            break;
        }
        if (bit < MOD_LIB_RETAIL_ENEMIES) {
            tab = BEST_RT() && BEST_LIB_RT ? BEST_LIB_RT : BEST_LIB_DESC;
        } else {
            bit -= MOD_LIB_RETAIL_ENEMIES;
            tab = BEST_RT() && BEST_LIB_RT_S &&
                          bit < MOD_LIB_SATURN_ENEMIES - MOD_LIB_RETAIL_ENEMIES
                      ? BEST_LIB_RT_S
                      : BEST_LIB_DESC_S;
        }
        BestRead(tab + bit * 4);
        g_BestLd = 2;
        break;
    case 2:
        BestRead(*(u32*)(BEST_CHUNK + off));
        g_BestLd = 3;
        break;
    case 3:
    case 4:
        start = off;
        while (off < 0x2000 && g_BestN < BEST_DESC_LEN - 1) {
            if (!(g_BestDesc[g_BestN++] = BEST_CHUNK[off++])) {
                break;
            }
        }
        if (off == 0x2000 && g_BestLd == 3 && BEST_CHUNK[off - 1]) {
            BestRead(g_BestAt + (0x2000 - start)); // the next chunk
            g_BestLd = 4;
            break;
        }
        g_BestDesc[g_BestN] = 0;
        g_BestLd = 5;
        break;
    case 5:
        // the two lines: "@" ends the first
        for (s = g_BestDesc; *s && *s != '@'; s++) {
            if (*s >= 0x80) {
                s++; // (a Shift-JIS pair: its second byte may be 0x40)
            }
        }
        if (*s) {
            *s++ = 0;
        }
        D_8013794C = g_Pix[0];
        func_800F99B8((const char*)g_BestDesc, 0x80, false);
        func_800F99B8((const char*)s, 0x81, false);
        g_BestLd = 6;
        break;
    case 6:
        g_BestPicOld = g_CdCallbacks[CdCallback_Monster];
        g_CdCallbacks[CdCallback_Monster] = BestPicCb;
        if (g_api.LoadMonsterLibrarianPreview(LIB_PIC(e))) {
            g_BestLd = 7;
        } else {
            g_CdCallbacks[CdCallback_Monster] = g_BestPicOld;
        }
        break;
    case 7:
        g_BestLd = 8;
        break;
    }
}

// a row of element names (Retrans: the patch's symbols, tiles
// MOD_RT_ICON_TILE0..), or "None"
static void BestElems(u16 m, s32 y, MenuContext* ctx) {
    char s[5];
    s32 i, x = 148;

    if (!(m & ELEMENT_ALL)) {
        MenuDrawStr(BestLabel(8), x, y, ctx);
        return;
    }
    s[3] = 0xFF;
    s[4] = 0;
    for (i = 0; i < LEN(g_BestElBit); i++) {
        if (m & (1 << g_BestElBit[i])) {
            s[0] = g_BestEl[i * 3];
            s[1] = g_BestEl[i * 3 + 1];
            s[2] = g_BestEl[i * 3 + 2];
            if (BEST_RT()) {
                s[0] = MOD_RT_ICON_TILE0 + i;
                s[1] = 0xFF;
                s[2] = 0;
            }
            MenuDrawStr(s, x, y, ctx);
            x += BEST_RT() ? 12 : 28;
        }
    }
}

// a drop's name (src/st/lib/e_shop.c func_us_801B7C94)
static const char* BestItem(u16 id) {
    if (id < 0x80) {
        return BestLabel(8); // None (no other kind is listed)
    }
    id -= 0x80;
    if (id >= MOD_DROP_HAND_BASE) {
        return g_api.equipDefs[id - (MOD_DROP_HAND_BASE - NUM_HAND_ITEMS)].name;
    }
    if (id < NUM_HAND_ITEMS) {
        return g_api.equipDefs[id].name;
    }
    return g_api.accessoryDefs[id - NUM_HAND_ITEMS].name;
}

static void BestPage(MenuContext* ctx) {
    s32 e = g_BestCur;
    s32 bit = LIB_BIT(e);
    EnemyDef* def = &g_api.enemyDefs[g_ModLibEnemy[bit]];
    s32 i;

    if (ctx->unk1C == 0) {
        BestLoad(e);
        // back to the list once the loads are done (they use DRA's state)
        if ((g_pads[0].tapped & PAD_TRIANGLE) && g_BestLd == 8) {
            g_BestPage = 0;
            return;
        }
    }
    MenuDrawStr(def->name, 24, 36, ctx);
    MenuDrawStr(BestLabel(0), 28, 48, ctx); // LV
    if (e) {
        MenuDrawInt(def->level, 60, 48, ctx);
    } else {
        MenuDrawStr(BestLabel(9) + 6, 52, 48, ctx); // "??"
    }
    MenuDrawStr(BestLabel(1), 76, 48, ctx); // HP
    if (def->hitPoints > 9999) {
        MenuDrawStr(BestLabel(9) + 4, 100, 48, ctx); // "????"
    } else {
        MenuDrawInt(def->hitPoints, 124, 48, ctx);
    }
    MenuDrawStr(BestLabel(2), 148, 48, ctx); // Exp
    MenuDrawInt(def->exp, 204, 48, ctx);
    for (i = 0; i < 4; i++) {
        MenuDrawStr(BestLabel(4 + i), 140, 60 + i * 24, ctx);
    }
    BestElems(def->strengths, 72, ctx);
    BestElems(def->immunes, 96, ctx);
    BestElems(def->weaknesses, 120, ctx);
    BestElems(def->absorbs, 144, ctx);
    MenuDrawStr(BestLabel(3), 140, 156, ctx); // Drop Items
    MenuDrawStr(BestItem(def->uncommonItemId), 148, 166, ctx);
    if ((g_CastleFlags[(bit >> 3) + ENEMY_LIST_RAREDROP_1B0] &
         (1 << (bit & 7))) ||
        !def->rareItemId) {
        MenuDrawStr(BestItem(def->rareItemId), 148, 176, ctx);
    } else {
        MenuDrawStr(BestLabel(9), 148, 176, ctx);
    }
    if (g_BestLd >= 6) {
        // the description (as the info bar: 3 sprites of the 296 px lines)
        for (i = 0; i < 6; i++) {
            MenuDrawImg(ctx, 24 + (i % 3) * 128, 188 + (i / 3) * 16,
                        i % 3 == 2 ? 40 : 128, 16, (i % 3 & 1) << 7,
                        48 + (i / 3) * 16, 0x1A1, (i % 3) / 2 + 6, 1, 0);
        }
    }
    if (g_BestLd == 8) {
        MenuDrawImg(ctx, 24, 60, 96, 112, 0, BEST_PIC_Y, 0, 0x100 | 6, 1, 0);
    }
}

void ModBestDraw(MenuContext* ctx) {
    s32 i, e, x, y, bit, r;
    u16 enemy;

    if (g_MenuStep != MOD_STEP_BEST) {
        if (g_MenuStep == MENU_STEP_FAMILIAR_INIT ||
            g_MenuStep == MENU_STEP_FAMILIAR_INIT + 1) {
            g_BestOwn = 0;
        }
        if (!g_BestOwn) {
            MenuFamiliarsDraw(ctx);
        }
        return;
    }
    D_8013784C = 0;
    MenuDrawStr(g_BestNo, 284, 36, ctx);
    MenuDrawInt(g_BestCur + 1, 332, 36, ctx);
    if (g_BestPage) {
        BestPage(ctx);
        return;
    }
    if (ctx->unk1C == 0) {
        BestInput(); // (fully open)
    }
    MenuDrawStr(g_BestName, 180 - BEST_NAME_W / 2, 36, ctx);
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
