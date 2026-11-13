# SOTN Ultimate v1.4: source architecture analysis for the six new features

Scope: read-only analysis of `/home/claude/work/sotn-ultimate`, a shallow clone with no `disks/` content and no `build/`. Every size below that depends on a build is an estimate and is marked as one. Paths are relative to the repo root unless they are absolute. "MOD/" means `mods/sotn-ultimate/`.

Confidence tags: **[H]** read directly in the source. **[M]** inferred from the source but not proven. **[L]** a guess or outside knowledge, to be verified on the discs or in an emulator.

---

## 0. Cross-cutting constraints (read this first)

### 0.1 DRA is full
- The data must stay where it is: `sound_data.c` .data at `0x800BD1E0`, `dra_DATA_END` at `0x800DB3B4` and `dra_BSS_START` at `0x801362AC`. `MOD/tools/check_dra_layout.sh` checks all three. **[H]**
- `MOD_DRA_PAD` is the code/rodata slack. The README says 4. The committed `src/dra/42398.c:265` holds **40**. `build_disc.sh` rewrites this value on every build, so the real slack is only known after a build. **[H]**
- `MOD_DATA_PAD` is the data slack. `src/dra/config_us.c:6` holds 64. The sysopt stubs already live in DRA *data* (`src/config_us.h` ~l.300-330, written as raw `.word`s). **[H]**
- **Rule for every feature below: put no new logic in DRA.** Code goes in SEL, in the stage or servant overlays, or in the ARC_F2 code region. DRA keeps only data that SEL writes, plus pointer swaps.

### 0.2 RAM regions the mod already uses
| Region | Size | Who | Notes |
|---|---|---|---|
| `g_ModDub` (`0x8013644C`, DRA BSS, the dead sim VSync buffers) | 4096 B | JP dub tables, dub text, fixedText, storeSave | Free space by my arithmetic: cfg 16 + ModJpDubTable 1208 + ModDubText 648 + fixedText 768 + 4 = 2644, so about **1452 B unused** (`MOD/include/game_mod.h:329-342`). [M]: alignment and padding could shift this a little. |
| ARC_F2 code (`0x8016DBF0`-`0x80170000`) | 9232 B max | sysopt.c | **Alucard games only.** For Richter and Maria, their player file occupies this RAM (`build_sysopt.sh`). Current sysopt size needs a build: `build_disc.sh` prints "ARC_F2.BIN free N". [L] estimate 1.5-3 KB used. |
| SEL data `.incbin SEL.BIN 0x25FC..+0x7F10` | 32 528 B | **dead**: SEL's unused copy of DRA's tables (`src/st/sel/config_us.c:4-12`) | The bytes must keep their *size*, but nothing reads their *content*. This is a free blob inside SEL. **[H]** for "no SEL code refers" (author's comment). Re-verify with a map/xref scan. |
| `0x801E8000` (DEMO_KEY_PTR, `include/game.h:291`) | 8 KB | demo playback only | A candidate for resident text. **[L]**: confirm with a write breakpoint in an emulator that nothing writes it during play. |

### 0.3 Persistent option bits
- `g_Status.saveName[11]` (`MOD_STATUS_FLAGS`, `MOD/include/game_mod.h:173`). Used bits: 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40. **Only 0x80 is free. Verified [H]**: every writer is listed at `2C048_mod_player_select.h:846-868`, `2C048.c:1332`, `sysopt.c:271`, `mar2.c:372`, `2C048_mod_player_select.h:1014,1183` (the sound mode temporarily clears and sets the dub bits) and `32D6C.c:428-438`.
- Overloading the per-character bits is **unsafe**. For example, `MOD_MARIA_PSP()` (bit 0x02) has no player check and is read by the drop rule `MOD_MARIA_PSP_NO_SUBWPN` (`game_mod.h:184-190`).
- **Proposed second flags byte: `g_Status.saveName[9]`. [M]**
  - Name entry writes bytes 0-7 and zeroes 8 and 9 (`src/st/sel/2C048.c:762-774`).
  - Every `strcpy` of a name is 8 characters plus the NUL, so it writes byte 8 at most (`game_handlers.c:527,531,1425,1439,1444`, `32D6C.c:414,435`).
  - The save converters copy saveName..D_80097C40 as is (`src/save_mgr.h:627-630,745-748`).
  - The card header copies bytes 0-9 into `info.name` (`src/save_mgr.h:928-930`). The file list stops at the NUL at byte 8. That is [M]: check that the SEL file list and the BIOS card manager never print past the NUL.
  - Result: 8 new bits that SEL can set at new game, plus 0x80 in byte 11.
- Castle flags 0x2F9-0x2FF are free but are **cleared at new game in DRA** (`src/dra/game_handlers.c:431`, Play_Reset), after SEL. SEL therefore cannot pre-set them. Only in-game code (sysopt) could use them, so they are not suitable for new-game choices.
- `ModSaveExtra` is exactly full (20/20 B, `src/save_mgr.h:663-675`).

Proposed allocation:
- `saveName[11]` 0x80 = `MOD_FLAG_RT_SCRIPT` (retranslation text, font and JP banners).
- `saveName[9]` bit 0x01 = `MOD_FLAG2_PSP_ENDING`.
- `saveName[9]` bits 0x02-0x80 are reserved for later (subtitles on/off, JP narration on/off).

### 0.4 Menus that must carry the toggles
**SEL Player Select panel** (`MOD/src/menu/2C048_mod_player_select.h`):
- Rows are fixed code, not a table: version, [Alucard: Boss Maria], Balance, Dub (`MOD_CHARSEL_ROWS(id)` l.122). Drawing is at l.701-737 and commit at l.835-868.
- The vertical space is already tight. Four rows use `MOD_CHARSEL_ROW_H4 35` (l.550) so the panel fits between the header and the hint bar. **Six rows (adding Ending and Script) will not fit [M].** The panel needs a redesign: either a second panel page ("More options" after the Dub row), or two compact rows sharing one line, or the new options moved to the main menu as a separate "Options" screen next to the Sound mode button.
- The SEL size headroom is unknown without a build. It is not checked by any script I found. The SEL relink also feeds `build_selric2.py` and psp_script `--apply`.

**In-game System popup** (`MOD/src/menu/sysopt.c`):
- Rows are a table `g_SysOptRows` (l.104-118). `ROWS 4`. The popup box is `POP_X/Y/W/H 172/124/168/64` (l.88-94). It ends at y 188, and the info bar starts at 193.
- Six rows need `POP_H` ≈ 96+, so `POP_Y` must move up to about 92. **[M]** The right half of the System screen above y 124 appears free. Check on screen.
- **It exists only in Alucard games.** Richter and Maria games cannot get an in-game toggle unless the code finds another home. Their player files fill 0x8013C000-0x80175A58 (RIC.BIN is 0x39A58 B), so no free RAM is known there. This is a **hard limitation** to flag to the user.
- Changing the script mid-game also needs the in-game text swap (§4), which needs its code and data resident. Another reason it only works in Alucard games.

### 0.5 What text-drawing primitives overlays have
- No `g_api` text routine. Stage overlays have their own static copies of `BottomCornerText` (`src/st/popup.h`), `BlitChar` (`src/st/blit_char.h`, BIOS Kanji ROM via `g_api.func_80106A28`) and the cutscene dialogue renderer.
- SEL has `DrawImages8x8` and the mod's `ModCharselTextRGB`.
- The 8x8 font sheet sits in VRAM at **x 896 (0x380), y 240**, 4bpp, 16 glyphs per row. Glyph = `(c&0xF)*2+896, ((c&0xF0)>>1)+240` (for example `src/st/st0/cutscene.c:685-690`). **[H]**
- That sheet is uploaded from `F_GAME.BIN` (Alucard) or `F_GAME2.BIN` (Richter, Maria, and ST0) through `CdFile_GameChr` (`src/dra/cd.c:796-804`). The cd.c redirect is [H]. That the font is inside F_GAME is [M], inferred from the VRAM area that F_GAME fills.
- `g_PrimBuf` holds `MAX_PRIM_COUNT 0x500` prims (`include/game.h:240`). A 30-character subtitle costs 30 SPRT prims plus 1-2 box prims.

---

## 1. PSP ending theme (with a toggle)

**Facts [H]**
- The PS1 ending vocal is `MU_STAFF_CREDITS` (0x33C, "I Am the Wind"). SEL plays it in two places:
  - the normal ending, through the ending **cutscene script's PLAY_SOUND op**: `src/st/sel/cutscene.c:296,385` call `g_api.PlaySfx(nextChar)`. The script data comes from `assets/st/sel/cutscene_endings.yaml`, and its PSP copy is made by psp_script.py (overlay "sel").
  - the "STAFF" credits-only path: `src/st/sel/34B30.c:851-853`.
- New music already has a path: `MOD/tools/gen_saturn_music.py` **ONESHOTS** (l.107-110). This encodes a PSP `.at3` from `disks/psp/snd_e/PS_BGM` into an XA one-shot with its own config id past the retail table (`MU_MOD_*`, `src/dra/mod_xa_music.h`). The fairy's English Nocturne is done exactly this way. `assert len(TRACKS)+len(ONESHOTS) <= 16` (l.117). Today there are 10 tracks plus 1 one-shot, so there is room for 5 more.
- The builder already re-creates ONESHOT songs from the player's UMD (`songs: SongStream[]`, `builder/src/build.ts:110`).

**Proposed hook (no DRA code)**
1. Add `("MU_MOD_ENDING_PSP", "<the PSP ending .at3>", gain, 0x3C, vol)` to ONESHOTS. The PSP file name is unknown here; the disc agent must find it. **[L]** The PSP track is said to be "Mournful Serenade"; confirm by listening.
2. In SEL `cutscene.c` PLAY_SOUND (both sites) and in `34B30.c:852`: `if (id == MU_STAFF_CREDITS && (g_Status.saveName[9] & MOD_FLAG2_PSP_ENDING)) id = MU_MOD_ENDING_PSP;`. That is about 24-40 B of SEL code.
   - This is cleaner than editing script bytes, which exist in up to three copies (PS1, PSP, JP).
   - Alternative: an override in `ModXaConfig` like `MU_MOD_NOCTURNE_EN` (`MOD/src/audio/sound_mod_music.h:44-55`). That costs **DRA** bytes and should be avoided.
3. Credit-roll sync. The credits are timed by SEL's own steps, not by the song. **[M]** If the PSP song is longer or shorter, the roll ends at a different point than the music. Measure on the discs. Possible fixes: let the one-shot timer end it (mode 2 one-shot, as retail), or fade out at the roll's end. Check how the PSP ending crawl is timed.
4. The Ending row goes into SEL (all characters) and sysopt (Alucard only). See §0.4.

**Costs**
- Disc: the song as 37.8 kHz stereo XA. About 300 KB/min, so a 4-5 min song is about 1.2-1.5 MB. **[M]**
- DRA: 0.
- SEL: about 40 B plus the row UI.
- `xa_music_config` table: none. Mod configs are appended in `mod_xa_music.h`.
- `check_cd_lba.py` is not affected: XA_STR1 is the last file, and README §5 shows new files go before XA.

**Risks**
1. The PSP song's identity and file. [L]
2. Credit sync. [M]
3. A stereo song's interleave share. repack_xa packs streams first-fit in 16 slots; a long stereo track takes 2 of 16. It is fine, but the disc grows.
4. Where the ending is reached by Richter: Richter mode has an ending too. The `saveName[9]` flag works for every character, so no special case is needed.

## 2. PSP ending in the sound test

**What exists [H]**
- The Ultimate "Sound mode" is a SEL main-menu button: `MOD_MENU_SOUND 5`, `Upd_Eng_ModSound 0x14`.
  - `MOD/src/menu/2C048_mod_sound_menu.h` and `2C048_mod_sound_button.h`.
  - The button art is made by `MOD/tools/gen_sel_soundmode.py` and uploaded to VRAM x 960, y 96.
  - Hooks are in `src/st/sel/2C048.c:210,698-700,744,1290-1293,1377-1378`.
- Its playlist is `g_ModSoundTracks[]` (`2C048_mod_player_select.h:931-976`): 44 Saturn-order entries, with "I Am the Wind" last. The list scrolls with `MOD_SOUND_ROWS 11`, so it has no length limit.
- `ModSoundStart` clears the dub bits, and a high bit `0x8000` selects a variant (`MOD_SOUND_NOCTURNE_JP`).
- The retail Librarian sound test (`src/st/lib/e_shop.c:5180-5213`, 33 ids, names around l.5140-5177, `"Sound test"` l.777) is a separate list in the LIB overlay.

**Change**
- Add `{_S("<PSP ending name>"), MU_MOD_ENDING_PSP}` after "I Am the Wind". That is 8 B of table plus the string in SEL rodata. Trivial.
- Optional: the Librarian list in LIB. This changes `D_us_80181978` and its name table. The LIB overlay can grow, but the PS1 Librarian draws names with a fixed row count, so check the scrolling. Medium effort; not needed for the request.

**Risk:** none beyond §1.

## 3. Area-name banner: JP graphics and effects behind the script toggle (user decision)

**Requirement:**
- Script = RT (retranslation): JP-style banner art (as on the retranslated JP disc) with the JP effects. Alchemy Laboratory and Abandoned Mine use the "drum/roll" effect; every other area uses the "shutter: drawn from one side, wiped to the other" effect.
- Script = PS1 or PSP: the US art with the US fade-in and disintegrate.

**What the source has [H]**
| Variant | File | Used by |
|---|---|---|
| US: fade in, dissolve to the sides | `src/st/e_stage_name_us.h` (440 lines) plus `stage_name_dissolver.h` | every US stage (`#ifdef VERSION_US`) |
| JP "shutter + wipe away" | `src/st/e_stage_name_jp.h` (1232 lines), non-TEK path; steps INIT/RENDER/WAIT/WIPE_AWAY(18) | HD, PSP, and every stage's `#else` branch |
| JP "drum/roll" (3D GTE rotation, "turning drum style text and shrinks the text out") | **`src/st/nz0/e_stage_name.c:6-406` and `src/st/chi/en_stage_name.c:12-411`**, identical bodies, PSP only | NZ0 (Alchemy Lab), CHI (Abandoned Mine) |
| Extra JP effects (colours/zoom/drum/cube/dissolve) | `e_stage_name_jp.h` `STAGE_IS_TEK` | HD's test stage TEK only. Probably the original multi-effect version. **Not needed.** |
| Saturn | `src/saturn/warp/particle.c:31` `EntityWarpStageNamePopup` | **Not decompiled** (declaration only) |

- The drum variant needs only libgte calls that PS1 overlays already link from main.exe: RotMatrix, RotTransPers, SetGeomOffset/Screen, SetColorMatrix, SetLightMatrix, NormalColorCol, TransMatrix, SetRotMatrix, SetTransMatrix, SetBackColor. All are present in `config/symbols.us.txt`. **[H]**
- The JP non-TEK path additionally uses `PrimDecreaseBrightness`, `UnkPrimHelper` and `UnkPolyFunc2` (stage prim helpers) and `Random`.
- PSP-only bits to remove: `func_psp_091040A0(gfxBank)`, `D_psp_091CE570`, `LoadStageNameGraphics`, `g_UserLanguage`.

**Graphics [H] / [M]**
- US art: tpage 17 (VRAM x 64, y 256), 4bpp, CLUTs `PAL_UNK_19F` and `PAL_UNK_19D`. Two 116x40 strips: u 4-120 v 0-40 and u 8-124 v 64-104 (`e_stage_name_us.h:74-100`, also documented in `MOD/tools/gdn_assets.py:1017-1018`).
- JP art: the same tpage, **one 128-wide strip** u 0-128 v 0-32 (and v 0-`PRIM_BOTTOM_V`) (`e_stage_name_jp.h:196-250`). The NZ0/CHI drum uses u 0-128 v 0-0x27.
- **The US stage BINs still contain the JP banner graphics** as cmpgfx assets: `gfx_stage_name_jp_sm` / `_jp_lg` / `stage_title_*_jp`, 22 entries over 22 overlays. Examples: CHI `bn_gfx_stage_name_jp_sm/lg`, ST0 `stage_title_st0_jp`, NZ0 `stage_title_nz0_jp` (`config/assets.us.yaml`; several are marked "# unused"). The original JP graphics are therefore partly obtainable from the US disc. **But the user wants the RT disc's banners**, which the fan patch may have edited (for example the English subtitle). Those must come from the 4th disc, so the disc agent should diff RT against the JP Rev 2 disc for each stage's banner gfx. **[L]**
- How the art reaches VRAM: through the stage's gfx banks (`g_api.o.gfxBanks`, `g_api.LoadGfxAsync(id)` → DRA `src/dra/4AEA4.c:52`, which decompresses cmpgfx). A JP banner can be its own `GfxBank` entry appended to a **rodata copy** of the stage's gfxBanks table.
  - The stage data section must not move (`check_stage_data.py`), but rodata can grow. The mod already does this for layouts and rooms.
  - The popup calls `g_api.LoadGfxAsync` at init when RT is on. This overwrites the US art in the same VRAM area, which nothing else uses while the popup is shown.
  - DRA cost: 0. [M]: check that LoadGfxAsync completes before the first draw; use a 1-2 frame wait step.

**Design**
- Each stage `e_stage_name.c` builds both entities:
  ```c
  void EntityStageNamePopup(Entity* e) {
      if (RT_ON()) StageNameJp(e); else StageNameUs(e);
  }
  ```
  - NZ0 and CHI (and RNZ0/RCHI? **[L]**: on PSP they use the shutter variant; per TCRF only the two normal-castle areas use the roll) use the drum body.
  - Make the headers re-includable with renamed entry points through a `#define`.
  - Latch the choice at step 0 (store it in the entity) so that a toggle in the middle of a banner does not switch implementations.
- Cost per overlay **[M]**: the JP shutter is about 2.5-3.5 KB of code plus data (it is longer than the US version), and the drum is about 2-3 KB. Add a few dozen bytes of gfx bank entries and the compressed JP art (about 0.7-1.5 KB, judging from the asset offsets: jp_sm→jp_lg spans 0x2D4-0x444 B).
- Overlays affected (those with an `e_stage_name.c`): about 26 stages plus 16 boss overlays (bo0-bo7, rbo0-rbo8 have `e_stage_name.c`) plus the mod's GDN/PRS/RGDN/RPRS.
- Boss overlays: check whether a popup is ever placed there. The US file includes it, but the boss rooms may never show it. [L]
- Total: about 26 × 4 KB ≈ 100 KB of disc. Every stage file after the first one shifts, which is allowed: README §5 says `lba_us.h` is regenerated and `check_cd_lba.py` only guards the literal sectors in cd.c and SEL, which sit after the stages… [M] check that check_cd_lba passes.
- **Shared code elsewhere is not possible**: no RAM is resident across stages apart from DRA, and the ARC_F2 region is Alucard-only.
- RAM per stage: stage overlays must end below `0x801E0000` with BSS. Most retail stages are far below that. Measure NO3, NO0, TOP and CEN after a build.
- Prim budget: JP NUM_PRIMS is 183 GT4 prims, against 87 in the US version (`e_stage_name_jp.h:36`, `_us.h:60`). That is about 100 more prims while the banner is shown. **[M]** It should be fine against 0x400 alloc, but test in busy entry rooms.
- **New Saturn stages** (`MOD/src/garden/gdn/e_stage_name.c`, `prison/prs/...`; flags 0xF0 and 0xF8; art composed from US glyphs by `gdn_assets.py:1015-1080` and `prs_assets.py:430-470`):
  - The Saturn's own name images are **Japanese** (`prs_assets.py:431`).
  - In RT mode, use the Saturn JP name images, which match JP-style banners, converted to the 128-wide JP layout with the shutter effect.
  - The English subtitle has to be composed (RT-disc glyphs) or omitted. Fan-text decision.
  - RGDN and RPRS place no popup at all (Saturn faithful), so nothing changes there.
- Name differences ("Olrox's Room", "Ground Water Vein" and so on) only appear in the JP-style subtitles. That is consistent with following the script toggle.

**Risks**
1. Whether the RT disc changed the banners, and how (needs a diff). [L]
2. Overlay growth and checks: `check_stage_data.py`, `check_status_shift.py` (whose `INTENDED` list must include every stage touched), and `psp_script.py --apply` (which patches overlays by address, so rodata moves are fine; it re-checks).
3. The JP code was matched for HD and PSP, not compiled for PS1 US. Expect small fixes (`VERSION_HD` paths, the `stpopupj` ext struct, `PAL_UNK_19E`). [M]
4. `check_status_shift.py` treats every changed retail overlay as an intended change, so the list grows a lot.

## 4. Retranslation font and all text, as a third script option

### 4.1 How US text is stored and drawn [H]
| Text | Storage | Renderer | Font |
|---|---|---|---|
| Cutscene dialogue (stages, bosses, SEL endings) | per-overlay script bytecode (`assets/.../cutscene_*.yaml`; asm bosses BO2/BO5/BO6/RBO2/RBO6 by address) | per-overlay copy of the dialogue entity, fixed 8 px advance (`MoveImage`, `nextCharX += 2` halfwords, e.g. `src/st/st0/cutscene.c:776`) | 8x8 VRAM sheet (§0.5) |
| Menu labels (`g_MenuStr`) and item, enemy, relic and spell **names** | DRA tables `g_EquipDefs` (0x34 stride), `g_AccessoryDefs` (0x20), `g_EnemyDefs` (0x28), `g_RelicDefs` (0x10), `g_SpellDefs`, with `char*` to `_S` strings (char − 0x20, terminated by 0xFF 0) | DRA `MenuDrawStr`, stage `BottomCornerText` | 8x8 sheet |
| **Descriptions** (info bar) and item pickup names | raw ASCII/Shift-JIS C strings | DRA `func_800F99B8` (`src/dra/menu.c:2384-2470`) and stage `BlitChar`. Both use `func_80106A28` → `Krom2RawAdd`, the **BIOS Kanji ROM**, 12x16 with trimmed (proportional) width | BIOS ROM. A custom glyph is used only when Krom returns −1 (`src/dra/66590.c:323-345`, `D_800AC910/914`) |
| Librarian bestiary text | LIB overlay (`src/st/lib/e_shop.c`, mod `MOD_LIB_DESC_*`) | LIB | Krom/8x8 |
| Area names | images (§3) | | |
| File menu, title, SEL menu text | SEL strings and images in F_SEL | SEL | 8x8 sheet / gothic 16x16 |
| JP-only text paths | `func_800F98AC` (pure SJIS, `menu.c:2350`) is still present. `func_800F9D40` ("JP text; only HD calls it") was **removed by `MOD_DRA_STRIP`** and is not recoverable without DRA bytes. | | |

Volume: the author notes that SEL's copy of DRA's config strings was **~15 KB** (`src/st/sel/config_us.c:4-8`). Add g_MenuStr and spells, so the DRA text is **about 16-18 KB** [M]. Script text in the overlays is extra, per overlay.

### 4.2 How the PSP script swap works [H]
- `MOD/tools/psp_script.py` maps the PSP text line by line onto the PS1 skeleton (voice id PS1 = PSP+2, plus overrides). It wraps at 21 columns, with NO4 capped at 3 lines of 22 columns.
- It writes `mod_psp_script.h` per overlay: `g_ModPspSpill` (a rodata copy filled post-link by `--apply`, because the copies jump inside themselves) and the map `g_ModPspMap[][2]`. The JP dub adds `g_ModJpSpill/Map`.
- `SetCutsceneScript` calls `ModPspScript(script)` (`src/st/cutscene_script_text.h:24`, `set_cutscene_script.h:18`). The lookup function is generated at `psp_script.py:1194-1225`.
- Menu names that differ (only 9 strings) follow the dub through `ModApplyDubText`. That is DRA code (`MOD/src/menu/game_handlers_mod_balance.h:71-88`), called every frame from `HandlePlay` (`src/dra/game_handlers.c:422-423`). It copies equal-or-shorter spans over the DRA strings, with ≤16 entries and 384 B.
- Fixed fixes repoint DRA table pointers to strings that SEL builds in `g_ModDub.fixedText` (768 B; `gen_menu_text.py`, `2C048_mod_player_select.h:152-243`).

### 4.3 What a third script costs, and where it could live
**Cutscene scripts** (cheapest, the established path):
- Add an "rt" set to psp_script.py: a third spill and map per overlay, chosen first in `ModPspScript` when `RT_ON()`.
- Source text: the RT disc's JP-skeleton scripts. The JP and US skeletons differ (voice ids shifted, for example `jp = us − 2` around 0x342+, and different line splits), so a JP→US line map is needed, as for the PSP.
- Cost: roughly equal to the PSP spill per overlay, about 1-6 KB per cutscene overlay. [L] Measure `sp["size"]` in `build/us/psp_script/report.txt` after a build.
- Pairing: RT text matches the **JP** voices best. Today the JP dub shows PSP English text, so "JP dub + RT text" becomes the natural combination. Caveat: the mod's JP dub is the PSP's Japanese recording. **[L]** Whether that is the 1997 script or a revision affects how well the text fits.

**DRA text (16-18 KB): the hard part.** Options:
1. **Pointer redirection, no DRA code.** At new game, SEL writes each table's `name`/`desc` pointer to RT strings in a resident RAM blob. In Alucard games, sysopt re-points them when the user toggles. US pointers are restored from a copy in SEL or ARC_F2. **The blocker is a resident RAM home for about 18 KB.**
   - `g_ModDub` spare is about 1.4 KB.
   - DEMO_KEY is 8 KB [L].
   - Overwriting the **US string pool in DRA rodata itself** is the strongest candidate. If the RT pool fits in the bytes of the US pool (~15 KB) plus the spares, SEL writes RT strings over it and repoints. Switching back means re-copying the US bytes from SEL's dead 32 KB blob (§0.2) at the next SEL pass, or from a CD file.
   - In-game switching back needs the US text resident or loadable. sysopt could re-point a DRA CdFile (for example `g_LbaBinDemokey`, `src/dra/cd.c:51`, which loads 0x2000 B to 0x801E8000) at a text-bank file and copy it in chunks. This is complex. **Recommendation: allow the script toggle only at new game and on load (SEL), and show it read-only in sysopt.** If in-game toggling is mandatory, budget the CD-load approach.
2. Making `ModApplyDubText` 3-way is not viable: RT strings are longer than US strings.
3. A second DRA.BIN is not possible: DRA is loaded once at boot.

**Fonts**
- **8x8 sheet** (dialogue and menus): VRAM-neutral if the RT glyphs replace the US sheet in place.
  - The cleanest method is alternative files `F_GAME_RT.BIN` and `F_GAME2_RT.BIN` (0x42000 B each, about 528 KB of disc), chosen in `cd.c:796-804`. That is **DRA code**: about 8-16 B, if `g_LbaBinGame.loc` is loaded from a `g_ModDub` word that SEL sets instead of the immediate `OFF_BIN_FGAME(2)`. It fits only if the pad allows; otherwise free more dead code.
  - Alternative: patch only the font rows into VRAM after the F_GAME load, from SEL. Not possible: F_GAME loads after SEL hands over.
  - Glyph cells: 256 cells. US uses about 96, so there is room for extra glyphs (accents, ligatures). [M]
- **Proportional (VWF) font**: if the RT patch uses one, the US dialogue renderer (fixed 8 px, one copy per stage overlay) and the DRA menus (fixed) cannot show it without code in every cutscene overlay, plus DRA for menus. **Determine the RT font format first.** [L]
- **Descriptions** use the BIOS Kanji ROM. An RT description font would need `func_80106A28` changed, which is DRA code. **Recommend keeping the ROM font for descriptions.**

**Other text**
- The LIB bestiary.
- SEL file menu strings.
- Shop texts.
- Item pickup popups (DRA names, so covered by repointing).
- The PSP-only `fixedText` fixes must not be applied in RT mode. `ModDubTextCopy` must be made RT-aware.

**Risks (ranked)**
1. The resident RAM home for DRA strings, and in-game toggling. [H that it is hard]
2. The RT font format (VWF or not) and its encoding versus `_S`. [L]
3. The JP→US script mapping effort for every cutscene, plus the asm-only bosses. [M]
4. The DRA bytes for the F_GAME redirect. [M]
5. Overlay growth in many overlays (§3 compounds this).
6. Rights and permission from the RT authors (the README credits Knight0fDragon for comparable use).

## 5. Subtitles for voice-only lines

**Triggers [H]**
- Confessional priest: DAI `src/st/dai/e_confessional.c:220-224` plays `UNK_4E7` (an XA voice id, PSP behaviour ported under `MOD_SATURN_CASTLE`). It is held about 288 frames, and `ModStopPrayer` (l.80-86) stops it.
- Familiars: `g_api.PlaySfx(id)` with VAB voice ids from per-servant tables. Faerie: `src/servant/tt_002/faerie_data.h:138-172` (`g_FaerieSfx`, hint and intro event descriptors), calls at `faerie.c:734-1255`. Similar tables exist for demon (tt_003), sprite (tt_005/_psp) and nose devil (tt_006/_psp).
- The dub swaps the banks (`g_ModPspServantSfx`, `JP_SD.BIN`), so **the subtitle text depends on the dub row**: PS1 English, PSP English, or Japanese (show English). The JP familiars Sprite and Nose Devil speak Japanese on PS1.

**Mechanism**
- **DAI**: draw with an 8x8-sheet SPRT string plus a box. Add about 300-500 B of code to DAI plus the strings. Trigger it next to `PlaySfx(UNK_4E7)` and clear it on `ModStopPrayer` or the timer.
  - Alternatively, run a tiny cutscene script with only TEXT ops through DAI's existing dialogue entity. It is reusable, but [M] the dialogue entity may take player control. Avoid that.
- **Familiars**: servant files are fixed at **0xA000 B** (40 KB, loaded at `FAMILIAR_PTR 0x80170000`, `config/splat.us.tt_00x.yaml`). TT_002 ends at .bss 0x92D0, which leaves about 3.3 KB minus BSS. [M] Cannot grow: weapon RAM starts at 0x8017A000.
  - Option A: a per-servant wrapper `ServantSay(id)` that plays the voice and draws the subtitle. About 600 B per servant plus the strings, and the strings × 3 dub variants are tight.
  - **Option B (preferred)**: put the subtitle renderer and all familiar strings in the **ARC_F2 code region**. Familiars exist only in Alucard games, so it is always resident then. Add a jump-table header entry, as sysopt has. Servants call `ModSubtitle(id)` through a magic-checked pointer (about 40 B each) and tick it every frame from their update. The ARC_F2 budget is the 9232 B total shared with sysopt. [L] Measure the sysopt size.
  - A global hook by overwriting the `g_api.PlaySfx` pointer (g_api is RAM, copied once at boot, `src/dra/42398.c:832`) is tempting but **dangerous**: the hook would dangle in Richter or Maria games (ARC_F2 is replaced). Avoid it, or restore the pointer on every player load.
- Prim budget: about 30-40 prims per line. OK.

**Risks**
1. The servant file size limit. [M]
2. The ARC_F2 budget shared with the new sysopt rows. [L]
3. Getting exact line texts for the PS1, PSP and JP banks (transcription work).
4. Timing (VAB clips have no length table in code; use fixed per-id durations).

## 6. JP prologue narration

**Facts [H]**
- The US disc keeps the JP voices `JP_VO_NARRATOR_KATSUTE` 0x341 ("Katsute…"), `_SOSHITE` 0x342 ("Soshite 5 nen no tsukihi ga nagareta"), `_AKUMAJO` 0x343 (the title call), the developer messages 0x344-0x34B, the "Konami" calls 0x34C-0x357, and the Shaft lines 0x52E-0x530 (`include/sfx.h:160-194,313-316`).
- **repack_xa.py silences exactly `JP_IDS = 0x341..0x357 + 0x52E..0x530`** unless `--keep-all` (`MOD/tools/repack_xa.py:79-82,285-301`). The narration is among them. It can be kept selectively by removing 0x341-0x343 from `JP_IDS`. The audio comes from the **US disc**, so no new disc is needed.
- The disc cost is a few hundred sectors. [L] The repack prints the dropped sector count.
- The US prologue scroll is `src/st/st0/prologue_scroll.c:145-479`: an image crawl (tpages 0x98-0x9E, loaded by `CdFile_Prologue`) with `MU_MOONLIGHT_NOCTURNE` (l.284-286) and an `EndTimer` of 0x14B0 frames. The title fade follows (steps 7-9), then the NO3 load (l.466-476).
- **No JP ST0 code is in the decomp** (HD has no ST0). How the JP version sequences the narration (over the crawl? replacing the music? 0x342 at "five years later", 0x343 at the logo) must be read from the JP disc's ST0 by disassembly. [L] XA plays one stream at a time, so the JP narration probably replaces Moonlight Nocturne, or the music and narration are mixed in one stream.
- `src/st/st0/2A218.c:243-262` holds a mod change for START during the skipped prologue dialogue. It is unrelated to the scroll.

**Proposal**
- Keep 0x341-0x343.
- In ST0 `PrologueScroll`: when narration is on (a new bit, or tied to the JP dub or RT script), play 0x341 instead of Moonlight Nocturne at step 4, 0x343 at step 7, and 0x342 where the JP sequence has it.
- Make the scroll speed and `EndTimer` match the narration length.
- RT text crawl: the US crawl is *images* (prologue art file), so a crawl matching the RT text would need new crawl images. That is another per-mode asset.
- Cost: ST0 code about 100-200 B. No DRA cost.

**Risks:** the JP sequencing is unknown [L]; the crawl images [M]; the skip and START paths.

## 7. Build pipeline

- `build_disc.sh` (378 lines), in order:
  1. Generators (layouts, rooms, items, enemies, menu text, music, stage sounds, F_MAP, title art).
  2. `patch_status_asm`.
  3. `make build_assets`.
  4. The PSP dub (`psp_dub.py`, `psp_script.py`, grunts, sfx), the JP dub set and `repack_xa.py`.
  5. `sotn.sh build us`.
  6. Pad balancing (data pad, then code pad).
  7. `psp_script --apply`.
  8. New stages, weapons, MONSTER2, RIC2/BO6RIC2/TOPRIC2, Maria builds, CENP, `gen_mar_hud`, `build_sysopt`, SELRIC2.
  9. `make disk`, which reruns once if `lba_us.h` changed.
  10. `fix_sector_headers` and the checks: check_cd_lba, dra_layout, symbol rechecks, no_dirt, stage_data, psp_dub, status_shift, menu_text, abs_syms.
- Tools: the sotn-decomp toolchain (cc1-psx-26, maspsx, mipsel binutils), Python 3 `.venv` plus `MOD/tools/requirements.txt`, Go (sotn-assets, sotn-disk), Rust/cargo (`tools/saturn/assets`, `tools/maria-sfx`, `sotn_str`), Node ≥22, gcc (satxa). The builder's audio module needs emsdk 4.0.10 and FFmpeg 7.1.1 source.
- Inputs: `disks/us` (extracted PS1 US), `disks/saturn` (Saturn files) and `disks/psp` (`PSP_GAME/USRDIR/res/ps`, from `extract_psp.sh`). `SEL config_us.c` even `.incbin`s retail SEL. **Nothing meaningful builds without the PS1 US disc.** Without the Saturn and PSP discs the full script fails (`MOD_PSP_DUB=0` skips the dub, but the Saturn generators have no switch). [M] `-DNO_MOD_ULTIMATE` builds vanilla.
- The builder (`MOD/tools/builder`) is a parallel TypeScript pipeline. `make_hollow.ts` blanks every Saturn- or PSP-derived span (file, xa, xamono, array, text) of the full image and writes an xdelta patch plus `manifest.json`. `build.ts` refills those spans from the player's discs, and the result must match the MD5. Disc identity is in `src/identify.ts` (`DiscKind = "ps1"|"saturn"|"psp"`, with serial and sector-count checks).
- **For a fourth disc (JP PS1 plus the RT patch):**
  - Add `DiscKind "jp"` (SLPS-00067 Rev 2, Redump md5 and sector count).
  - Decide whether the player supplies the patched RT image or the builder applies the RT patch itself. The second is safer for MD5 checking.
  - Add `IsoFs` reads.
  - Add span generators for every RT-derived byte (script spills = "array"/"text" spans; F_GAME_RT; banner gfx; crawl images).
  - Mirror each in Python (build_disc) and TypeScript (builder), with `test_*.ts` parity tests.
  - Add a `disks/jp` extraction step, and add the hollow sweep's "remaining foreign bytes" check for JP runs.
  - The release must not contain RT text or font bytes unless the RT authors permit it.

## 8. Recommended implementation order

1. **Build baseline** on the user's machine (US, Saturn and PSP discs). Record the real `MOD_DRA_PAD`/`MOD_DATA_PAD`, the sysopt size (ARC_F2 free), the SEL size, the per-overlay psp-spill sizes, the TT_00x .bss sizes, and the stage overlay ends.
2. **Flag plumbing:** `saveName[9]` as a second flags byte, verified in an emulator (file list, card manager). The SEL panel redesign (page 2) and the sysopt row table expanded to 6 rows (popup moved up). No feature behaviour yet.
3. **PSP ending** (§1) plus the **sound test entry** (§2). Small and self-contained; validates the ONESHOT, SEL and flag path and the builder song span.
4. **JP narration** (§6): un-silence 0x341-0x343, then reverse-engineer JP ST0. Independent of the RT text.
5. **Subtitles** (§5): DAI first, then the ARC_F2-hosted familiar renderer.
6. **RT script, step A:** fourth-disc ingestion (Python, then builder), the RT font format study, and the JP→US script mapping in psp_script.py (cutscenes only).
7. **RT step B:** DRA strings by pointer redirection (SEL, new-game and load only), the F_GAME_RT redirect (needs DRA bytes), and LIB/SEL texts.
8. **Feature 3 banners** (depends on the RT flag and the RT banner art): the shared re-includable US/JP/drum headers, then per-stage gfx bank copies, then GDN/PRS RT art.
9. In-game RT toggling (optional; complex; Alucard only).
10. Builder parity and the release.

## 9. Open questions for the disc agent and the user
- The PSP ending track's file name and length. The credits timing of the PSP and PS1 endings.
- The RT patch v1.2: does it use a fixed or proportional font, its encoding, where its font lives on the JP disc, whether it changed the stage banners and the prologue crawl images, and its licence.
- JP ST0: where 0x341-0x343 (JP ids are shifted; check) are played, and whether music plays under them.
- Whether `0x801E8000`-`0x801EA000` is ever written during normal play.
- Whether the user accepts **no in-game toggles for Richter and Maria games**, and **RT toggling only at new game or load**.

---

# Addendum A: mid-game script switching and the proportional retranslation font

User decisions:
1. Richter and Maria games get the toggles in the new-game menu only.
2. The script must be switchable **mid-game** from the Alucard System popup.
3. The RT font is **proportional** (VWF). Its exact format is still to come from the disc agent.

## A.1 Mid-game script switching (Alucard games)

### A.1.1 The machinery to reuse [H]
sysopt already reloads data from the CD mid-game. In `SysOptBanks()` (`MOD/src/menu/sysopt.c:213-247`) it:
- re-points a DRA `CdFile`'s `.loc` (`g_LbaSdAlkVh/Vb`),
- sets `g_LoadFile`,
- sets `g_CdStep = CdStep_LoadInit`,
- waits for `g_CdStep == CdStep_None && !g_IsUsingCd`.

The pause menu's exit waits for the CD (`g_IsUsingCd`).

**The CdFile to borrow is `g_LbaBinDemokey`** (`src/dra/cd.c:51`, `{0x7415, 4, 0x2000, ...}`, slot `CdFile_DemoKey` in `D_800ACC74`). Its callback copies to `DEMO_KEY_PTR` = `0x801E8000` (`cd.c:268-269`, `CdCallback_4`).
- sysopt can set `.loc` and `.size` to any sector run of a new disc file, load it in 8 KB chunks, and copy each chunk out.
- **DRA cost: 0 B.**
- Condition: `0x801E8000-0x801EA000` must not be in use while the pause menu is open. It is the demo buffer [M]. `SAVE_DATA_PTR` 0x801EA000 follows it, so a chunk must stay ≤ 0x2000.

### A.1.2 Where the text lives: alternatives
The DRA strings are about 16-18 KB: names and descriptions referenced by pointers inside `g_EquipDefs` (0x34 stride), `g_AccessoryDefs` (0x20), `g_EnemyDefs` (0x28), `g_RelicDefs` (0x10), `g_SpellDefs` and `g_MenuStr`.

| | Mechanism | Resident RAM needed | DRA bytes | Verdict |
|---|---|---|---|---|
| **A1. Pool overwrite** | A per-script "text pack" file holds (a) the string bytes, laid out to fit DRA's own US string pool plus an overflow area, and (b) the list of table pointers. sysopt (or SEL) loads it chunk by chunk through `CdFile_DemoKey`, copies the strings over the pool and rewrites every table pointer. Switching back loads the US pack. | Only the overflow beyond the US pool (~0-4 KB [L]), in `g_ModDub` spare (~1.4 KB) and/or the last chunk left in `0x801E8000` | **0** | **Recommended [M]** |
| A2. Pointer swap into a separate buffer | The US pool stays intact. The RT strings live in a spare buffer and the tables are repointed. | All ~18 KB | 0 | Not feasible. The spares add up to `g_ModDub` ~1.4 KB + DEMO_KEY 8 KB + ARC_F2 tail (9232 − sysopt − subtitles, likely < 5 KB) ≈ 13 KB at best [M]. |
| A3. Hook the string accessors in DRA | e.g. select the table by flag inside MenuDrawStr | none | hundreds of bytes, over dozens of call sites | Rejected |

Pack format (proposed):
- header: magic, script id, pool length, overflow length, pointer count;
- `u16` pointer-slot ids (a table id and a record index are enough; the stride is known);
- `u16` offsets into pool or overflow;
- the bytes.

Three packs: **PS1 text, PSP text, RT text**. This turns today's two text mechanisms into one:
- `ModApplyDubText` (DRA, every frame, `MOD/src/menu/game_handlers_mod_balance.h:71-88`, called at `src/dra/game_handlers.c:423`);
- the `fixedText` repointing (SEL `ModDubTextCopy`).

A pack is a whole state, so the Dub row selects PS1 or PSP text through the same loader. Every way into a game passes through SEL, so SEL applies the pack at game start: from its dead 32 KB blob (the RT pack ≈ 18 KB fits) or via the same `CdFile_DemoKey` load. sysopt applies it when the row changes.

**This also frees DRA bytes.** Once packs replace the per-frame dub text, `ModApplyDubText` and its call can be deleted. That frees about **80-100 B of DRA code** [M]; the exact size needs `nm --size-sort build/us/dra.elf`.
- `g_ModDub.text` (648 B) and `fixedText` (768 B) also become free BSS.
- With the 1.45 KB spare, `g_ModDub` then has about 2.8 KB for overflow and the width table.

**Must do in any variant:** while RT is active, `ModApplyDubText` must not run (set `g_ModDub.text.magic = 0`). Otherwise it writes PS1/PSP bytes every frame at the *US string addresses*, which then hold RT text. [H]

### A.1.3 What already holds old text when the toggle flips
| Item | Behaviour | Action |
|---|---|---|
| Menu names drawn with `MenuDrawStr` (`src/dra/menu.c:952`, 65 call sites) | Read through the table pointers every frame | Correct on the next frame [H] |
| VRAM-cached text rendered with the BIOS font at menu open or selection: relic list (`func_800F9E18`, `menu.c:2545-2595`, RECT 0x180,0x30), info-bar descriptions (`ShowText` = `func_800F99B8`), spell descriptions (`menu.c:4284`), menu header (`menu.c:3628`) | Stale until the next render | Accept: it refreshes when the cursor moves or the menu is reopened. Or call those DRA functions again from sysopt when the popup closes (callable at known addresses, 0 DRA B) [M] |
| Stage `BottomCornerText` (`src/st/popup.h`) | Copies the string at creation | Transient; fine [M] |
| Overlays, servants and weapons holding a *pointer* to a name across frames | None found in the source [M] | Read through `g_api.equipDefs` or `enemyDefs` when needed |
| Cutscene scripts | Chosen in `SetCutsceneScript` (`src/st/cutscene_script_text.h:24`) when a scene starts. Pause is normally off during scenes [M] | Latch the RT flag (VWF path and script) in the dialogue state at scene start |
| Banner (§3) | Chosen at the popup's step 0 | Applies at the next area entry; latch it |
| JP narration / prologue | ST0 only | n/a in-game |

### A.1.4 Font swap mid-game
- The 8x8 sheet both renderers sample is at **VRAM (896,256)-(1023,383)**, 4bpp, 16 glyphs per row:
  - `MenuDrawChar` uses tpage 0x1E with u `(ch&0xF)*8`, v `(ch&0xF0)>>1` (`menu.c:947-950`);
  - the dialogue renderer's MoveImage source is y `((b&0xF0)>>1)+240` for ASCII ≥ 0x20, the same rows.
  - [H] for the coordinates. [M] that no other F_GAME art shares the rect `x 896-927 (halfwords 32), y 256-383`.
- One sheet is **exactly 8 KB**, one DemoKey chunk. sysopt loads `FONT_RT.BIN` (or the US one) and `LoadImage`s it. `LoadImage` is libgpu in main.exe, so sysopt can call it through `config/symbols.us.txt` like `SsUtAllKeyOff`.
- Rewriting this VRAM while the pause menu is open is safe: the next frame simply samples new glyphs. The dialogue line strips are at y 384+ and do not overlap [M].
- Load order on a toggle:
  1. font chunk → `LoadImage`;
  2. text-pack chunks → copy;
  3. the final overflow chunk last, if it stays resident at 0x801E8000.
- **Game start and load:** `F_GAME`/`F_GAME2` are uploaded after SEL hands over (`cd.c:796-804`), which reinstalls the US sheet. Options:
  - (i) **`F_GAME_RT.BIN`/`F_GAME2_RT.BIN`**: whole copies with the RT sheet, 2 × 0x42000 B of disc. `cd.c` takes `g_LbaBinGame.loc` from a `g_ModDub` word that SEL sets, instead of the immediate. **About 8-16 B of DRA**, paid from the freed `ModApplyDubText` bytes. Recommended.
  - (ii) Re-upload the font from every stage overlay's init when a VRAM marker mismatches. That costs per overlay, needs the font resident (it would be the 8 KB at 0x801E8000) and races the stage's own uploads. Not recommended.
  - (iii) Accept the US glyphs until the first pause. Not acceptable.

### A.1.5 DRA byte budget
| Item | Bytes |
|---|---|
| Pack loader/applier (sysopt + SEL), font chunk upload | 0 (in ARC_F2 / SEL) |
| `F_GAME_RT` redirect (A.1.4 i) | +8..16 |
| MenuDrawStr VWF (A.2, stage 2 only) | +16..24 code; width table in `g_ModDub` |
| `ModApplyDubText` + call removed | −80..100 [M] |
| Committed `MOD_DRA_PAD` (re-measure) | 40 (README says 4) |

Further `MOD_DRA_STRIP` candidates: a static scan of every DRA C function for references across `src/` and `mods/` finds **no unreferenced DRA function left**. The only hits were the already-stripped `GetCdVolume`, `func_800E38CC`, `func_800FD39C`, `func_801072FC`, `func_801083F0`, `func_8010DA2C`, plus the PSP-only `RenderEntitiesPSP`. Further bytes therefore come from **moving mod code out of DRA**, not from stripping retail code:
1. `ModApplyDubText`, as above.
2. Possibly `ModXaConfig`'s `MU_MOD_NOCTURNE_EN` special case (`MOD/src/audio/sound_mod_music.h:44-55`, ~10 instructions [M]), if the Nocturne swap is moved into the pack/dub path.

A size-sorted symbol diff after a build is needed for exact numbers.

### A.1.6 Risks (ranked)
1. Whether `0x801E8000` is really free while paused. Check with a write watchpoint over a full playthrough segment. [L]
2. Whether the RT strings fit the US pool plus overflow. Measure once the RT text is extracted. [L]
3. Whether `CdFile_DemoKey`'s callback is safe outside demo mode (`cd.c:268, 1080`). It uses `g_Cd.D_80137F74` block offsets; set them the way the demo loader does. [M]
4. Text cached in VRAM showing stale glyphs until it is redrawn. Cosmetic.
5. Removing `ModApplyDubText` changes retail-equivalent timing assumptions. Re-run `check_menu_text.py` and rewrite it to check the packs.

## A.2 Proportional font: every renderer the RT text touches

| # | Renderer (where) | Copies | Glyph path | Is VWF needed for RT to fit? | VWF cost / home |
|---|---|---|---|---|---|
| 1 | **Cutscene dialogue**: C in NO3, ST0, DAI, DRE, LIB, NZ0, TOP, CEN (+CENP), RCEN, NO4, SEL (+SELRIC2), MAR (12 sources); **asm-only** in BO2, BO5, BO6 (+BO6RIC2), RBO2, RBO6 (`INCLUDE_ASM`) | 17 overlays (+3 derived) | 8x8 4bpp glyph `MoveImage`d from the sheet into a per-line VRAM strip at y 384+12·line, fixed 8 px (`src/st/st0/cutscene.c:685-777`); 21-22 columns (`psp_script.py` MAX_COLS) | **Yes, for fidelity.** Without it, RT lines need re-wrapping (more boxes or scrolling), as psp_script already does | **The PSP build's software VWF is already in these C sources** under `VERSION_PSP`: `StoreImage` the glyph, compute its width from its pixels, nibble-shift into a RAM line buffer `cutsceneUnk3Unknown[896]` (224x8), then `LoadTPage` (`st0/cutscene.c:691-765`). It is present in ST0, NO3, NO4, RCEN, DAI and DRE. Move it into a shared `src/st/` header for the others. About 0.5-0.8 KB code + 0.9 KB BSS per overlay [M]. No width table is needed (auto-trim), but an explicit table could be added if the RT font has kerning. **The 5 asm bosses need hand-written MIPS or decompiling their dialogue entity.** |
| 2 | **DRA menus**: `MenuDrawStr`/`MenuDrawChar` (`menu.c:947-995`): item, accessory, relic, spell and familiar names, enemy names in the equip/bestiary contexts, menu labels | 1 (DRA) | 8x8 sheet SPRT per char, `x += 8` | For long RT names: yes. Short names fit at fixed width | Change `x += ChWidth` to `x += g_ModDub.w[ch]` (US table all 8): **+16-24 B DRA**, 256 B table in `g_ModDub`. Callers that centre or right-align by `len*8` will misalign [M] |
| 3 | **Info bar, descriptions, relic list, spell descriptions**: `func_800F99B8` (`menu.c:2384`) → `func_80106A28` → `Krom2RawAdd` (BIOS Kanji ROM, 12x16, auto-trimmed) | 1 (DRA) | Already proportional; cached in VRAM | No | Using the RT *font* here would need `func_80106A28` changed (its custom-glyph fallback only runs when the ROM misses, `src/dra/66590.c:323-345`): **not recommended**. Keep the BIOS font and fit the text to the bar width (`var_s4` 0x90/0x3C) |
| 4 | **Stage `BottomCornerText`** (`src/st/popup.h`: pickup and "obtained" names) | ~40 stage overlays | 8x8 sheet, fixed 8 px, box sized from the text | No (names are short) | Per-overlay VWF is not worth it |
| 5 | **Stage `BlitChar`** (`src/st/blit_char.h`, pickup names in `e_collect.h`) | stage overlays | BIOS ROM proportional | No | — |
| 6 | **LIB shop and bestiary** (`src/st/lib/e_shop.c`: `func_us_801B1064` 8x8 prim text, `func_us_801B0C40` pixel text) | 1 | Fixed 8x8 / ROM | Mostly no; long bestiary lines need refitting | LIB-local VWF possible later (~0.5 KB) |
| 7 | **SEL**: file select, name entry, the mod's panels (`DrawImages8x8`, `ModCharselTextRGB`) | 1 | Fixed 8x8 | No (few strings; names are player input) | — |
| 8 | Images: banners (§3), prologue crawl (§6), title and menu buttons, the HUD | — | — | Asset swaps, not a renderer | — |

Note [L]: if the RT font's cells are taller than 8 px (for example 8x12 or 8x16 for dialogue), renderer #1 also needs a new line pitch (12 px today), line-strip height and box geometry, and the buffer grows. Confirm the cell size first.

### Recommended staging
- **v1**
  - VWF in the 12 C cutscene overlays (the ported PSP path, selected by the latched RT flag).
  - RT glyphs at a **fixed 8 px advance** everywhere else (menus, popups, LIB, SEL).
  - BIOS font for descriptions.
  - Text refitted by the pack tool, with hard length checks per field (as `gen_menu_text.py` asserts today).
  - The 5 asm bosses at fixed width, with re-wrapped boxes.
- **v2**
  - MenuDrawStr VWF (DRA +16-24 B, after `ModApplyDubText` is removed).
  - VWF in the asm boss dialogues.
  - Optional LIB VWF.

Candidly, under v1 these will look worse than the RT patch on the JP disc:
- Menu names are monospaced, so they look wider and gappier. Some long RT names must be abbreviated to fit US columns.
- Descriptions use the console's BIOS font, not the RT font.
- Boss dialogues with Richter, Shaft and the others in BO2/BO5/BO6/RBO2/RBO6 are monospaced and re-wrapped.
- Line breaks and box counts follow the US box geometry (21-22 columns, 3-4 lines, NO4 limited to 3), not the RT patch's.
- Any RT glyph cell taller than 8 px is out of v1.

## A.3 Updated implementation order
1. Baseline build and measurements (unchanged), **plus**:
   - a size-sorted DRA symbol list;
   - an emulator write-watch on `0x801E8000-0x801EA000` across play, menus, saves and the map.
2. Flag plumbing (`saveName[9]`) and the menu redesign: SEL page 2; sysopt rows 6, popup moved up.
3. **Text-pack infrastructure, without RT yet:**
   - a pack builder tool, plus TypeScript parity in the builder;
   - SEL applies the pack at game start;
   - sysopt applies it on Dub change;
   - remove `ModApplyDubText` and `fixedText` from DRA;
   - the PS1 and PSP packs must reproduce today's behaviour byte for byte, with `check_menu_text.py` ported to packs.
   - This frees the DRA bytes for later steps and de-risks A.1 with known text.
4. PSP ending and sound-test entry.
5. JP narration (0x341-0x343 un-silenced, JP ST0 reverse-engineering).
6. Subtitles (DAI, then the ARC_F2 familiar renderer). Check the ARC_F2 budget against the sysopt growth from steps 2-3.
7. **RT, step A:** fourth-disc ingestion; the RT font format (cell size, widths, encoding); `FONT_RT` + `F_GAME_RT`/`F_GAME2_RT` and the `cd.c` redirect (+8-16 B); the RT pack (DRA strings), mid-game swap via `CdFile_DemoKey`.
8. **RT, step B:** cutscene scripts (third copy set in `psp_script.py`), the shared VWF header ported from the PSP path into the 12 C overlays, the latch at scene start.
9. Banners (§3), following the RT flag.
10. v2: MenuDrawStr VWF, asm-boss VWF, LIB VWF.
11. Builder parity and the release (RT bytes only from the player's disc, subject to the RT authors' permission).
