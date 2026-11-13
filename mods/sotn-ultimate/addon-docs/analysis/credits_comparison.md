# SOTN credits: PS1 US vs PSP US (Dracula X Chronicles port)

Scripts/outputs: `/home/claude/work/credits_analysis/` (decode.py, analyze.py, propose.py, mkmd.py; `psp_credits_decoded.yaml`, `credits_psp_order_A.yaml`/`_B.yaml`, `table_{orig,A,B}.bin`). Nothing in the repo was touched; PS1 bytes read from `disks/us/ST/SEL/SEL.BIN`, PSP bytes from `disks/psp/PSPBIN/sel.bin` (US UMD extraction, not the EU `disks/pspeu`).

## 1. PS1 US roll

- Data: `SEL.BIN` file offset `0xBC54`..`0xC404` (1968 bytes, VRAM 0x8018BC54). Verified: my decoder re-encodes to exactly these 1968 bytes.
- Format: byte stream. `00` END_CREDITS; `01 n` SUBTEXT, `02 n` ENTRY, `03 n` SECTION (each = "end of current line, next line's x offset = n"; the opcode type is the vertical gap before the next line: SUBTEXT +0 px, ENTRY +6 px, SECTION +12 px; an opcode with no text before the next opcode is a blank line); `20..7E` ASCII glyph; `80..9F xx` two-byte glyph (func_80106A28, e.g. `81 67` = opening quote, `9F 54 82 50 82 58 82 58 82 56` = "(C)1997").
- Build: `config/assets.us.yaml` line `[0xBC54, credits, credits]` -> `assets/st/sel/credits.yaml` (276 rows of `[CREDITS_SUBTEXT|ENTRY|SECTION, n]`, `[TEXT, "..."]`, `[BYTE, 0x..]`, `[END_CREDITS]`) -> Go handler `tools/sotn-assets/assets/credits/handler.go` emits `src/st/sel/gen/credits.h` -> `src/st/sel/cutscene_data.c: u8 cutscene_credits[] = {#include <gen/credits.h>}`. Consumed by the credits entity in `src/st/sel/cutscene.c` (~line 590-790, fed through `func_801B76F0(cutscene_credits)`).

Blocks (112 text lines, 150 opcode slots):

1. **(title card)** (2 lines): CASTLEVANIA; SYMPHONY OF THE NIGHT
2. **-Cast-** (8 lines): ROBERT BELGRADE; SCOTT MCCULLOCH; KIMBERLY FORSYTHE; MICHAEL G.; BARBARA WHITLOW; DENNIS FALT; ALISON LESTER; JEFF MANNING
3. **-Staff-** (0 lines): 
4. **-Producer & Director-** (1 lines): TORU HAGIHARA
5. **-Assistant Director-** (1 lines): KOUJI IGA
6. **-Localization A.D.-** (1 lines): HARRY INABA
7. **-Programers-** (4 lines): TORU HAGIHARA; GAGENSAI.F; KOUJI IGA; KOUSUKE IWAKURA
8. **-Designers-** (7 lines): REIKA BANDO; TOSHIHARU FURUKAWA; KIMIHIRO MORISHITA; HIROTO YAMAGUCHI; NOBUYA NAKAZATO; SHINICHIRO SHIMAMURA; NORIYOSHI SATO
9. **-CG-** (1 lines): KENICHIRO IMAIZUMI
10. **-Scenario Writers-** (2 lines): KOUJI IGA; TOSHIHARU FURUKAWA
11. **-Sound Staff-** (5 lines): MICHIRU YAMANE; (MUSIC/SOUND EFFECTS); O.KASAI; (PROGRAM/SOUND EFFECTS); IMOHORE IMAI(MIXER)
12. **-Musicians-** (5 lines): TAKAYUKI FUJII; (ELECTRIC GUITAR); NISHIMURA OH.YA.ZI.; (ELECTRIC GUITAR); KAHORI YAMANE(VOCAL)
13. **-Voice Coordinatar-** (1 lines): N.SAKAUE
14. **-Product Design-** (2 lines): SHOGO KUMASAKA; YUMIKO NOZAWA
15. **-Character Design & Illustration-** (2 lines):     & Illustrations-; AYAMI KOJIMA
16. **-Ending Theme-** (1 lines): 「I AM THE WIND"
17. **-Staff-** (18 lines): Produced by; RIKA MURANAKA; Music written by; RIKA MURANAKA; TONY HAYNES; JEFF LORBER; Arranged by; RIKA MURANAKA ; JEFF LORBER; Recorded by; JEFF LORBER; ROBERT CHINELLI; ERIC GREEDY AT JHL STUDIO; LARRY MAH AT MAD HATTER; RECORDING STUDIO; Mixed by; AL SCHMITT AT CAPITOL; RECORDING STUDIO
18. **-Musicians-** (9 lines): CYNTHIA HARRELL; (LEAD VOCAL/BACK CHORUS); JEFF LORBER(KEYBOARDS); RIKA MURANAKA(KEYBOARDS); NATE PHILLIPS(BASS); JOHN ROBINSON(DRUMS); MICHAEL TOMPSON(GUITAR); GERALD ALBRIGHT(SAX); LOUIS CONTE(PERCUSSION)
19. **-Special Thanks-** (13 lines): SIGERU FUKUTAKE; YUTAKA HARUKI; KEISUKE FUKUDA; MASA HRD; AKIRA YAMAOKA; SHOICHIRO HIRATA; TAKU URABE; HIROE NOGUCHI; Y.MAT; HIDEAKI SUGAYA; HIDEKI KASAI; K.FUKAMI; RMC STAFF
20. **-Translation-** (1 lines): AOISHI TRANSLATIONS
21. **-VO Talent Booking-** (1 lines): LATINA INTERNATIONAL CORP.
22. **-Recording Studio-** (1 lines): TOA STUDIO
23. **-Executive Producer-** (4 lines): KAZUMI KITAUE; (C)1997 KONAMI; ALL RIGHTS RESERVED.; DEVELOPMENT BY KCET.

## 2. PSP US roll

- How located: PS.ELF loads overlays via `disc0:/PSP_GAME/USRDIR/res/ps/PSPBIN/%s.bin`; the decomp's `pspeu` stsel target is `PSPBIN/sel.bin`. Searching it for the known strings found ONE credits blob; PACK_E/PACK `STP69.BIN` (identical in both dirs) bundles copies of sel.bin-like images. The decomp's `src/st/sel_psp/credits_data.h` is this very blob misdecoded with cutscene macros (SET_SPEED=ENTRY, SET_WAIT=SECTION, trailing END_CUTSCENE = zero padding) and used for all 5 languages (`credits_data_en/fr/sp/ge/it`, picked by `GetLangAt`); the US image holds only one copy.
- Data: `PSPBIN/sel.bin` offset `0xF150`, 1371 bytes, same opcode format as PS1 (same 00/01/02/03 values, same SJIS two-byte glyphs). Verified by exact re-encode. Decoded yaml: `psp_credits_decoded.yaml`.
- Confidence: high that this is the PSP SEL's roll (the decomp wires `D_psp_09285B98` to it and the PSP code reads it with the same opcodes). Medium on whether anything else is shown in-game (see section 6).

Blocks (83 text lines, 112 slots):

1. **(title card)** (2 lines): CASTLEVANIA; SYMPHONY OF THE NIGHT
2. **-Cast-** (8 lines): RYOUTAROH OKIAYU; KIYOYUKI YANADA; CHISA YOKOYAMA; NORIO WAKAMOTO; RIKA FUKAMI; MASAHARU SATOH; HEKIRU SHIINA; JYOUJI YANAMI
3. **-Staff-** (0 lines): 
4. **-Producer & Director-** (1 lines): TORU HAGIHARA
5. **-Assistant Director-** (1 lines): KOUJI IGA
6. **-Program-** (5 lines): TORU HAGIHARA; GAGENSAI.F; KOUJI IGA; KOUSUKE IWAKURA; HIROSHI YOGIASHI
7. **-Design-** (7 lines): REIKA BANDO; TOSHIHARU FURUKAWA; KIMIHIRO MORISHITA; HIROTO YAMAGUCHI; NOBUYA NAKAZATO; SHINICHIRO SHIMAMURA; NORIYOSHI SATO
8. **-CG-** (1 lines): KENICHIRO IMAIZUMI
9. **-Scenario-** (2 lines): KOUJI IGA; TOSHIHARU FURUKAWA
10. **-Sound Staff-** (5 lines): MICHIRU YAMANE; (MUSIC/SOUND EFFECT); O.KASAI; (PROGRAM/SOUND EFFECT); IMOHORE IMAI(MIX)
11. **-Musicians-** (5 lines): TAKAYUKI FUJII; (ELECTRIC GUITAR); NISHIMURA OH.YA.ZI.; (ELECTRIC GUITAR); KAHORI YAMANE(VOCAL)
12. **-Product Design-** (2 lines): SHOGO KUMASAKA; YUMIKO NOZAWA
13. **-Character Design & Illustration-** (1 lines): AYAMI KOJIMA
14. **-Special Thanks-** (16 lines): SIGERU FUKUTAKE; TAKASHI TATEISHI; YUTAKA HARUKI; HARUHIKO INABA; JUNICHI MURAKAMI; TARO MIYAKE; MASA HRD; AKIRA YAMAOKA; SHOICHIRO HIRATA; TAKU URABE; HIROE NOGUCHI; Y.MAT; HIDEAKI SUGAYA; HIDEKI KASAI; K.FUKAMI; RMC STAFF
15. **-Cooperation-** (4 lines): AONI PRODUCTION; ARTS VISION; １ＰPRODUCE; SIGMA SEVEN
16. **-Studio-** (2 lines): CENTRAL STUDIO; STUDIO＿
17. **-Executive Producer-** (4 lines): KAZUMI KITAUE; (C)1997 KONAMI; ALL RIGHTS RESERVED.; DEVELOPMENT BY KCET.

Also present but not referenced by PS.ELF strings I could find: a second blob "DRACULA X / NOCTURNE IN THE MOONLIGHT" in `disks/psp/hdbin/sel.bin` (0xB964, 1942 bytes) and inside `STP69.BIN`; it is the JP PS1-style roll: identical to the PSP roll above PLUS the Ending Theme / Staff / Musicians "I Am the Wind" block between Character Design and Special Thanks (`hd_nocturne_credits_decoded.yaml`).

## 3. Alignment

- The "I Am the Wind" block IS absent on PSP: exactly the three consecutive PS1 blocks `-Ending Theme-` (heading + `"I AM THE WIND"`), `-Staff-` (second one: Produced by RIKA MURANAKA; Music written by RIKA MURANAKA, TONY HAYNES, JEFF LORBER; Arranged by RIKA MURANAKA, JEFF LORBER; Recorded by JEFF LORBER, ROBERT CHINELLI, ERIC GREEDY AT JHL STUDIO, LARRY MAH AT MAD HATTER RECORDING STUDIO; Mixed by AL SCHMITT AT CAPITOL RECORDING STUDIO) and `-Musicians-` (CYNTHIA HARRELL ... LOUIS CONTE(PERCUSSION), 9 lines) = 31 text lines, 3 headings. It sits between Character Design and Special Thanks.
- Other PS1 blocks absent on PSP: `-Localization A.D.-` (HARRY INABA), `-Voice Coordinatar-` (N.SAKAUE), `-Translation-` (AOISHI TRANSLATIONS), `-VO Talent Booking-` (LATINA INTERNATIONAL CORP.), `-Recording Studio-` (TOA STUDIO).
- PSP-only blocks: `-Cooperation-` (AONI PRODUCTION, ARTS VISION, 1P PRODUCE, SIGMA SEVEN), `-Studio-` (CENTRAL STUDIO, STUDIO_). PSP-only lines: Program +HIROSHI YOGIASHI; Special Thanks +TAKASHI TATEISHI, HARUHIKO INABA, JUNICHI MURAKAMI, TARO MIYAKE, minus KEISUKE FUKUDA (16 vs 13 lines). Cast block is the Japanese cast (OKIAYU, YANADA, ...) instead of the English one. Renames: Programers->Program, Designers->Design, Scenario Writers->Scenario, EFFECTS->EFFECT, (MIXER)->(MIX).
- Order of common blocks: IDENTICAL. Common blocks (title, Cast, Staff, Producer & Director, Assistant Director, Programers/Program, Designers/Design, CG, Scenario, Sound Staff, Musicians, Product Design, Character Design & Illustration, Special Thanks, Executive Producer + (C) footer) appear in the same relative order on both. The decoded PSP roll shows NO reordering; the only "reorganization" after the removed block is that Special Thanks moves up and the PS1 trailing credits (Translation / VO Talent Booking / Recording Studio) are replaced by Cooperation / Studio. The user's "reorganized the blocks after it" is not corroborated by the data (see section 6).

## 4. Scroll timing

PS1 (`src/st/sel/cutscene.c`, credits entity step 1 + tail; `g_Dialogue.unk12` is a countdown, one script item per tick):
- Prims (0x20 of them) move `y0--` (1 px) every `clutIndex` reset: `clutIndex = 4`, decremented each tick -> 1 px per 4 ticks (15 px/s at 60 Hz).
- Each text line takes `unk12 = 76` ticks (= 19 px line pitch); ENTRY adds `0x18` (24 ticks = 6 px), SECTION adds `0x30` (48 ticks = 12 px); SUBTEXT adds 0. Characters are drawn one per tick inside that window.
- END_CREDITS: `unk12 = 0x400` (1024 ticks = 256 px of blank scroll) then the entity returns 1.
- Simulated (my faithful tick simulation of these rules): END opcode reached at 15320 ticks = 255.3 s, roll returns at 16344 ticks = 272.4 s @60 Hz (song 280.3 s: ~8 s of tail). Total scroll 3793 px.

PSP (`src/st/sel_psp/cutscene.c` ~line 910-1105, decomp pspeu; I confirmed the US sel.bin contains the same constants: table `{6,5,6,5}` as u32 at 0x2F2A0 and immediates 0x69/0x21/0x42/0x300):
- Line `0x69` (105) ticks, ENTRY `+0x21` (33), SECTION `+0x42` (66), END wait `0x300` (768); scroll period from table `{6,5,6,5}` = 5.5 ticks/px (10.9 px/s) vs 4 on PS1, i.e. 27% slower, same pixel layout. Simulated PSP roll: END at 15834 ticks (263.9 s), returns at 16602 ticks = 276.7 s @60 Hz, matching the 276 s song. That 60 Hz match strongly supports the tick=1/60 s assumption. (From decomp code + simulation, not measured from a running game.)

Required speed for a PS1-block roll with the song block removed (PSP order == PS1 order):
- Option A (only I Am the Wind removed): 2900 px to the END opcode. At PS1 speed it ends after 210 s (66 s early). For 276 s: 5.25 ticks/px (11.4 px/s) keeping the 256 px end wait; or exactly the PSP constants (105/33/66, `{6,5,6,5}`) with end wait `0x252` (594) -> 276.0 s; with the PSP's own 0x300 it is 278.9 s.
- Option B (also drop the 5 PS1-only blocks absent on PSP): 2504 px; 6.0 ticks/px (10.0 px/s) with 256 px end wait.
Scaling rule when changing speed: line wait = 19*r, ENTRY = 6*r, SECTION = 12*r, scroll period = r (use a period table for fractional r).

## 5. Proposal for "Ending = PSP" roll (PS1 blocks only)

Order (Option A, recommended; identical to PSP order for the common blocks): title, Cast, Staff, Producer & Director, Assistant Director, Localization A.D., Programers, Designers, CG, Scenario Writers, Sound Staff, Musicians, Voice Coordinatar, Product Design, Character Design & Illustration, Special Thanks, Translation, VO Talent Booking, Recording Studio, Executive Producer + Konami footer.
- Join: after AYAMI KOJIMA keep the two blank slots, then `SUBTEXT 15` before `-Special Thanks-` (as PSP; the PS1 original has SECTION 15).
- Option A: 81 text lines (original 112, -31), 112 opcode slots (orig 150), **1397 bytes** (orig 1968, -571). File `table_A.bin`, yaml `credits_psp_order_A.yaml`.
- Option B (A minus Localization A.D., Voice Coordinatar, Translation, VO Talent Booking, Recording Studio; trailing blanks match the PSP's): 71 text lines, 97 slots, **1205 bytes**. File `table_B.bin`, `credits_psp_order_B.yaml`.
- Code implication: the credits entity hard-codes 76/0x18/0x30/4/0x400 and reads `cutscene_credits`; both the table pointer and these constants need to become variables for the PSP-ending variant. 1397 B fits in the 1968 B original slot only if the original is shared; a separate second table needs its own ~1.4 KB of spare SEL space.

## 6. Not verified

- The user's claims (new voice cast, port staff credits, reorganised blocks, "slightly" changed speed) are NOT found in any PSP data I could decode: no English cast names (Belgrade, McCulloch, ...) exist uncompressed anywhere in the 1.1 GB ISO, the only roll in `PSPBIN/sel.bin` has the Japanese cast and no port staff. The video may show a different roll (compressed/other pack data, other region, or the DXC-level credits), or a mismatch of memory. The speed change I find is 27% slower, not slight.
- Which of the sel.bin blob vs the STP69 / hdbin "DRACULA X" blob the running game uses (I inferred PSPBIN from PS.ELF's format string and the decomp).
- 60 Hz tick rate for both games, and PS1 SEL running the credits at that rate (supported by the 276.7 s vs 276 s PSP match, not measured).
- The simulation assumes `unk12`/`clutIndex` start at 0 and ignores the ticks lost on opcode early-returns (+/- a few ticks); the 3793 px vs 15320/4 gap is that effect.
- PS.ELF main-game flow (when the roll is entered, what the music cue/fade timing around it is) was not analysed; PSP US sel.bin code was checked only for constants, not disassembled.
