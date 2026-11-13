# Step 1 report: flags byte + menus (branch addon/step1-flags-menus, 3 commits on 22a9c6d)

Image: /home/claude/work/out/step1_flags_menus.bin (+ .cue), 704,762,688 B (= baseline size), md5 61802fda54aace8953f040e518758772.
NOT RUN in any emulator (none in this container). Everything below is source reading + build artifacts.

## Changes
- mods/sotn-ultimate/include/game_mod.h: MOD_STATUS_FLAGS2 = g_Status.saveName[9]; MOD_FLAG2_ENDING_PSP 1, _SCRIPT_RETRANS 2, _SUBTITLES 4; MOD_ENDING_PSP(), MOD_SCRIPT_RETRANS(), MOD_SUBTITLES_ON().
- mods/sotn-ultimate/src/menu/2C048_mod_player_select.h: second page (rows Ending/Script/Subtitles) reached with X after the Dub row; DrawPanel refactored into ModCharselDrawRows (page 1 layout identical); commit writes FLAGS2.
- src/st/sel/32D6C.c: the ending's ApplySaveData path also preserves FLAGS2 (as it does FLAGS).
- mods/sotn-ultimate/src/menu/sysopt.c: 7 rows, table gets a flags2 selector, popup y 76 h 112, VALUE_DX 104, names Off/On/Default/Retrans.
- include/lba_us.h: ST_SEL_BIN_LEN (generated, tracked).
- No DRA code or data touched. gen_menu_text.py/check_menu_text.py cover DRA item/enemy text only; labels are inline _S() strings (same as existing rows), so nothing to generate. check_menu_text still OK.

## saveName[9] verification (source read)
Writers: SEL name entry func_801AD66C writes 0..7, zeroes 8 and 9 (so 0 before the Player Select sets it); all strcpy of names are 8 chars + NUL (byte 8 max): game_handlers.c, 32D6C.c, 3410C.c. Readers of saveName: 5F60C.c (cheat codes, bytes 0..7 / two words), 2C048.c staff check (0..7), memcard header Title (0..saveNameLen<=7). save_mgr.h converters copy saveName..statsFamiliars verbatim (retail/SAT1-4). info.name copies 0..9; SEL file list (32D6C.c:112 strcpy into name[10], 2C048.c:578 draws 0..7) stops at NUL in byte 8. InitStatsAndGear/Play_Reset never clear it (byte 10 holder item is cleared explicitly, 5F60C.c:308). Found and fixed one gap: 32D6C.c ending path reloads a card status and would have replaced the in-memory byte 9 with the card's. Not verified: BIOS memory card manager (uses Title only, so expected fine).

## Measurements
- MOD_DATA_PAD 64, MOD_DRA_PAD 40 (unchanged; DRA.BIN differs from baseline only in the 2-byte ST_SEL_BIN_LEN constant).
- SEL: ends 0x801dff58, 168 B free (baseline 552; -384). Dead 32,528 B blob NOT used (not needed; first attempt overflowed by 316 B before refactoring DrawPanel and caching MOD_CHARSEL_ROWS in a local, which also shrank ModCharselUpdate below baseline).
- sysopt: 2,520 B (baseline 2,344, +176), ARC_F2 free 6,712.
- Build: all checks OK, exit 0.

## Baseline comparison (cmp of images)
113 sectors differ: DRA 1 sector (SEL length constant), 2 file-table sectors (same constant), SEL.BIN and SELRIC2.BIN (menu code), ARC_F2.BIN (sysopt). Also BO2, BO6, RBO6, BO6RIC2: 2-3 instructions each `lw ...0x80097C0C` -> `0x80097C20` (+0x14, the status-layout shift for fields after saveName). The new value is what patch_status_asm.py intends; the baseline image appears to have had stale unshifted objects there (pre-existing baseline issue, not from this step; worth checking in an emulator: BO2/BO6 read a g_Status field there). Everything else is byte-identical. With flags2 = 0, no code reads it, so behaviour is as baseline.

## Tester checklist (emulator)
1. New game, each of Alucard/Richter/Maria: select panel shows page 1 as before (Alucard 4 rows, others 3); X on Dub goes to page 2 with Ending (PS1/PSP), Script (Default/Retrans), Subtitles (Off/On); Triangle walks back across pages; Start on any row starts; X on last row starts. Check look: 3-row panel position, text fit in tags ("Retrans", "Subtitles"), chains.
2. Start, save, reload; in-game System > Extra settings (Alucard): 7 rows in order Boss Richter, Boss Maria, Balance, Dub, Ending, Script, Subtitles; values match the choice made at new game; popup does not collide with the menu header (y 76..188) and values fit the box; toggling persists after closing and saving. Existing four rows (locks, dub reload) still work.
3. Save/load persistence of each flag for all three characters (Richter/Maria: new-game panel only; verify with a RAM view of saveName[9] if possible).
4. Memory card file list: names show correctly (8 chars, no stray glyph), BIOS card manager title unchanged.
5. Load a pre-v1.4-addon (v1.4) save: Alucard popup shows Ending PS1, Script Default, Subtitles Off.
6. Ending sequence / file-menu rename / copy: flags unchanged; game still plays normally.
7. Check BO2/BO6 area (see above).

## Weak points
Popup top y 76 not checked against the System window; "Retrans" label abbreviated for 8-px tag width; the info-bar text still says "Boss versions, game balance and voices"; the SEL margin is 168 B only.
