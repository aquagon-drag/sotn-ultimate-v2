# Test build: ending shortcut (branch test/ending-shortcut, from addon/step2-psp-ending b100f17)

Image: /home/claude/work/out/test_ending_shortcut.bin (+ .cue), same size as step 2 (304,764 sectors).
Patch: /home/claude/work/out/test_ending_from_step2.secpatch, 87 sectors, 204,972 B (4-byte LE sector index + 2352 bytes each).
NOT run in an emulator (none here). Everything below is from reading source/asm and build checks.

## What the switch does (MOD_TEST_ENDING_SHORTCUT, mods/sotn-ultimate/include/game_mod.h, defined on this branch)
SEL's file menu load (src/st/sel/2C048.c): when a file is chosen (Upd_Eng_0x100) it latches whether L1+R1 are held;
when the card load finishes (Upd_Eng_257, after ApplySaveData) and the latch is set and the save is Alucard's, it:
- sets g_StageId = STAGE_RBO6 and room (left,top) = (0x1F,0x1E): the Dracula room, the arrival of teleport 0x08
  (RCEN -> Dracula; D_800A245C[8], roomId 0x10 = room index 2 of RBO6). The file-load path (D_8003C730 = 1) puts Alucard at
  x 0x80, y 0xB4 of that room (the teleport uses 0xB3).
- castle flags SHAFT_ORB_DEFEATED = INVERTED_CASTLE_UNLOCKED = 1 (the good route's state, same as the Library-card test chain).
- max stats: HP 9999/9999, MP 99, hearts 999, level 99, exp 99999999, STR/CON/INT/LCK base 99 (total = 99 + equip).
- g_api.enemyDefs[0x17B Dracula Lv98]: HP 10000 -> 1, defense 18 -> 0 (runtime poke of DRA's table, no DRA change).
Without L1+R1 the load is completely normal (so the save room stays reachable to flip options and save).
Nothing is written to the card by the hook (it is not inside ApplySaveData, so the ending's card reload does not re-apply it).
The Ending option is the save's own (saveName[9] is untouched).

## Why this fight and which ending
Alucard's final boss is Dracula in RBO6 (Dracula Lv98, enemy 0x17B, entity 0x17 = func_us_8019DB9C). Shaft (RCEN) only leads there.
Dracula's FLAG_DEAD sends any step to step 0xC; its cutscene ends in entity 0x31 (func_us_801A4594) which sets
D_800978B4 = 5 if g_RoomCount < 0x737 else 3, g_GameState = Game_Ending. The save-room save has far fewer rooms, so ending type 5
(SEL ending script index 4) results; it needs no relic check. Then DRA HandleEnding -> SEL ending cutscene (plays 0x33C through the
script op, MOD_ENDING_SONG swaps it) -> credits -> StageEndCutScene (func_801B17C8) reloads the card save (arg 1 marks it cleared).
Real code path throughout, including the SEL card reload (which preserves FLAGS/FLAGS2 of the memory, step 1).

## Where the code lives (SEL space)
SEL grew only by the two call sites: 40 bytes free below 0x801E0000 (was 56), ends 0x801dffd8. ST_SEL_BIN_LEN +0x10 (generated).
The hook (0x160 bytes: latch word + code) replaces the first 0x160 bytes of SEL's dead copy of DRA config tables (config_us.c).
Deadness check: no word in SEL.BIN outside the region holds an address inside it and no lui+load/store/addiu pair resolves into it
(scan of the built SEL.BIN; the 6 raw hits were false positives: unrelated lui reuse, odd values). The .data of config_us.o is still 0x7F10.
This cc1 ignores a function's section attribute, so the function is the cc1 -O2 output embedded as top-level asm (C source kept under #if 0).
Check change (test branch only): mods/sotn-ultimate/tools/check_stage_data.py skips those 0x160 bytes of stsel when symbol ModTestEnding exists.
Other checks unchanged and passing: MOD_DRA_PAD 24, MOD_DATA_PAD 64, dra_DATA_END 0x800db3b4, DRA.BIN matches dra.elf, no compiler errors.

## Tester steps (both option values)
1. Load the memory-card save normally (no buttons), you are in the first save room. System menu -> Ultimate settings: set Ending = PS1; save at the crystal (or skip: the save's current value is used). Repeat later with PSP.
2. Back at the title: Load game, choose the file with X while HOLDING L1+R1, keep holding until the screen fades out.
3. You arrive in the inverted castle's Dracula room (no save room). Dracula's intro dialogue plays (it can be skipped as usual); the fight begins; hit him once with anything. He dies, the dialogue/fade runs, then the ending cutscene and credits.
4. Listen to the credits song: "I Am the Wind" (PS1) or "Mournful Serenade" (PSP). Repeat 1-3 with the other value. After the ending the card file is marked cleared (retail behaviour) but is otherwise unchanged; it can be reloaded with L1+R1 again.
The Ending option cannot be changed inside the Dracula room before the fight (cutscene/boss room, menu not reachable as far as source shows); flip it in step 1.

## Not verifiable here / doubts
- Nothing was run: the stage load of RBO6 from a file load, Dracula's HP poke taking effect, one-hit kill, and the song heard are unproven.
- Room (0x1F,0x1E) as the Dracula room is inferred from the teleport table (roomId 0x10) and the Library-card chain's "Dracula + good ending" stop (teleport 0x08), not from the room's entity layout.
- Dracula may need a cutscene trigger flag not set by the loaded state (unknown; the card chain sets only INVERTED_CASTLE_UNLOCKED for it).
- If the hit does 0 damage (weapon attack 0), nothing dies; stats are set on the base values only (make_all may recompute totals).
- That the credits (0x33C) play in ending-5's script was not individually traced (every ending script group has the op).
- L1+R1 must still be held when the load finishes; releasing early gives a normal load (harmless, retry).
- Because the ending reload uses the card's copy, the in-memory vs card flag survival is not distinguishable here (both equal).
