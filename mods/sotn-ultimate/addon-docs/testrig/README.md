# Test rig (cloud workspace or any Linux box)

Built on 2026-11-14 to find the Retrans pack load bug (step 6f). Two emulators, both scriptable, no GUI needed.
Paths in the scripts are the ones of that session (`/home/claude/emu`, `/home/claude/ds`); adjust them.

## Getting an image without transferring 700 MB at once
`_builds` on Gerardo's PC holds `baseline.part00/01` and one `.secpatch` per step (u32 LE sector index + 2352 bytes
per changed sector). Concatenate the parts and apply the patches in order (step1 … step6e, step6f) to get any step's
image; compare the MD5 with the `.bin` on the PC. `secedit.py` patches bytes of a file inside a MODE2/2352 image,
repairs the sector's EDC/ECC (Mode 2 Form 1) and writes a `.secpatch`.

## 1. DuckStation headless (the reference: it is what Gerardo tests on)
- `DuckStation-x64.AppImage` from the GitHub release page, `--appimage-extract`; put `portable.txt`, `settings.ini`
  (his, with `Renderer = Software`, audio `Backend = Null`, `LogToFile = true`, `EnableGDBServer = true`),
  `bios/SCPH1001.BIN` and `memcards/` next to `usr/bin/duckstation-qt`.
- `Xvfb :7 -screen 0 1024x768x24 &` (apt: `xdotool libegl1 libopengl0 libxcb-cursor0 …`). Background processes die
  between turns: restart Xvfb when `xdotool` cannot open the display.
- `prep.sh <cue> <Recompiler|Interpreter>` boots to the file-select screen; `k.sh <key> [hold] [wait]` presses a key
  (his bindings: x = Cross, Return = Start, arrows); `import -window root shot.png` for a screenshot.
- `run.sh <cue> <tag> <mode>` loads the first save and writes the filtered CD log to `/tmp/<tag>.log`.
- `watch.py <seconds> Z2,<addr>,<len>` attaches to the GDB server (port 2345), sets a write watchpoint, presses
  Cross and prints pc / ra / registers and the loader's state block at every hit. `gdbc.py` is the tiny client
  (memory reads, registers, continue).

## 2. pcsx_rearmed core driven from Python (fast: ~500 fps, save states, frame stepping)
- `git clone --recurse-submodules https://github.com/libretro/pcsx_rearmed`, apply `pcsx_rearmed_debug_hooks.patch`
  (write-watch log in psxmem.c, CD command log in cdrom.c, exported symbols), then
  `make -f Makefile.libretro DYNAREC=0 HAVE_CHD=0`.
- `rig.py`: `Emu(cue, card, opts={'pcsx_rearmed_memcard1':'libretro'})`, `run(n, *buttons)`, `tap`, `r8/r32/rb`,
  `watch(lo, hi)` + `watch_new()`, `cd_new()` + `cdfmt`, `save/load` (states), `shot` (PNG).
- Caveats: loading his memory-card saves gives "Loading error" here (new games work); its CD timing differs from
  DuckStation's, so a bug that depends on what runs in a given frame may not show (the 6f bug did not).

`mdis.py <DRA|SEL|MAIN> <from> <to>` disassembles the binaries extracted from an image (capstone).
