# SOTN Ultimate v1.4 - unmodified baseline build (measured)

Build host: cloud container, 2 cores / 7 GB, commit 22a9c6d ("v1.4 disc layout"), branch sotn-ultimate.
Reproduce with `/home/claude/work/env/setup.sh` section 8b. Log: `/home/claude/work/env/baseline-build.log`
(the last, incremental run; the first successful run is `baseline-build-run1.log`).
All numbers below are MEASURED from build artifacts unless marked (est.).

## 3a. Final image
- `build/sotn_ultimate.bin` = `/home/claude/work/out/sotn_ultimate_baseline.bin` (+ `.cue`, single track MODE2/2352)
- size **704,762,688 bytes** = **299,644 sectors** (x2352) -> identical to the v1.4 release size
- md5 **98ff3528c08fa9440d7afe50e8dca13e** -> does **NOT** match the release md5 901d74656aedbd8da3050d6a3716f32f
  (not diagnosed: no release image here to diff against). Two consecutive builds were byte-identical
  (cmp), so the build is deterministic on this machine; the difference is in inputs/toolchain/commit vs release.
  All of build_disc.sh's own checks pass (cd lba, DRA layout, sysopt/MARIA2 symbols, no dirt, stage data,
  psp dub, menu text, no compiler errors). `sha1sum -c config/check.us.sha` lists every modded file as differing
  from retail (expected, informational).
- Wall time: the successful `build_disc.sh` run = 6m49s (second, incremental run 6m38s). Total effort
  including the bootstrap/debug cycles was far longer (see "Bootstrap problems").

## 3b. DRA (build/us/dra.map, dra.elf, `check_dra_layout.sh`)
| item | value |
|---|---|
| MOD_DATA_PAD (src/dra/config_us.c) | **64** (README says 64: matches) |
| MOD_DRA_PAD (src/dra/42398.c) | **40** (README text says "currently 4": stale; the committed value is also 40, so the build reproduced it) |
| DRA.BIN size | 1,153,136 bytes (0x119870; includes the appended dra_data part) |
| dra_DATA_START / dra_DATA_END | 0x800A0000 / 0x800DB3B4 (retail, size 0x3B3B4) |
| sound_data .data | 0x800BD1E0 (retail) |
| dra_RODATA | 0x800DB3B4 - 0x800E2890 (0x74DC) |
| text start / end (dra_TEXT_START/END) | 0x800E2890 / 0x801362AC (0x53A1C = 342,556 bytes) |
| BSS start / end | 0x801362AC (retail) / 0x8013B6A0 (0x53F4 = 21,492 bytes) |
| gap BSS end -> 0x8013C000 | 0x8013C000 - 0x8013B6A0 = **0x960 = 2,400 bytes** |
| effective free DRA code/rodata room | only the pad: **40 bytes** (any growth >40 B in rodata/text before BSS needs dead code removed) |

Implication: the XA music config table (`g_ModXaMusicConfigs`, 16 B per entry, in rodata) is paid out of that
40-byte pad: adding 3 streams = at least 3 entries (48 B) -> pad -8 -> "DRA code grew past its pad" unless
>= 8 B (plus ModXaConfig/ModStageMusic changes) is freed elsewhere or the table is placed outside DRA.

### 40 largest DRA functions (size = address delta to next symbol; matches nm -S size where present; sum of all 642 functions = 342,556 = TEXT_SIZE)
| # | bytes | name | address |
|---|---|---|---|
| 1 | 7776 | `RunMainEngine` | 0x800f0464 |
| 2 | 7252 | `EntityPlayerBlinkWhite` | 0x8011a9d8 |
| 3 | 6596 | `EntityAlucard` | 0x801090bc |
| 4 | 6164 | `MenuHandle` | 0x800f9aa8 |
| 5 | 5504 | `RenderPrimitives` | 0x800ebd60 |
| 6 | 5228 | `EntityMist` | 0x801220e4 |
| 7 | 4960 | `UpdateCd` | 0x80106a88 |
| 8 | 4520 | `func_80105428` | 0x80103c34 |
| 9 | 4172 | `RenderEntities` | 0x800e9a30 |
| 10 | 4112 | `InitStatsAndGear` | 0x800fd7a8 |
| 11 | 3824 | `EntityStopWatch` | 0x8012a638 |
| 12 | 3464 | `DrawRichterHudSubweapon` | 0x800ff2d8 |
| 13 | 3452 | `AlucardHandleDamage` | 0x80112ce0 |
| 14 | 3396 | `func_8010EDB8` | 0x8010d9dc |
| 15 | 3244 | `ControlBatForm` | 0x80115774 |
| 16 | 3188 | `HandleSaveMenu` | 0x80101a5c |
| 17 | 3128 | `PlayerStepStand` | 0x80110a1c |
| 18 | 2992 | `EntityPlayerDissolves` | 0x80120b98 |
| 19 | 2652 | `DrawHudSubweapon` | 0x801002a4 |
| 20 | 2636 | `EntityTransparentWhiteCircle` | 0x8011fe74 |
| 21 | 2512 | `func_8012F894` | 0x8012f630 |
| 22 | 2332 | `RenderTilemap` | 0x800eacdc |
| 23 | 2280 | `func_80104790` | 0x80102f9c |
| 24 | 2276 | `func_8011E4BC` | 0x8011e284 |
| 25 | 2244 | `EntityGiantSpinningCross` | 0x80131394 |
| 26 | 2228 | `HandlePlay` | 0x800e3d80 |
| 27 | 2184 | `MenuDraw` | 0x800f6bdc |
| 28 | 2172 | `EntityNumberMovesToHpMeter` | 0x80117978 |
| 29 | 2160 | `StoreSaveData` | 0x800e7780 |
| 30 | 2112 | `func_80129864` | 0x80129600 |
| 31 | 2076 | `PlayerStepKill` | 0x80113ffc |
| 32 | 2060 | `func_800FB23C` | 0x800f9040 |
| 33 | 2056 | `PlayerStepCrouch` | 0x80111e48 |
| 34 | 2032 | `CheckStageCollision` | 0x80108544 |
| 35 | 2004 | `EntitySubwpnReboundStone` | 0x80127cdc |
| 36 | 2004 | `WolfStepS_2` | 0x8012d184 |
| 37 | 1960 | `EntitySubwpnKnife` | 0x80124950 |
| 38 | 1948 | `CheckCollision` | 0x800ed2e0 |
| 39 | 1944 | `EntityGuardText` | 0x801181f4 |
| 40 | 1912 | `HandleNowLoading` | 0x800e5518 |

### Mod-specific symbols (Mod* / g_Mod*), 53 symbols
Functions have exact `nm -S` sizes ("sized"). Data symbols have no ELF size: "delta" = distance to the next
symbol, an UPPER BOUND (e.g. g_ModRainbowCapePal 12,668 swallows following unnamed rodata).
Exact: g_ModDub = 4096 (struct), g_ModDraPad = 40, g_ModDataPad = 64, g_ModXaMusicConfigs = 22 x 16 = 352.
| bytes | basis | address | sym | name |
|---|---|---|---|---|
| 12668 | delta | 0x800dc664 | T | `g_ModRainbowCapePal` |
| 4628 | delta | 0x800e0dc0 | t | `g_ModPspServantSfx` |
| 4096 | delta | 0x8013644c | T | `g_ModDub` |
| 2096 | delta | 0x800db3dc | t | `g_ModBalance` |
| 1208 | delta | 0x800dbc0c | t | `g_ModEmptySlot` |
| 1080 | delta | 0x800e2170 | t | `g_ModPspXa` |
| 904 | sized | 0x8011d544 | t | `ModBottomCornerText` |
| 712 | sized | 0x8011d27c | T | `ModHolderUse` |
| 544 | sized | 0x800e7560 | t | `ModStoreRetailStatus` |
| 496 | sized | 0x80131cc4 | t | `ModXaConfig` |
| 428 | sized | 0x800e8278 | t | `ModRainbowCape` |
| 380 | sized | 0x8011d8cc | t | `ModFoodCaught` |
| 372 | sized | 0x80105900 | t | `ModRicCostumeApply` |
| 356 | sized | 0x8011da48 | t | `ModFoodDraw` |
| 352 | delta | 0x800e1fd4 | t | `g_ModXaMusicConfigs` |
| 292 | sized | 0x800e3bc4 | t | `ModApplyBalance` |
| 272 | sized | 0x8011dbfc | t | `ModFoodGot` |
| 200 | sized | 0x800fc200 | T | `ModGetFamiliarStats` |
| 192 | sized | 0x80131f20 | T | `ModPauseCd` |
| 176 | sized | 0x800fc2c8 | T | `ModSetFamiliarStats` |
| 176 | sized | 0x800f03b4 | T | `ModStageMusic` |
| 156 | sized | 0x8011d1e0 | t | `ModHolderReduce` |
| 152 | sized | 0x800e3ce8 | t | `ModApplyDubText` |
| 148 | sized | 0x801057fc | t | `ModJpSfx` |
| 132 | sized | 0x8011d0f0 | T | `ModHolderAllows` |
| 112 | sized | 0x80105890 | t | `ModMarSfxPrio` |
| 108 | sized | 0x80131c58 | t | `ModXaIndex` |
| 100 | delta | 0x800b012c | t | `g_ModSpearWindup` |
| 88 | sized | 0x800fc378 | T | `ModCountFamiliarSummon` |
| 88 | delta | 0x800e0d68 | t | `g_ModMarSfxPrio` |
| 80 | sized | 0x8011dbac | t | `ModFoodEat` |
| 80 | sized | 0x800f2314 | t | `ModEquipSlot` |
| 80 | sized | 0x800f22c4 | t | `ModEquipRow` |
| 64 | delta | 0x800ac824 | T | `g_ModDataPad` |
| 60 | sized | 0x8011d1a4 | T | `ModHolderItem` |
| 60 | delta | 0x800e2134 | t | `g_ModPspXaBits` |
| 48 | sized | 0x8011d174 | T | `ModHolderOn` |
| 48 | sized | 0x8010f1d0 | t | `ModCastStep` |
| 40 | delta | 0x800db3b4 | T | `g_ModDraPad` |
| 36 | sized | 0x800e753c | t | `ModMarkSave` |
| 36 | delta | 0x800ac800 | t | `ModSysOptGo` |
| 24 | sized | 0x800fc1e8 | t | `ModFamiliarBytes` |
| 24 | delta | 0x800dc64c | t | `g_ModGlaringCapePal` |
| 16 | delta | 0x800ac7e4 | T | `ModSysOptBox` |
| 16 | delta | 0x800ac7d4 | T | `ModSysOptSound` |
| 12 | delta | 0x800b019c | t | `g_ModSpearAnim248` |
| 12 | delta | 0x800b0190 | t | `g_ModSpearAnim247` |
| 12 | delta | 0x800ac7f4 | T | `ModSysOptInput` |
| 8 | delta | 0x800dc644 | t | `g_ModGlaringCapeB` |
| 8 | delta | 0x800dc63c | t | `g_ModGlaringCapeA` |
| 4 | delta | 0x800dc0c4 | t | `g_ModHolderStr` |
| 4 | delta | 0x800a2f10 | T | `g_ModSubwpnIcons` |
| 4 | delta | 0x800a2dec | T | `g_ModMar2HudIcons` |
Sum of exact function sizes (sized rows): 6,852 bytes of DRA code (sized function rows); data/rodata mod symbols as above.

## 3c. ARC_F2 / sysopt (`build_sysopt.sh` output, `build/us/mod/sysopt`)
- sysopt code: **2,344 bytes** at 0x8016DBF0 (file offset 0x31BF0), range 0x8016DBF0 - 0x8016E518
- ARC_F2.BIN = 212,992 bytes (0x34000) loaded at 0x8013C000, up to 0x80170000
- free below 0x80170000: 0x80170000 - 0x8016E518 = **6,888 bytes** (build log: "ARC_F2.BIN free 6888")
- retail ARC_F.BIN is 0x31BEC bytes; 18 DRA symbols checked against it.

## 3d. SEL
- SEL.BIN 392,664 bytes; overlay ends at 0x801DFDD8 (BSS included); limit 0x801E0000 -> **552 bytes free**
- dead config table copy (`src/st/sel/config_us.c`): `.incbin` of retail SEL.BIN 0x25FC..+0x7F10 =
  **0x7F10 = 32,528 bytes** of .data at 0x801825FC-0x8018A50C, referenced by nothing. Its strings (~15 KB rodata)
  are already dropped. The bytes stay because SEL's data section must keep retail addresses; reclaiming them
  needs a relink of everything after it (checker "data section matches retail" would have to be relaxed).

## 3e/3f. Stage / boss / servant overlays (maps: build/us/*.map and build/us/mod/*/*.map)
"end" = <name>_BSS_END from the linker map (data+text+BSS), limit 0x801E0000 (check_stage_data.py).
Tightest: NO4 280, NO3 456, NO0 784, SEL 552 bytes free; TE1 (Underground Garden) 7,564; RNO4 8,108; DAI 18,044.

| overlay | file | file bytes | load | end (incl. BSS) | limit | free bytes |
|---|---|---|---|---|---|---|
| bobo0 | BO0.BIN | 321,136 | 0x80180000 | 0x801CE670 | 0x801E0000 | 72080 |
| bobo1 | BO1.BIN | 205,944 | 0x80180000 | 0x801B2478 | 0x801E0000 | 187272 |
| bobo2 | BO2.BIN | 224,720 | 0x80180000 | 0x801B6DD0 | 0x801E0000 | 168496 |
| bobo3 | BO3.BIN | 210,568 | 0x80180000 | 0x801B3688 | 0x801E0000 | 182648 |
| bobo4 | BO4.BIN | 347,892 | 0x80180000 | 0x801D4EF4 | 0x801E0000 | 45324 |
| bobo5 | BO5.BIN | 220,068 | 0x80180000 | 0x801B5BA4 | 0x801E0000 | 173148 |
| bobo6 | BO6.BIN | 336,004 | 0x80180000 | 0x801D2084 | 0x801E0000 | 57212 |
| bobo7 | BO7.BIN | 144,668 | 0x80180000 | 0x801A351C | 0x801E0000 | 248548 |
| bomar | MAR.BIN | 111,612 | 0x80180000 | 0x8019B3FC | 0x801E0000 | 281604 |
| borbo0 | RBO0.BIN | 161,176 | 0x80180000 | 0x801A7598 | 0x801E0000 | 232040 |
| borbo1 | RBO1.BIN | 139,292 | 0x80180000 | 0x801A201C | 0x801E0000 | 253924 |
| borbo2 | RBO2.BIN | 191,716 | 0x80180000 | 0x801AECE4 | 0x801E0000 | 201500 |
| borbo3 | RBO3.BIN | 132,844 | 0x80180000 | 0x801A06EC | 0x801E0000 | 260372 |
| borbo4 | RBO4.BIN | 154,848 | 0x80180000 | 0x801A5CE0 | 0x801E0000 | 238368 |
| borbo5 | RBO5.BIN | 345,284 | 0x80180000 | 0x801D44C4 | 0x801E0000 | 47932 |
| borbo6 | RBO6.BIN | 216,184 | 0x80180000 | 0x801B4C78 | 0x801E0000 | 177032 |
| borbo7 | RBO7.BIN | 142,760 | 0x80180000 | 0x801A2DA8 | 0x801E0000 | 250456 |
| borbo8 | RBO8.BIN | 161,400 | 0x80180000 | 0x801A7678 | 0x801E0000 | 231816 |
| stare | ARE.BIN | 352,824 | 0x80180000 | 0x801D6238 | 0x801E0000 | 40392 |
| stcat | CAT.BIN | 362,260 | 0x80180000 | 0x801D8714 | 0x801E0000 | 30956 |
| stcen | CEN.BIN | 273,104 | 0x80180000 | 0x801C2AD0 | 0x801E0000 | 120112 |
| stchi | CHI.BIN | 193,764 | 0x80180000 | 0x801AF4E4 | 0x801E0000 | 199452 |
| stdai | DAI.BIN | 375,172 | 0x80180000 | 0x801DB984 | 0x801E0000 | 18044 |
| stdre | DRE.BIN | 151,072 | 0x80180000 | 0x801A4E20 | 0x801E0000 | 242144 |
| stlib | LIB.BIN | 352,112 | 0x80180000 | 0x801D5F70 | 0x801E0000 | 41104 |
| stmad | MAD.BIN | 106,132 | 0x80180000 | 0x80199E94 | 0x801E0000 | 287084 |
| stno0 | NO0.BIN | 392,432 | 0x80180000 | 0x801DFCF0 | 0x801E0000 | 784 |
| stno1 | NO1.BIN | 356,640 | 0x80180000 | 0x801D7120 | 0x801E0000 | 36576 |
| stno2 | NO2.BIN | 327,316 | 0x80180000 | 0x801CFE94 | 0x801E0000 | 65900 |
| stno3 | NO3.BIN | 392,760 | 0x80180000 | 0x801DFE38 | 0x801E0000 | 456 |
| stno4 | NO4.BIN | 392,936 | 0x80180000 | 0x801DFEE8 | 0x801E0000 | 280 |
| stnp3 | NP3.BIN | 369,740 | 0x80180000 | 0x801DA44C | 0x801E0000 | 23476 |
| stnz0 | NZ0.BIN | 310,540 | 0x80180000 | 0x801CBD0C | 0x801E0000 | 82676 |
| stnz1 | NZ1.BIN | 271,576 | 0x80180000 | 0x801C24D8 | 0x801E0000 | 121640 |
| strare | RARE.BIN | 234,572 | 0x80180000 | 0x801B944C | 0x801E0000 | 158644 |
| strcat | RCAT.BIN | 278,376 | 0x80180000 | 0x801C3F68 | 0x801E0000 | 114840 |
| strcen | RCEN.BIN | 188,120 | 0x80180000 | 0x801ADED8 | 0x801E0000 | 205096 |
| strchi | RCHI.BIN | 175,068 | 0x80180000 | 0x801AABDC | 0x801E0000 | 218148 |
| strdai | RDAI.BIN | 295,924 | 0x80180000 | 0x801C83F4 | 0x801E0000 | 97292 |
| strlib | RLIB.BIN | 201,964 | 0x80180000 | 0x801B14EC | 0x801E0000 | 191252 |
| strno0 | RNO0.BIN | 349,388 | 0x80180000 | 0x801D54CC | 0x801E0000 | 43828 |
| strno1 | RNO1.BIN | 229,788 | 0x80180000 | 0x801B819C | 0x801E0000 | 163428 |
| strno2 | RNO2.BIN | 314,032 | 0x80180000 | 0x801CCAB0 | 0x801E0000 | 79184 |
| strno3 | RNO3.BIN | 336,136 | 0x80180000 | 0x801D2108 | 0x801E0000 | 57080 |
| strno4 | RNO4.BIN | 385,108 | 0x80180000 | 0x801DE054 | 0x801E0000 | 8108 |
| strnz0 | RNZ0.BIN | 281,728 | 0x80180000 | 0x801C4C80 | 0x801E0000 | 111488 |
| strnz1 | RNZ1.BIN | 261,148 | 0x80180000 | 0x801BFC1C | 0x801E0000 | 132068 |
| strtop | RTOP.BIN | 201,176 | 0x80180000 | 0x801B11D8 | 0x801E0000 | 192040 |
| strwrp | RWRP.BIN | 109,592 | 0x80180000 | 0x8019AC18 | 0x801E0000 | 283624 |
| stsel | SEL.BIN | 392,664 | 0x80180000 | 0x801DFDD8 | 0x801E0000 | 552 |
| stst0 | ST0.BIN | 273,436 | 0x80180000 | 0x801C2C1C | 0x801E0000 | 119780 |
| sttop | TOP.BIN | 251,372 | 0x80180000 | 0x801BD5EC | 0x801E0000 | 141844 |
| stwrp | WRP.BIN | 101,528 | 0x80180000 | 0x80198C98 | 0x801E0000 | 291688 |
| stgdn | TE1.BIN | 385,652 | 0x80180000 | 0x801DE274 | 0x801E0000 | 7564 |
| stprs | TE2.BIN | 174,500 | 0x80180000 | 0x801AA9A4 | 0x801E0000 | 218716 |
| strgdn | TE3.BIN | 313,128 | 0x80180000 | 0x801CC728 | 0x801E0000 | 80088 |
| strprs | TE4.BIN | 204,844 | 0x80180000 | 0x801B202C | 0x801E0000 | 188372 |

| servant | file bytes | load | end (incl. BSS) | slot end | used of 0xA000 | free |
|---|---|---|---|---|---|---|
| TT_000 | 40,960 | 0x80170000 | 0x80174D44 | 0x8017A000 | 19780 | 21180 |
| TT_001 | 40,960 | 0x80170000 | 0x80173824 | 0x8017A000 | 14372 | 26588 |
| TT_002 | 40,960 | 0x80170000 | 0x80179344 | 0x8017A000 | 37700 | 3260 |
| TT_003 | 40,960 | 0x80170000 | 0x801786E4 | 0x8017A000 | 34532 | 6428 |
| TT_004 | 40,960 | 0x80170000 | 0x80178B8C | 0x8017A000 | 35724 | 5236 |
| TT_005 | 40,960 | 0x80170000 | 0x801792DC | 0x8017A000 | 37596 | 3364 |
| TT_006 | 40,960 | 0x80170000 | 0x80178198 | 0x8017A000 | 33176 | 7784 |


Servant overlays: slot 0xA000 at 0x80170000 (end 0x8017A000). Tightest: TT_002 3,260 and TT_005 3,364 bytes free.
(File size is always 40,960 = padded slot; "used" is BSS_END - load.)

## 3g. g_ModDub (include game_mod.h ModDubState, DRA BSS 0x8013644C, 4096 B)
cfg 16 + jp table 1,208 (magic/xaBase/didYouNot 12, sfx 112, xaBits 60, xa[256] 1,024) + text 648
(count/magic 8, 16 x 16 entries = 256, bytes 384) + fixedText 768 + storeSave 4 = **2,644 bytes used, 1,452 unused**
(sizes computed from the struct definition by hand, not from a compiled sizeof; total matches the 0x1000 map span).

## 3h. XA
- Retail config table: 563 entries (`MOD_XA_RETAIL_CONFIGS`), cannot grow (g_SfxScripts follows).
- Mod table `g_ModXaMusicConfigs`: 22 entries (10 Saturn tracks x 2 [intro + loop] + 1 PSP one-shot Nocturne
  EN + 1 extra for MOD_VO_DID_YOU_NOT, ids 0x533-0x548); `MOD_XA_CONFIGS` = 22. repack_xa totals: 583 music configs,
  1068 configs incl. PSP/JP dub copies, all verified.
- ID capacity (est.): sound ids 0x549-0x5FF are unused by sfx.h (first SFX id is 0x601), and sound.c routes
  `0x300 < id < 0x300+563+MOD_XA_CONFIGS` to XA, so ~183 more config ids are available by id space. The real
  limit is the 40-byte DRA pad above (16 B per config).
- XA_STR1: retail 181,328 sectors; unpacked intermediate 287,088 sectors (retail + 105,760 Saturn/PSP sectors);
  **final packed XA_STR1 = 247,056 sectors (581,075,712 bytes, 581.1 MB)**, 40,032 saved by repack
  (dual-mono -> mono 6,756, silent JP lines 3,568, filler). PSP dub 9,229 sectors, JP dub 11,182.
- gen_saturn_music.py slots: files 100+ , 8 channels per file, 2 files = 16 streams max (`assert len(TRACKS)+len(ONESHOTS) <= 16`).
  Used 11 (10 TRACKS + 1 ONESHOT), **5 free**; adding 3 -> 14/16. File 101 holds slots 8-15 (now SD2D, SD28, Nocturne);
  its region is 8 x the longest member (SD2D, ~297.5 s) so a 4:38 (278 s) stream fits without growing the region (est.).
- Size estimate for the 3 streams in the final image (est.): stereo 37.8 kHz = 18.75 sectors/s per stream:
  4:38 song ~5,213 sectors (12.3 MB); 105 s narration ~1,969 sectors stereo or ~984 mono (2.3 / 1.2 MB) each
  -> +7.2k to +9.2k sectors. Image is 299,644 sectors = 66.6 min of an 80-min (360,000) disc: ~60k sectors headroom (est., media limit not enforced by the build).

## 3i. "I Am the Wind" (PS1 US ending/credits song)
- Name confirmed by the mod's own Sound Mode list: `{_S("I Am the Wind"), MU_STAFF_CREDITS}` (2C048_mod_player_select.h).
  SEL plays `g_api.PlaySfx(MU_STAFF_CREDITS)` in 34B30.c func_801B60D4 case 4 (STAFF path).
- MU_STAFF_CREDITS = sfx id 0x33C -> XA config index 0x3C (60). Retail config (from disks/us/DRA.BIN @0x800BD224+16*60):
  cd_addr 0x21DE8, timer unk228 = 0x41B0 = 16,816 VSyncs, XA file 0x1E channel 5, volume 0x48, mode 2 (one-shot).
- Duration, two independent ways (MEASURED): (1) timer 16,816 / 59.94 Hz = 280.5 s (280.3 s at 60 Hz; 281.1 at the
  mod's 59.80 Hz VSYNC_HZ constant); (2) counting retail XA_STR1 sectors with file 0x1E / channel 5: 5,255 sectors, CD-XA stereo
  37.8 kHz 4-bit (coding 0x01) = 2016 samples/sector -> 5,255 x 2016/37800 = **280.27 s = 4:40**.
  So the PS1 song is 4:40 (not 4:38 - a Saturn/PSP 4:38 song is 2 s shorter than the PS1 slot).

## Bootstrap problems found (all environment/workflow, no source changes made)
1. ~/.bashrc line 6 `[ -z "$PS1" ]` aborts under `set -u` (build_disc.sh sources ~/.profile): patched to `${PS1:-}`.
2. psp_dub.py needs `NODE` as an absolute path (os.path.exists("node") is False).
3. Fresh clone is circular: gen_prs_links needs src/st/*/gen (from a prior `./sotn.sh build us`), which needs
   tools/sotn_str (cargo build); the C compile `sotn_str | cc1 | as` pipe hides failures and leaves EMPTY .o files
   (symptom: undefined reference to PlaySfx/g_ModRooms...) -> `rm -rf build/us/src` after generated headers exist.
4. gen_np3_sconce.py needs build/us/st{np3,no3,rno3}.map first: worked around with an empty stub mod_sconce.h link (removed afterwards).
5. bin/satxa (gcc of satxa.c) is needed by gen_no3_sounds/gen_psp_grunts before gen_saturn_music builds it.
6. gen_mar_assets.py needs src/saturn/*/gen headers: `./sotn.sh extract-assets` + `build-assets config/assets.saturn.yaml`.
7. build_cenp.sh uses gawk `strtonum`; Ubuntu's mawk printed "function strtonum never defined" and silently skipped the
   CEN-data-symbol check; installed gawk, rebuilt, check passes (no output change).
8. Saturn disc: 7z reports "Data Error : CD3" (0-byte CD-DA marker file) - harmless, 290 files extracted.
9. The `emsdk` fake and partial audio output were deleted; real emsdk 4.0.10 audio_core.js built in 1m31s.
