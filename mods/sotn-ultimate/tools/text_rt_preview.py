#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Preview of Script = Retrans's 12 px font where DRA draws with the BIOS font
(func_800F99B8 -> mods/sotn-ultimate/src/menu/rt_font.c), before an emulator
test: sample strings of this build's RT pack drawn with text_rt.py rt_draw,
the pixel model of ModRtText (the glyphs and widths from the builder's
disks/jpre/DRA.BIN, the colours from CLUT 0x1A1 of the US F_GAME.BIN, as the
game shows them; a second copy with the patch's own CLUT for comparison).

It renders the retranslation's text, so it writes OUTSIDE the repository:
  text_rt_preview.py OUT_DIR
Needs the built DRA (build/us) and disks/jpre. Each line is the whole
texture line the renderer fills (288 px, the relic list's 120 px), 3x,
on an approximate menu-window blue; a red mark is the line's end."""
import os
import struct
import sys

from PIL import Image, ImageDraw

import text_packs as tp
import text_rt as rt

SCALE = 3
BG = (16, 16, 72)  # (approximate: the menu windows are a blue gradient)


def clut(path, pal=0xA1):
    d = open(path, "rb").read()
    out = []
    for v in struct.unpack_from("<16H", d, 0x40000 + pal * 32):
        out.append(((v & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v >> 10 & 31) * 255 // 31))
    return out


def line_image(px, colours):
    h, w = len(px), len(px[0])
    im = Image.new("RGB", (w, h), BG)
    for y in range(h):
        for x in range(w):
            if px[y][x]:
                im.putpixel((x, y), colours[px[y][x]])
    return im.resize((w * SCALE, h * SCALE), Image.NEAREST)


def samples(ents, saves):
    by = {(e.table, e.idx, e.field): e for e in ents}
    picks = [
        ("Description (equip 9)", ("equip", 9, "desc")),
        ("Description (acc 13)", ("acc", 13, "desc")),
        ("Description, fits exactly 288/288 (equip 37)", ("equip", 37, "desc")),
        ("Description, 286/288 (equip 76)", ("equip", 76, "desc")),
        ("Relic description with arrows, 286/288 (relic 6)", ("relic", 6, "desc")),
        ("Description, 285/288 (equip 166)", ("equip", 166, "desc")),
        ("Help line (help 6)", ("help", 6, "str")),
        ("Spell name (spell 0)", ("spell", 0, "name")),
        ("Relic name (relic 2, leading space)", ("relic", 2, "name")),
        ("Relic name (relic 22)", ("relic", 22, "name")),
        ("Relic name (relic 26)", ("relic", 26, "name")),
        ("Still US: does not fit (equip 16, its US text in the RT font)", ("equip", 16, "desc")),
    ]
    out = []
    for label, k in picks:
        e = by[k]
        w = 0x3C if e.context == "relic_name" else 0x90
        out.append((label, e.new, w, e.limit))
    # the longest relic and spell names drawn
    for ctx, w in (("relic_name", 0x3C), ("spell_name", 0x90)):
        L = [e for e in ents if e.context == ctx and e.new]
        e = max(L, key=lambda e: rt.rt_width(e.new) or 0)
        out.append(("Longest %s (%s %d): %d px of %d" % (ctx.replace("_", " "), e.table, e.idx,
                                                        rt.rt_width(e.new), e.limit),
                    e.new, w, e.limit))
    # what the cut looks like: an RT description that does not fit
    e = by[("equip", 16, "desc")]
    out.append(("(not used) the RT text of equip 16 drawn anyway: %d px, cut at 288" % e.measure,
                rt.encode(e, e.rt), 0x90, 288))
    for addr, room, us, new, text, wd, box, why, grp in saves:
        if new is not None and grp in ("saved", "select", "save"):
            out.append(("Save message (%s), box %s px" % (grp, box), new.rstrip(b"\0"), 0x90, box))
    return out


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    syms = tp.dra_symbols()
    dra = tp.dra_image(os.path.join(tp.BUILD, "DRA.BIN"), syms)
    res = rt.build(tp.Ram(dra, syms["g_ModDub"]), syms)
    if res is None:
        sys.exit("text_rt_preview: " + rt.inputs_state()[1])
    ents, saves, _ = res
    font = rt.rt_font()
    us_clut = clut(os.path.join(rt.ROOT, "disks/us/BIN/F_GAME.BIN"))
    jp_path = os.path.join(rt.INPUT_DIR, "BIN/F_GAME.BIN")
    jp_clut = clut(jp_path) if os.path.exists(jp_path) else None
    rows = []
    for n, (label, data, w, limit) in enumerate(samples(ents, saves)):
        px, extent = rt.rt_draw(data, w, font)
        ims = [line_image(px, us_clut)]
        if jp_clut:
            ims.append(line_image(px, jp_clut))
        for k, im in enumerate(ims):
            d = ImageDraw.Draw(im)
            if limit and limit < 2 * w:
                d.line([(limit * SCALE, 0), (limit * SCALE, im.height)], fill=(200, 40, 40))
            d.line([(2 * w * SCALE - 1, 0), (2 * w * SCALE - 1, im.height)], fill=(200, 40, 40))
        ims[0].save(os.path.join(out_dir, "%02d.png" % n))
        rows.append(("%s  [%d px]" % (label, extent), ims))
    lab = 14
    width = max(sum(i.width for i in ims) + 8 * (len(ims) - 1) for _, ims in rows) + 16
    height = sum(lab + ims[0].height + 10 for _, ims in rows) + 30
    sheet = Image.new("RGB", (width, height), (0, 0, 0))
    d = ImageDraw.Draw(sheet)
    d.text((8, 6), "Script = Retrans, func_800F99B8 lines (3x). Left: US CLUT 0x1A1 (as the game "
           "shows it); right: the patch's CLUT 0x1A1", fill=(255, 255, 255))
    y = 26
    for label, ims in rows:
        d.text((8, y), label, fill=(220, 220, 220))
        y += lab
        x = 8
        for im in ims:
            sheet.paste(im, (x, y))
            x += im.width + 8
        y += ims[0].height + 10
    sheet.save(os.path.join(out_dir, "sheet.png"))
    print("text_rt_preview: %d lines in %s (sheet.png)" % (len(rows), out_dir))


if __name__ == "__main__":
    main()
