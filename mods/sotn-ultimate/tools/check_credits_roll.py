#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Host-side tick simulation of the staff roll (src/st/sel/cutscene.c,
func_801B79D4 steps 0, 1 and 7) for both settings of Ending (include/
game_mod.h MOD_CREDITS_PSP_*), on the tables the build uses
(gen_credits_psp.py), and the checks that go with it:

  PS1 setting: retail timing, unchanged (76 ticks a line, +24 an ENTRY,
    +48 a SECTION, 1 px per 4 ticks, 1024 ticks at the END); the simulated
    totals are pinned below (they were the same before the option existed);
    cutscene.c must still carry those literals in its retail branches.
  PSP setting: the roll lasts as long as "Mournful Serenade" (276.0 s) within
    TOLERANCE_S, every line is 19 px apart (+6 / +12) and the roll
    stops (the END wait does not scroll) with the same final page as the PS1's.

Tick model (60 Hz): one script item per entity tick; the tail of step 1
(line timer, scroll) runs on every tick except those that read a SUBTEXT /
ENTRY / SECTION / END opcode (they return early), so a line's timer and the
scroll count the same ticks. The END wait does not scroll: the last
page (the Konami lines) stays up for it.

Usage: check_credits_roll.py [-v] [--build]
  --build also checks the built SEL.BIN / SELRIC2.BIN: the table is in their
  dead config copy at file offset 0x25FC (its symbol too), padded with zeros
  to MOD_CREDITS_PSP_AREA, and the text packs' chunks start after it."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_credits_psp as g

ROOT = g.ROOT
SONG_S = 276.0       # Mournful Serenade (one-shot, step 2)
SONG_PS1_S = 280.3   # I Am the Wind
TOLERANCE_S = 1.5
HZ = 60

# retail, pinned (simulated from the retail table and the retail constants)
PS1_PIN = {"ticks_to_end": 15242, "ticks": 16266, "scroll_px": 3774}


def defines():
    t = open(os.path.join(ROOT, "mods/sotn-ultimate/include/game_mod.h")).read()
    return {k: int(v, 0) for k, v in re.findall(r"#define (MOD_CREDITS_PSP_\w+) +(\w+)", t)}


def defines_area():
    t = open(os.path.join(ROOT, "mods/sotn-ultimate/include/game_mod.h")).read()
    return int(re.search(r"#define MOD_CREDITS_PSP_AREA (\w+)", t)[1], 0)


def params(psp):
    """The values cutscene.c uses: line, entry, section (ticks or px), reload
    pattern (indexed by scroll count & 3), end wait (ticks), unit."""
    if not psp:
        return dict(line=76, entry=24, section=48, reload=[4, 4, 4, 4], end=0x400, px=False)
    d = defines()
    lo, sh = d["MOD_CREDITS_PSP_PERIOD_LONG"], d["MOD_CREDITS_PSP_PERIOD_SHORT"]
    return dict(line=d["MOD_CREDITS_PSP_LINE"], entry=d["MOD_CREDITS_PSP_ENTRY"],
                section=d["MOD_CREDITS_PSP_SECTION"], reload=[lo, sh, sh, sh],
                end=d["MOD_CREDITS_PSP_END_TICKS"], px=True)


def simulate(tab, p):
    pos = 0
    # step 0 (tick 0): the first line is read at once, up to its SUBTEXT
    while tab[pos] != 1:
        pos += 1
    pos += 2
    tick, nchary, unk12, clut, scrolled, phase = 0, 0, 0, 0, 0, 0
    spawns = []        # (tick, scrolled px) of each line's window
    last_text = None   # scrolled px when the last glyph's line spawned
    first = True       # step 0 (tick 0) falls into the tail too
    while True:
        if not first:
            tick += 1
        if nchary and not first:
            op = tab[pos]
            pos += 1
            if op == 0:
                return dict(ticks_to_end=tick, ticks=tick + p["end"], scroll_px=scrolled,
                        spawns=spawns, last_text_spawn=last_text)
            if op in (1, 2, 3):
                pos += 1
                if op == 2:
                    unk12 += p["entry"]
                if op == 3:
                    unk12 += p["section"]
                nchary = 0
                continue
            if op & 0x80:
                pos += 1
            last_text = spawns[-1][1]
        # tail
        if not unk12:
            nchary = 1
            unk12 = p["line"]
            spawns.append((tick, scrolled))
        if not p["px"]:
            unk12 -= 1
        if not clut:
            scrolled += 1
            if p["px"] and unk12:
                unk12 -= 1
            clut = p["reload"][phase & 3]
            phase += 1
        clut -= 1
        first = False


def report(tab, psp):
    p = params(psp)
    r = simulate(tab, p)
    r["roll_s"] = r["ticks"] / HZ
    r["end_s"] = r["ticks_to_end"] / HZ
    # the roll stops at the END (step 7 does not scroll): the last text line
    # then sits this many px above where it appeared (the screen's bottom)
    r["rest_px"] = r["scroll_px"] - r["last_text_spawn"]
    return p, r


def main():
    verbose = "-v" in sys.argv
    full, psp = g.tables()
    fail = []
    out = {}
    for name, tab, is_psp in (("PS1", full, False), ("PSP", psp, True)):
        p, r = report(tab, is_psp)
        out[name] = (p, r)
        print("%s roll: %d lines, %d px scrolled, END read at %.1f s, last line stops %d px above its start, roll returns at %.1f s (%d ticks)" % (
            name, len(r["spawns"]), r["scroll_px"], r["end_s"], r["rest_px"], r["roll_s"], r["ticks"]))
        if verbose:
            print("   avg px/line %.3f" % ((r["spawns"][-1][1] - r["spawns"][1][1]) / (len(r["spawns"]) - 2)))
    p1, r1 = out["PS1"]
    for k, v in PS1_PIN.items():
        if r1[k] != v:
            fail.append("PS1 roll %s is %d, retail %d" % (k, r1[k], v))
    p2, r2 = out["PSP"]
    if abs(r2["roll_s"] - SONG_S) > TOLERANCE_S:
        fail.append("PSP roll lasts %.2f s, song %.1f s (+-%.1f)" % (r2["roll_s"], SONG_S, TOLERANCE_S))
    if abs(r2["rest_px"] - r1["rest_px"]) > 1:  # (+-1: the scroll phase)
        fail.append("PSP roll stops with its last line at %d px, the PS1's at %d" % (r2["rest_px"], r1["rest_px"]))
    # the PSP roll's pace: every line starts 19 px (+6 / +12) after the last
    if not (p2["line"] == 19 and p2["entry"] == 6 and p2["section"] == 12):
        fail.append("PSP roll must keep the PS1's pixel layout (19 / 6 / 12 px)")
    # no overlap: lines are spawned by scrolled pixels, so line n+1 starts
    # >= 19 px under line n whatever the tick rate
    px = [s[1] for s in r2["spawns"]]
    if min(b - a for a, b in zip(px, px[1:])) < 19:
        fail.append("PSP roll: two lines start less than 19 px apart")
    # cutscene.c keeps the retail literals in its retail branches
    src = open(os.path.join(ROOT, "src/st/sel/cutscene.c")).read()
    for lit in (": 76;", ": 0x18;", ": 0x30;", ": 0x400;", "clutIndex = 4;"):
        if lit not in src:
            fail.append("cutscene.c lost the retail literal '%s'" % lit)
    if "--build" in sys.argv:
        area = defines_area()
        m = re.search(r"0x([0-9a-f]+)\s+cutscene_credits_psp\n", open(os.path.join(ROOT, "build/us/stsel.map")).read())
        if not m or int(m[1], 16) != 0x80180000 + 0x25FC:
            fail.append("cutscene_credits_psp is not at 0x%X in stsel.map" % (0x80180000 + 0x25FC))
        for name in ("SEL.BIN", "SELRIC2.BIN"):
            f = open(os.path.join(ROOT, "build/us", name), "rb").read()
            if f[0x25FC:0x25FC + area] != psp + bytes(area - len(psp)):
                fail.append("%s: the table at 0x25FC is not credits_psp.bin + zero pad" % name)
        # (SEL's text pack reader follows the table: MOD_TEXT_CD_AREA)
        cd = int(re.search(r"#define MOD_TEXT_CD_AREA (\w+)", open(os.path.join(
            ROOT, "mods/sotn-ultimate/include/game_mod.h")).read())[1], 0)
        print("     SEL table: %d of %d bytes used, %d spare before SEL's text pack reader (%d B) and "
              "the text packs (0x3000)" % (len(psp), area, 0x3000 - 0x25FC - cd - len(psp), cd))
    for f in fail:
        print("FAIL", f)
    if fail:
        sys.exit(1)
    print("OK   credits roll: PS1 unchanged (%d ticks), PSP %.1f s vs song %.1f s" % (r1["ticks"], r2["roll_s"], SONG_S))


if __name__ == "__main__":
    main()
