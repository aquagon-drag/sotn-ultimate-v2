#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The staff roll of the "Ending = PSP" option (include/game_mod.h
MOD_ENDING_PSP, src/st/sel/cutscene.c).

The PSP port's roll leaves out the credit for "I Am the Wind" (it plays
"Mournful Serenade" instead), so with that option SEL rolls a copy of the
PS1 table without the three consecutive blocks that credit the song:
-Ending Theme-, the second -Staff- (Produced / Music written / Arranged /
Recorded / Mixed by) and the second -Musicians- (CYNTHIA HARRELL ... LOUIS
CONTE), 31 text lines. Everything else stays in the PS1's order and words.

The copy is derived here from assets/st/sel/credits.yaml, the table that
makes src/st/sel/gen/credits.h, so the two cannot drift apart: the same
encoding as tools/sotn-assets/assets/credits/handler.go (checked against the
retail bytes of SEL.BIN: the full yaml must encode to them), minus the rows
from the Ending Theme heading up to Special Thanks, whose heading then
follows the Character Design block after a SUBTEXT 15 (the PSP roll's own
gap; the retail's 18 led to the Ending Theme heading).

Usage: gen_credits_psp.py            writes build/us/credits_psp.bin (and
                                     touches src/st/sel/config_us.c when it
                                     changed: that file .incbins it)
       gen_credits_psp.py --check    verifies only
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
YAML = os.path.join(ROOT, "assets/st/sel/credits.yaml")
RETAIL_SEL = os.path.join(ROOT, "disks/us/ST/SEL/SEL.BIN")
RETAIL_OFF, RETAIL_LEN = 0xBC54, 1968
OUT = os.path.join(ROOT, "build/us/credits_psp.bin")
CONFIG_C = os.path.join(ROOT, "src/st/sel/config_us.c")

OPS = {"END_CREDITS": 0, "CREDITS_SUBTEXT": 1, "CREDITS_ENTRY": 2, "CREDITS_SECTION": 3}
FIRST, LAST = "-Ending Theme-", "-Special Thanks-"
JOIN_SUBTEXT = 15


def rows(path=YAML):
    out = []
    for line in open(path, encoding="utf-8"):
        m = re.match(r'\s*- \[(\w+)(?:, (.*))?\]\s*$', line)
        if not m:
            continue
        op, arg = m.group(1), m.group(2)
        if op == "TEXT":
            assert arg.startswith('"') and arg.endswith('"'), line
            arg = arg[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        out.append((op, arg))
    return out


def encode(rs):
    b = bytearray()
    for op, arg in rs:
        if op == "TEXT":
            b += arg.encode("latin-1")
        elif op == "BYTE":
            b.append(int(arg, 0))
        else:
            b.append(OPS[op])
            if op != "END_CREDITS":
                b.append(int(arg, 0))
    return bytes(b)


def psp_rows(rs):
    t = [i for i, r in enumerate(rs) if r == ("TEXT", FIRST)]
    s = [i for i, r in enumerate(rs) if r == ("TEXT", LAST)]
    assert len(t) == 1 and len(s) == 1 and t[0] < s[0], (t, s)
    # [.. AYAMI KOJIMA, SUBTEXT 0, SECTION 0, SUBTEXT 18, "-Ending Theme-" ..]
    assert rs[t[0] - 1] == ("CREDITS_SUBTEXT", "18"), rs[t[0] - 1]
    return rs[:t[0] - 1] + [("CREDITS_SUBTEXT", str(JOIN_SUBTEXT))] + rs[s[0]:]


def tables():
    """(retail table bytes, PSP-ending table bytes), from the yaml."""
    rs = rows()
    return encode(rs), encode(psp_rows(rs))


def area():
    t = open(os.path.join(ROOT, "mods/sotn-ultimate/include/game_mod.h")).read()
    return int(re.search(r"#define MOD_CREDITS_PSP_AREA (\w+)", t)[1], 0)


def main():
    full, psp = tables()
    if len(psp) > area():
        sys.exit("gen_credits_psp: %d bytes, past MOD_CREDITS_PSP_AREA (%d)" % (len(psp), area()))
    retail = open(RETAIL_SEL, "rb").read()[RETAIL_OFF:RETAIL_OFF + RETAIL_LEN]
    if full != retail:
        sys.exit("gen_credits_psp: credits.yaml does not encode to the retail table")
    dropped = sum(1 for r in rows() if r[0] == "TEXT") - sum(1 for r in psp_rows(rows()) if r[0] == "TEXT")
    assert dropped == 31, dropped
    print("credits_psp: %d bytes (retail table %d), 31 text lines dropped" % (len(psp), len(full)))
    if "--check" in sys.argv:
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    old = open(OUT, "rb").read() if os.path.exists(OUT) else None
    if old != psp:
        open(OUT, "wb").write(psp)
        os.utime(CONFIG_C, None)  # config_us.c .incbins it


if __name__ == "__main__":
    main()
