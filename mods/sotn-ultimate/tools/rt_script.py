#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""SOTN Ultimate (step 6b, cutscenes): the retranslation's cutscene text.

Under Script = Retrans the cutscenes show the retranslation patch's
dialogue, drawn with its 12 px font, timed to the Japanese voices (one copy
per script, used with every dub; Gerardo, 2026-11-16).

The text is read from the builder's patched Japanese disc (disks/jpre/ST/*
and BOSS/*, as the Librarian's: never committed): the patched overlays keep
the JP script structure with ENC12 text (glyph codes 0x20-0x7F, 0x80-0xFF a
DTE pair from the patched DRA's table) and the US opcodes 0x00-0x18. Each
voiced line is found by its PLAY_SOUND id; JP id + 2 = PS1 id (as the PSP's).

  rt_script.py   report: every PS1 cutscene voice line and its retranslated
                 text, its lines' widths in the 12 px font
                 (build/us/rt_script/report.txt)
"""
import os
import re
import sys

import psp_script as ps
import text_rt

ROOT = ps.ROOT
JPRE = os.path.join(ROOT, "disks/jpre")
WORK = os.path.join(ROOT, "build/us/rt_script")
REPORT = os.path.join(WORK, "report.txt")
# PS1 voice id -> the patched JP script's PLAY_SOUND id where it is not
# PS1 - 2: DRE's Succubus line and BO6's swapped branches as the PSP's
# (psp_script.py TEXT_OVERRIDE), TOP's 0x3F0 (Richter, "What have I been
# doing...?": JP 0x3F6; Gerardo checked both in the patched game). CEN's
# Maria lines follow PS1 - 2 (the PSP's restructure is the PSP's own).
# Voices with no text in the scripts: DRE 0x392 (subtitled later), LIB
# 0x3B9, BO2 0x394 (laughter), BO6 0x3E1 (Richter's death scream)
RT_ID = {0x38B: 0x38A, 0x3D4: 0x3D4, 0x3D6: 0x3D2, 0x3F0: 0x3F6}
# the dialogue's text strip: 192 px (psp_script.py MAX_COLS: 8 px cells
# from x = 8, the box ends at 248)
LINE_PX = 192


def jp_overlay(retail_rel):
    p = os.path.join(JPRE, retail_rel)
    return open(p, "rb").read() if os.path.exists(p) else None


def rt_segments(b, jp):
    """patched JP voice id -> [items], items: ('T', str) / ('BR',) / ('W', n), from
    the patched JP overlay b (ENC12 text, DTE through jp, a text_rt.Jp)"""
    found = {}
    for m in re.finditer(rb"\x09([\x30-\x53])(.)", b, re.S):
        sid = (m.group(1)[0] << 4) | m.group(2)[0]
        if not (ps.VOICE_LO - 2 <= sid <= ps.VOICE_HI):
            continue
        i, items, bad = m.end(), [], False
        while i < len(b):
            c = b[i]
            if c >= 0x20:
                s = ""
                while i < len(b) and b[i] >= 0x20:
                    c = b[i]
                    try:
                        if c >= 0x80:
                            x, y = jp.dte[c - 0x80]
                            s += jp.g12(x) + jp.g12(y)
                        else:
                            s += jp.g12(c)
                    except ValueError:
                        bad = True
                        break
                    i += 1
                items.append(("T", s))
                if bad:
                    break
                continue
            name = ps.NAMES.get(c)
            if name is None or name in ps.SEG_END or name == "SCRIPT_SWITCH":
                break
            if name == "LINE_BREAK":
                items.append(("BR",))
            elif name == "SET_WAIT":
                items.append(("W", b[i + 1]))
            i += 1 + sum(ps.OPS[name][1])
        text = "".join(x[1] for x in items if x[0] == "T")
        if bad or len(text) < 2:
            continue
        found.setdefault(sid, []).append((ps.en_score(text), items))
    return {k: max(v, key=lambda c: c[0])[1] for k, v in found.items()}


def lines_of(items):
    out, cur = [], ""
    for it in items:
        if it[0] == "T":
            cur += it[1]
        elif it[0] == "BR":
            out.append(cur)
            cur = ""
    out.append(cur)
    return out


def px(text):
    w = text_rt.rt_width(text_rt.to_bios(text))
    return -1 if w is None else w


def main():
    os.makedirs(WORK, exist_ok=True)
    jp = text_rt.Jp(open(text_rt.JP_DRA, "rb").read())
    rep, missing, widest, total = [], [], 0, 0
    for ovl, (retail_rel, _, scripts) in ps.OVERLAYS.items():
        b = jp_overlay(retail_rel)
        if b is None:
            rep.append("%s: no %s in disks/jpre" % (ovl, retail_rel))
            continue
        rt = rt_segments(b, jp)
        retail = open(os.path.join(ROOT, "disks/us", retail_rel), "rb").read()
        for sc in scripts:
            if "c" in sc:
                continue  # (CEN's Saturn fight copies: C arrays, later)
            toks, off = ps.retail_script(retail, sc, ovl)
            ids = [t[1] for t in toks if t[0] == "PLAY_SOUND" and ps.VOICE_LO <= t[1] <= ps.VOICE_HI]
            rep.append("%s @0x%X voices %s" % (ovl, off, " ".join("%X" % i for i in ids)))
            for sid in ids:
                total += 1
                jid = RT_ID.get(sid, sid - 2)
                if jid not in rt:
                    missing.append("%s %X" % (ovl, sid))
                    rep.append("  %X  (no retranslated line)" % sid)
                    continue
                ls = lines_of(rt[jid])
                ws = [px(l) for l in ls]
                widest = max(widest, max(ws))
                rep.append("  %X  %d lines, widest %d px%s" % (
                    sid, len(ls), max(ws), "  OVER" if max(ws) > LINE_PX else ""))
                for l, w in zip(ls, ws):
                    rep.append("      %3d | %s" % (w, l))
    head = ["voiced lines: %d, without a retranslated line: %d, widest line %d px (strip %d)" % (
        total, len(missing), widest, LINE_PX)]
    if missing:
        head.append("missing: " + ", ".join(missing))
    open(REPORT, "w").write("\n".join(head + [""] + rep) + "\n")
    print("\n".join(head))


if __name__ == "__main__":
    main()
