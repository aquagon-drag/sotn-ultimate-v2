# SOTN JP (SLPM-86023 Rev 2) English retranslation patch: technical characterisation

The patch is RHDN #1427 (Gemini, hacking; Tom, translation editing); the user confirmed this. The base image is Rev 2, and sotn-decomp's "jp12" build hashes match our Rev 2 DRA/NO0/SEL/WRP/RIC byte for byte.
Everything below comes from comparing extract/jp (patched) with extract/jp2 (Rev 2). Confidence labels: **[V]** verified from code or bytes, **[I]** inference, **[?]** unverified.

## 1. Language and identity
* **[V] The dialogue, descriptions, menus and narration are in ENGLISH.** I decoded them with the tables below. Samples:
  * ST0 prologue: "Begone! This world was not meant for the likes of you!" / "My own powers did not bring about my resurrection. It was greed, the greed of you men which summoned me back." / "Such a selfish claim! Humanity is guided by our shared principles."
  * NZ0 (Alucard/Maria): "We meet again, Alucard." / "Did you say your name was Maria?" / "You're still not quite the social type." / "Dracula's castle was spawned out of chaos. It is not bound to a single form."
  * Item descriptions (DRA): "A shield bearing a heart-shaped crest", "Strawberry shortcake with whipped cream (consumable)", "A curved sword from India", "Strong against flame, thunder, and frost... probably".
  * ST0 also carries the **English prologue narration scroll**: "After a series of exhausting battles, Richter Belmont finally succeeded in destroying Count Dracula, ... And perhaps only the moon hovering in the dark night knows the truth that awaits them." This is the JP narration text, which bears on the "restore JP narration" goal.
* **[V] Italian leftovers** show that the engine is shared with Gemini's 2007 Italian patch: READMEI.PDF; DRA 0x3C980 "...nte tutti i tasti", 0x3C943 "...enuto"; DRA 0x3CFC7-0x3D06C hold unreferenced Italian save prompts ("Sì/No", "Ingresso 1/2", encoded with a different DTE table so they are garbled now).
* **[V] The boot executable has a new splash program.** `start` (0x80010DFC) jumps to 0x80033A00 → 0x8003A2CC. That routine shows 3 LZ16-compressed TIMs (0x80034088, 0x800360A0, 0x80037814) and then returns to the normal boot. The program is self-contained: it has its own libgpu copy, an LZ16 decoder at 0x80039EA4 and its own font/charset. The third TIM is an English anti-resale notice ("If you bought this... ripped off ... for free..."). PNGs: gfx/splash_*.png.
* [?] I found no version or credit string ("v1.2") in the exe or DRA. The credits are probably inside the splash TIMs, which I only read as ASCII art.

## 2. Text encodings (decoder: scripts2/sotn_retrans_text.py)
**ENC12 (8x12 VWF)** is used for item, accessory, spell and relic descriptions, relic and spell names, cutscene dialogue, prologue narration, Librarian monster descriptions, save/memory-card messages, menu help lines and "Obtained X" popups.
* 0x00 = end; 0x01 = newline.
* 0x02-0x18 = cutscene opcodes (in scripts), with argument counts as in sotn-decomp include/cutscene.h: 02/03/10/11/18 take 1 byte, 05/07/09/14 take 2, 0C/0E/0F take 4, 13 takes 5.
* 0x20-0x7F = glyph index (b-0x20). Order: ` !"(),'` àèéìòùÈ `:?-.` 0-9 A-Z a-z. Then 0x70 '+', 0x72 ↓, 0x73 ↑, 0x74 →, 0x75 ↘, 0x77 '%'. 0x71, 0x76 and 0x78-0x7F are icons/unknown.
* **0x80-0xFF = DTE**: one byte expands to two glyph codes from the table at DRA 0x40C50 (128 pairs: "e ", "th", " t", ...). This is the undeciphered 0x80+ code. It is compression, not 2-byte glyph indices. Table: font/vwf12_dte_table.csv.

**ENC8 (8x8 VWF)** is used for equipment and accessory names, enemy names, g_MenuStr (status/config words, boss-record list), spell command strings, cutscene actor names and SEL names.
* 0x01-0x5E = ASCII-0x20; 0x5F = space; 0x00 (or 0xFF) = end.
* Repurposed slots: 07 ',', 1B ''', 3B à, 5B ä, 5D ū. Read from glyph shapes only: 20 È, 3C-40 èéìòù, 5C ō, 5E ü.
* 0x60-0x6F are pair-ligature tiles: 60 ae, 61 ë, 62 il, 63 ll, 64 li, 65 'a ', 66 'e ', 68 'o ', 69 ' d', 6A el, 6C di, 6D ' c', 6E ti, 6F ri. 0x6B is unknown.
* DF-E7 are the charge mark and arrows ←↖↑↗→↘↓↙ (verified against JP combos).

**Other formats:**
* The prologue narration lines in ST0 start with a byte X (pixel x offset; the code stores it as X+0x800).
* SEL credits use another code (uppercase ASCII+5) **[I]**.

**Dumps (UTF-8):**
* text/DRA.BIN.tsv: 1,288 entries with category, index, field, offset, length, encoding, text and pointer sites (data words and lui/addiu pairs).
* text/<overlay>.txt: 59 files. Each changed region is decoded with opcode tags and labelled code, text or "non-text".

**DRA pointer tables (file offsets):**

| Table | Offset | Layout |
|---|---|---|
| Equipment | 0x4B70 | ×217, stride 0x34, {name ENC8, desc ENC12} |
| Accessories | 0x7784 | ×90, stride 0x20 |
| Spells | 0x8418 | ×28, stride 0x1C, {name12, combo8, desc12} |
| Relics | 0x8728 | ×30, stride 0x10 |
| Enemies | 0x8908 | ×400, stride 0x28, name ENC8 |
| g_MenuStr | 0x82C4 | ×80 |
| Menu help | 0x2D48 | |
| Save messages | 0x3CEA8 | ×22; widths for centring at 0x3CF00 |

String pool: 0x3D468-0x40700.

**US comparison (DRA):**

| Pool | US | Patched JP |
|---|---|---|
| Equipment names | 170 unique, 1,827 B | 170, 1,873 B |
| Equipment descriptions | 166, 4,410 B (plain ASCII, 0-terminated) | 170, 4,106 B (DTE) |
| Accessory names | 87, 1,030 B | 90, 1,110 B |
| Accessory descriptions | 84, 2,130 B | 90, 1,742 B |
| Enemy names | 150, 1,569 B | 150, 1,589 B |

US names are ASCII-0x20 with 0xFF terminators.

## 3. Fonts (font/)
* **[V] 8x12 VWF**: 1bpp, 12 bytes per glyph, 112 glyphs (codes 0x20-0x8F) at DRA 0x40710. Advance widths: 112 bytes at DRA 0x40DC0 (font/vwf12_widths.csv). Rendering adds a drop shadow (colour 1 right and below, colour 6 for the body). **Glyph height is 12 px**; it uses 13 px with the shadow, inside an 8x16 VRAM cell. Sheet: font/vwf12_font_patched_DRA_0x40710.png.
* **[V] 8x8 VWF**: the F_GAME/F_GAME2 font page at file 0x30000 (128x128 4bpp, CLUT 150), extended with ligature, accent and arrow tiles. Widths: 112 bytes at DRA 0x40D50 (font/vwf8_widths.csv). **Glyph height is 8 px.** Before/after sheets: font/vwf8_fgame_font_{jp2,jp,us}.png. The patch also changed CLUT 161 (F_GAME 0x41422) **[I: text colour]**.
* The splash program has its own small font (charset string at 0x80040FE0), used for its own screen only.
* Glyph height per text class: names, menus and enemies use 8 px; everything listed under ENC12 uses 12 px.

## 4. Code (asm/; annotated _diff.asm files show patched code then JP original)
* **VWF12_DrawChar(ch,x,y)** at 0x801068B4 (DRA) **replaces JP func_80106A28**, the BIOS-Krom2RawAdd kanji fetch that overlays reach through g_api.func_80106A28. State: 0x800E0700/04 = VRAM x/y base, 0x800E0708 = 64-byte cell buffer (0x80082FEC or 0x8007EFEC), 0x800E070C = sub-cell pixel offset.
  * It expands the 1bpp glyph into 4bpp rows with a shadow (0x80106A00), shifts it by the pen offset and ORs it into the cell buffer.
  * It uploads the 8x16 cell with LoadImage (0x80106AB4 → 0x8001112C) and DrawSync.
  * When the pen passes 8 px, it uploads the spill-over into the next cell and returns 2 (VRAM halfwords).
  * So text is **composited into a VRAM texture strip**; it is not one sprite per glyph.
* **Callers:**
  * VWF12_DrawString 0x800F9B28 (DTE expansion, 0x01 newline; at the JP DrawString slot, with the wrapper 0x800F9C34 kept).
  * Save-menu printer 0x800CDDF0/0x800CDEF4: HandleSaveMenu calls were repointed to message indices.
  * StrWidth 0x800DC714; DrawCharAtPixel 0x800DC7AC (used by ST0 narration and dialogue).
  * Direct `jal` calls in LIB (shop) and SEL.
* **VWF8**: 0x8002BA18 in the boot exe, written over the unused libgpu debug-font data. It is the item-name popup: one GPU sprite per glyph from the F_GAME font page, advanced by the width table. 0x8002BE18 truncates a VWF12 string to a maximum width and appends "...".
* **Overlay hooks [V]**: every stage and boss overlay's own copy of sotn-decomp `BlitChar` (st/blit_char.h; 980 B, 709 B in TE*/BO*) is replaced by `j 0x8002BA18` plus zero fill, which frees about 970 B per overlay. The ~216 B and 19 B hooks patch EntityRelicOrb (st/e_collect.h): it builds "Obtained "+relic name, centres it with (256-width)/2 and calls VWF12_DrawString.
* Bigger rewrites:
  * SEL: 8 KB at 0x30354 plus several smaller ranges (file select and name entry).
  * LIB: about 3 KB of code (shop and librarian).
  * DRA menu hooks: 0x56730-0x5BE00, mostly 8x8 menu drawing, listed in asm/DRA_menu_hooks.asm but not analysed instruction by instruction.
* Matching to US function names is by sotn-decomp file and role, not by binary match **[I]**.

## 5. Graphics text
* **[V] The area-name banners are compressed graphics in the stage overlays.** Each is a gfx-bank entry {x=0x100, y=0x40, 128x128 4bpp} in the overlay header, compressed with the standard SOTN nibble codec (DecompressData; ported in scripts2/sotn_cmp.py).
  * The patch replaced these banners in ARE, CAT, CHI, DAI, DRE, LIB, NO0, NO1, NO2, NO4, NZ0, NZ1, ST0 and TOP.
  * It emptied the second bank (y=0x60, a 9-byte stream) in DRE, NZ1 and LIB (LIB 1,263 B → 145 B). This is the "expand space" hack.
  * Before and after PNGs: gfx/banner_*_{JPorig,patched}.png (grayscale; the real CLUT was not applied). Index: gfx/banners_index.tsv.
* F_GAME/F_GAME2 0x2C000-0x2FFFF ("logo1/logo2", 8bpp, CLUT 208) changed: gfx/F_GAME_*_logo_*.png.
* F_TITLE0 has 8 changed 0x2000 blocks and F_TITLE1 has 3 (title-screen graphics). They are exported as raw grayscale 4bpp and 8bpp: gfx/F_TITLE*.png. CLUT not identified.

## 6. Ultimate "JP script add-on" (cross-check)
[V] ult/ST/ST0/ST0.BIN 0x27CA9 holds the same English dialogue as **plain ASCII in the US cutscene format**, re-wrapped to shorter lines ("Begone! / This world / was not meant for the / likes of you!"). It uses US opcodes and the US font, with no DTE or VWF.

## 7. Not verified / open
1. I never looked at the PNGs; I checked them only as ASCII art. These need a visual check: ENC8 accent slots 20/3C-40/5C/5E, ligatures 61/67/69/6D, 0x6B, ENC12 0x71/0x76/0x78-0x7F, the banner wording, and the F_TITLE content and palettes.
2. The overlay text dumps use heuristics to set region bounds and choose the encoding. Some regions mix leftover JP bytes or graphics that are shown as "[low score]". The LIB monster list is decoded in script mode and contains tag noise. A proper fix is to walk each overlay's script and string pointer tables.
3. DRA menu hooks, the SEL 8 KB and the LIB code are disassembled but not annotated. I also did not confirm whether the cutscene box went from 3 to 4 lines at 12 px.
4. I found no version or credit string. Running the image in an emulator would settle this and the visual items above.
5. The SEL credits encoding (ASCII+5) is a guess.
6. I did not check every overlay for non-banner text graphics outside the gfx-bank entries.
