#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Checks the text packs (mods/sotn-ultimate/tools/text_packs.py, applier
mods/sotn-ultimate/src/menu/text_pack.h) on the built files:

1. build/us/SEL.BIN (and SELRIC2.BIN) hold exactly the chunks text_packs.py
   makes from this build's DRA, where SEL's code reads them
   (g_ModTextSelChunk) and inside its dead config copy.
2. The disc image holds them where the System popup reads them: DRA's
   CdFile_DemoKey entry (g_LbaBinDemokey: sector 0x7415, 0x2000 bytes)
   plus 4 * the g_LoadOvlIdx sysopt uses (g_ModTextCdIdx in ARC_F2.BIN).
3. The proof: for each dub, the RAM after applying the pack (the
   applier's C, mirrored by text_packs.apply_chunk) is byte for byte the RAM
   the retired step 3 mechanism made (SEL's ModDubTextCopy, then DRA's
   per-frame ModApplyDubText, emulated from step 3's compiled tables in
   text_packs_legacy.json): all of DRA's image, and the strings in g_ModDub.
4. A synthetic pack of the retranslation's size (every name and
   description string rewritten and repointed) round-trips through the
   chunk encoder and the applier.

--ref DIR (not run by the build; step 3's DRA.BIN, dra.elf and SEL.BIN in
DIR): (3) against step 3's own DRA image, with its rodata moved by the pad
change, and the legacy tables found in its SEL.BIN.

Prints OK / FAIL lines; exits 1 on a failure."""
import json
import os
import random
import re
import struct
import sys

import text_packs as tp

ROOT = tp.ROOT
BUILD = tp.BUILD
LEGACY = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "text_packs_legacy.json")))
bad = []


def fail(msg):
    bad.append(msg)
    print("FAIL text packs: " + msg)


def nm(path):
    return tp.dra_symbols(path)


# --- the retired mechanism (step 3), emulated --------------------------------
def legacy_apply(ram, syms, dub, psp):
    """SEL's ModDubTextCopy (2C048_mod_player_select.h, step 3) then DRA's
    ModApplyDubText (game_handlers_mod_balance.h, step 3) with
    MOD_PSP_DUB_ON() = psp"""
    tables = [syms["g_EquipDefs"], syms["g_AccessoryDefs"], syms["g_EnemyDefs"],
              syms["g_RelicDefs"], LEGACY["menu_str"]]
    fixed = dub + LEGACY["fixed_text_off"]
    ins = bytes.fromhex(LEGACY["fixed_bytes"])
    pos = ip = 0
    for table, fpos, off, dele, nins, room in LEGACY["fixed"]:
        slot = tables[table] + off
        d = fixed + pos
        if ram.u32(slot) != d:
            s = ram.u32(slot)
            out = b""
            if dele != 0xFF:
                out += ram.read(s, fpos)
                s += fpos + dele
            out += ins[ip:ip + nins]
            if dele != 0xFF:
                while True:
                    c = ram.read(s, 1)
                    out += c
                    s += 1
                    if c == b"\0":
                        break
            ram.write(d, out)
            ram.w32(slot, d)
        ip += nins
        pos += room
    src = bytes.fromhex(LEGACY["dub_bytes"])
    pos = 0
    for table, off, n in LEGACY["dub"]:
        dst = ram.u32(tables[table & 7] + off) + (table >> 3)
        ram.write(dst, src[pos + n * psp:pos + n * psp + n])
        pos += 2 * n


def sector_data(img, lba, n):
    """n Form 1 sectors' user data from a raw 2352-byte image"""
    return b"".join(img[(lba + k) * 2352 + 24:(lba + k) * 2352 + 24 + 2048] for k in range(n))


def word_at(path_bin, base, addr):
    b = open(path_bin, "rb").read()
    return struct.unpack_from("<I", b, addr - base)[0]


def main():
    ref = None
    if "--ref" in sys.argv:
        ref = sys.argv[sys.argv.index("--ref") + 1]
    d = tp.c_defines()
    syms = nm(os.path.join(BUILD, "dra.elf"))
    dra = tp.dra_image(os.path.join(BUILD, "DRA.BIN"), syms)
    dub = syms["g_ModDub"]
    sel_packs, rt_packs, rt_info = tp.all_packs(tp.Ram(dra, dub), syms, d)
    packs = {p: sel_packs[p] for p in (0, 1)}
    chunks = tp.encode_chunks(sel_packs, d)
    rt_chunks = tp.encode_chunks(rt_packs, d, lambda c: d["MOD_TEXT_CHUNK_LEN"], "8 chunks") if rt_packs else []

    # 1. SEL's copy, where its code reads it
    sel_syms = nm(os.path.join(BUILD, "stsel.elf"))
    if "g_ModTextSelChunk" not in sel_syms:
        fail("SEL has no g_ModTextSelChunk (2C048_mod_player_select.h)")
    else:
        at = word_at(os.path.join(BUILD, "SEL.BIN"), tp.SEL_BASE, sel_syms["g_ModTextSelChunk"])
        if at != tp.SEL_BASE + d["SECTOR"] * 0x800:
            fail("SEL reads its chunks at 0x%X, they are at 0x%X" % (at, tp.SEL_BASE + d["SECTOR"] * 0x800))
    for name in ("SEL.BIN", "SELRIC2.BIN"):
        f = open(os.path.join(BUILD, name), "rb").read()
        for c, blob in enumerate(chunks):
            off = (d["SECTOR"] + 4 * c) * 0x800
            if not (tp.DEAD_START <= off and off + len(blob) <= tp.DEAD_END):
                fail("chunk %d outside SEL's dead copy" % c)
            if f[off:off + len(blob)] != blob:
                fail("%s chunk %d at 0x%X is not this build's (run text_packs.py --apply)" % (name, c, off))
    # nothing in SEL may point into its dead copy (it is free only while
    # nothing reads it); g_ModTextSelChunk is the one reference allowed
    sel = open(os.path.join(BUILD, "SEL.BIN"), "rb").read()
    lo, hi = tp.SEL_BASE + tp.DEAD_START, tp.SEL_BASE + tp.DEAD_END
    # (word-aligned values: the save icons' palettes hold two odd ones)
    words = struct.unpack("<%dI" % (len(sel) // 4), sel[:len(sel) // 4 * 4])
    refs = [4 * i for i, v in enumerate(words)
            if not (tp.DEAD_START <= 4 * i < tp.DEAD_END) and lo <= v < hi and not v & 3]
    # lui + addiu / load / store pairs in the code that resolve into it
    for i, v in enumerate(words):
        if 4 * i >= tp.DEAD_START and 4 * i < tp.DEAD_END or v >> 26 != 0xF:
            continue
        rt, top = (v >> 16) & 31, (v & 0xFFFF) << 16
        for k in range(i + 1, min(i + 9, len(words))):
            w = words[k]
            op, rs = w >> 26, (w >> 21) & 31
            if rs == rt and op in (0x09, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B):
                a = (top + (w & 0xFFFF) - ((w & 0x8000) << 1)) & 0xFFFFFFFF
                if lo <= a < hi:
                    refs.append(4 * k)
            # rt written again: the pair ends
            dst = (w >> 11) & 31 if op == 0 else (w >> 16) & 31 if 0x08 <= op <= 0x26 else -1
            if dst == rt:
                break
    allowed = {sel_syms.get("g_ModTextSelChunk", -1) - tp.SEL_BASE}
    if set(refs) - allowed:
        fail("SEL words point into the dead copy at %s" % ", ".join(hex(tp.SEL_BASE + i) for i in sorted(set(refs) - allowed)[:8]))

    # 2. the disc, where sysopt reads it
    demokey = syms["g_LbaBinDemokey"]
    loc, cb, size = struct.unpack_from("<iii", dra, demokey - tp.DRA_BASE)
    if (loc, cb, size) != (d["MOD_TEXT_DEMOKEY_LBA"], 4, d["MOD_TEXT_CHUNK_LEN"]):
        fail("DRA's g_LbaBinDemokey is {0x%X, %d, 0x%X}" % (loc, cb, size))
    sys_syms = nm(os.path.join(BUILD, "mod/sysopt/sysopt.elf"))
    if "g_ModTextCdIdx" not in sys_syms:
        fail("sysopt has no g_ModTextCdIdx")
        idx = None
    else:
        a = sys_syms["g_ModTextCdIdx"]
        arc = open(os.path.join(BUILD, "ARC_F2.BIN"), "rb").read()
        idx = struct.unpack_from("<i", arc, a - 0x8013C000)[0]
        if idx != d["CD_IDX"]:
            fail("sysopt loads with g_LoadOvlIdx %d, the chunks need %d" % (idx, d["CD_IDX"]))
    img_path = os.path.join(ROOT, "build/sotn.us.bin")
    if idx is not None and os.path.exists(img_path):
        img = open(img_path, "rb")
        for c, blob in enumerate(chunks):
            lba = loc + 4 * (idx + c)
            img.seek(lba * 2352)
            raw = img.read(4 * 2352)
            got = sector_data(raw, 0, 4)
            if got[:len(blob)] != blob:
                fail("the disc's sector 0x%X (CdFile_DemoKey, g_LoadOvlIdx %d) is not chunk %d" % (lba, idx + c, c))
            elif not tp.chunk_ok(got, d) or got[8] != c:
                fail("chunk %d on the disc fails the applier's own check" % c)

    rt_disc_check(d, syms, dra, sel_syms, rt_chunks, img_path)

    # 3. the proof, on this build's DRA
    n_bytes = n_ptrs = 0
    for psp in (0, 1):
        old = tp.Ram(dra, dub)
        legacy_apply(old, syms, dub, psp)
        new = tp.Ram(dra, dub)
        tag = tp.apply_pack(new, chunks, psp, d)
        if tag != 0x54585400 | psp:
            fail("pack %d not applied" % psp)
        if old.regions[0][1] != new.regions[0][1]:
            diff = [i for i in range(len(dra)) if old.regions[0][1][i] != new.regions[0][1][i]]
            fail("dub %s: DRA RAM differs at %s" % (tp.PACK_NAMES[psp], ", ".join(hex(tp.DRA_BASE + i) for i in diff[:8])))
        a = d["MOD_TEXT_OVF_A_OFF"]
        if old.regions[1][1][a:a + d["MOD_TEXT_OVF_A_LEN"]] != new.regions[1][1][a:a + d["MOD_TEXT_OVF_A_LEN"]]:
            fail("dub %s: the fixed strings in g_ModDub differ" % tp.PACK_NAMES[psp])
    # the step 3 struct (ModDubText) lived where the new rooms B / tag are:
    # only the tag differs from zero now
    fp = tp.footprint(packs[0])
    n_ptrs = len(fp[1])

    # 3b. against step 3's own files
    if ref:
        ref_proof(ref, d, syms, dra, dub, chunks)

    # 4. a retranslation-sized synthetic pack
    synth_test(d, syms, dra, dub)

    # 5. the retranslation: round trips, pointers, write bounds
    rt_hook_check(d, syms, dra)
    if rt_packs:
        rt_proof(d, syms, dra, dub, chunks, rt_chunks, sel_packs, rt_packs, rt_info)

    if bad:
        sys.exit(1)
    print("OK   text packs: SEL dead copy %d of %d B used; %s" % (
        sum(map(len, chunks)), sum(tp.chunk_room(d, c) for c in range(8)),
        "retranslation pack %d chunk(s) (%s B) in SD/TXT_RT.BIN" % (len(rt_chunks), "+".join(str(len(c)) for c in rt_chunks))
        if rt_chunks else "no retranslation pack (no disks/jpre): Script = Retrans shows the dub's text"))
    print("OK   text packs: %d chunk(s) (%s B) in SEL sector %d and on the disc (g_LoadOvlIdx %d); "
          "PS1 / PSP packs = step 3's mechanism byte for byte (footprint %d bytes, %d pointers)"
          % (len(chunks), "+".join(str(len(c)) for c in chunks), d["SECTOR"], d["CD_IDX"],
             len(fp[0]), n_ptrs))


def rt_disc_check(d, syms, dra, sel_syms, rt_chunks, img_path):
    """the switch, the words SEL / sysopt load with and SD/TXT_RT.BIN on
    the disc"""
    hdr = open(tp.RT_HEADER).read()
    on = int(re.search(r"#define MOD_TEXT_RT_ON (\d)", hdr)[1])
    if on != (1 if rt_chunks else 0):
        fail("mod_text_rt.h says MOD_TEXT_RT_ON %d, the build made %d RT chunk(s)" % (on, len(rt_chunks)))
    lba = tp.rt_lba()
    if lba is None:
        fail("include/lba_us.h has no OFF_SD_TXT_RT")
        return
    first, idx = tp.rt_layout(d, lba)
    want = tp.rt_file(rt_chunks, first) if rt_chunks else bytes(0x800)
    if open(tp.RT_FILE, "rb").read() != want:
        fail("build/us/TXT_RT.BIN is not this build's (run text_packs.py --apply)")
    if not rt_chunks:
        return
    sys_syms = nm(os.path.join(BUILD, "mod/sysopt/sysopt.elf"))
    arc = open(os.path.join(BUILD, "ARC_F2.BIN"), "rb").read()
    for who, syms_, data, base in (("sysopt", sys_syms, arc, 0x8013C000),
                                   ("SEL", sel_syms, open(os.path.join(BUILD, "SEL.BIN"), "rb").read(), tp.SEL_BASE)):
        if "g_ModTextRtCdIdx" not in syms_:
            fail("%s has no g_ModTextRtCdIdx" % who)
            continue
        got = struct.unpack_from("<i", data, syms_["g_ModTextRtCdIdx"] - base)[0]
        if got != idx:
            fail("%s loads the RT chunks with g_LoadOvlIdx %d, they need %d" % (who, got, idx))
    if not os.path.exists(img_path):
        return
    img = open(img_path, "rb")
    for c, blob in enumerate(rt_chunks):
        sec = d["MOD_TEXT_DEMOKEY_LBA"] + 4 * (idx + c)
        img.seek(sec * 2352)
        raw = img.read(4 * 2352)
        if len(raw) < 4 * 2352:
            fail("RT chunk %d: the disc ends inside its 4-sector read" % c)
            continue
        got = sector_data(raw, 0, 4)
        if got[:len(blob)] != blob:
            fail("the disc's sector 0x%X (g_LoadOvlIdx %d) is not RT chunk %d" % (sec, idx + c, c))
        elif not tp.chunk_ok(got, d) or got[8] != c:
            fail("RT chunk %d on the disc fails the applier's own check" % c)
    print("OK   text packs: RT chunks at SD/TXT_RT.BIN sector %d + %d = DEMOKEY + 4 * %d, read by SEL "
          "and sysopt with that g_LoadOvlIdx" % (lba, first, idx))


# --- the drivers, as the C runs them (text_pack.h, SEL, sysopt) ----------
def rt_hook_check(d, syms, dra):
    """DRA's func_800F99B8 calls the RT font's code (jal MOD_RT_FONT_ADDR)
    only after reading the low byte of g_ModDub.textPack (lui + lbu); the
    font's code was linked against this DRA's line pointer"""
    f = syms["func_800F99B8"] - tp.DRA_BASE
    words = struct.unpack_from("<%dI" % 0x100, dra, f)
    a = d["MOD_RT_FONT_ADDR"]
    jal = 0x0C000000 | ((a >> 2) & 0x3FFFFFF)
    tag = syms["g_ModDub"] + 1224  # OFF(ModDubState, textPack), text_pack.h
    lo = tag & 0xFFFF
    hi = (tag + 0x8000) >> 16
    k = [i for i, w in enumerate(words) if w == jal]
    ok = len(k) == 1 and any(
        words[i] >> 26 == 0xF and words[i] & 0xFFFF == hi and words[i + 1] >> 26 == 0x24 and
        words[i + 1] & 0xFFFF == lo for i in range(max(0, k[0] - 6), k[0]))
    if not ok:
        fail("DRA's func_800F99B8 does not call the RT font (jal 0x%X after lbu textPack)" % a)
    rs = nm(os.path.join(tp.RTFONT, "rtfont.elf"))
    if rs.get("ModRtText") != a or rs.get("D_8013794C") != syms["D_8013794C"]:
        fail("rtfont.elf is not linked at 0x%X against this DRA (build_rtfont.sh)" % a)
    else:
        print("OK   text packs: DRA calls the RT font at 0x%X when the RT pack's tag is set; "
              "its code is linked against this DRA" % a)


def run_pack(ram, chunks, pack, d, upto=None):
    """every chunk of the stream, pack's records (upto: stop after that many
    chunks, a half-applied pack); 1 when all applied"""
    for i, c in enumerate(chunks):
        if upto is not None and i >= upto:
            return 0
        if not tp.chunk_ok(c, d) or c[8] != i:
            return 0
        tp.apply_chunk(ram, c, pack)
        if i + 1 >= c[9]:
            return 1
    return 0


class Game:
    """DRA's RAM + g_ModDub.textPack, driven like SEL / the System popup"""

    def __init__(self, dra, dub, sel, rt, d):
        self.ram, self.tag, self.sel, self.rt, self.d = tp.Ram(dra, dub), 0, sel, rt, d

    def default(self, pack):
        """ModTextSelDub / SysOptText to a dub's pack"""
        if self.tag != 0x54585400 | pack:
            if self.tag not in (0x54585400, 0x54585401):
                run_pack(self.ram, self.sel, tp.PACK_RESTORE, self.d)
            run_pack(self.ram, self.sel, pack, self.d)
            self.tag = 0x54585400 | pack

    def retrans(self, upto=None):
        if self.tag != 0x54585402:
            self.tag = 0
            if run_pack(self.ram, self.rt, tp.PACK_RT, self.d, upto):
                self.tag = 0x54585402

    def half_default(self, pack, upto):
        """a restore pass cut after upto chunks (the menu left mid-load)"""
        self.tag = 0
        run_pack(self.ram, self.sel, tp.PACK_RESTORE, self.d, upto)

    def state(self):
        return bytes(self.ram.regions[0][1]) + bytes(self.ram.regions[1][1])


def rt_proof(d, syms, dra, dub, chunks, rt_chunks, sel_packs, rt_packs, info, quiet=False):
    """(b) round trips restore RAM exactly, (c) RT pointers land in strings
    RT writes, (d) no write outside DRA's rewritten strings, the overflow
    rooms and the save message literals, no pointer outside the slots"""
    errs = []
    dubs = [("PS1", 0), ("PSP", 1), ("JP", 1)]
    ref = {}
    for name, pk in dubs:
        g = Game(dra, dub, chunks, rt_chunks, d)
        legacy_apply(g.ram, syms, dub, pk)
        ref[pk] = g.state()
    g = Game(dra, dub, chunks, rt_chunks, d)
    g.default(0)
    if g.state() != ref[0]:
        errs.append("restore + PS1 from boot differs from step 3's PS1")
    g.retrans()
    rt_state = g.state()
    steps = 0
    for name, pk in dubs:
        for other, pk2 in dubs:
            g = Game(dra, dub, chunks, rt_chunks, d)
            g.default(pk)
            g.retrans()
            steps += 1
            if g.state() != rt_state:
                errs.append("RT after %s differs from RT after PS1" % name)
            g.default(pk2)
            if g.state() != ref[pk2]:
                errs.append("%s -> Retrans -> Default (%s) does not restore RAM" % (name, other))
            g.retrans()
            g.default(pk)
            if g.state() != ref[pk]:
                errs.append("%s -> RT -> %s -> RT -> %s does not restore RAM" % (name, other, name))
            # cut loads: RT half applied, then Default; a cut restore, then RT / Default
            for k in range(1, len(rt_chunks)):
                h = Game(dra, dub, chunks, rt_chunks, d)
                h.default(pk)
                h.retrans(upto=k)
                h.default(pk2)
                if h.state() != ref[pk2]:
                    errs.append("%s -> RT cut after %d chunk(s) -> %s does not restore RAM" % (name, k, other))
            for k in range(1, len(chunks)):
                h = Game(dra, dub, chunks, rt_chunks, d)
                h.retrans()
                h.half_default(pk2, k)
                h.retrans()
                if h.state() != rt_state:
                    errs.append("RT -> restore cut after %d chunk(s) -> RT differs" % k)
                h.half_default(pk2, k)
                h.default(pk2)
                if h.state() != ref[pk2]:
                    errs.append("RT -> restore cut after %d -> %s does not restore RAM" % (k, other))
    # (c) every pointer RT writes: the whole string it points to is RT's
    kinds = {e.slot: e.kind for e in info["ents"]}
    g = Game(dra, dub, chunks, rt_chunks, d)
    g.retrans()
    rt_bytes, rt_ptrs = tp.footprint(rt_packs[tp.PACK_RT])
    nptr = 0
    for slot in sorted(rt_ptrs):
        t = g.ram.u32(slot)
        s_ = g.ram.cstr(t, kinds[slot])
        nptr += 1
        if not set(range(t, t + len(s_))) <= rt_bytes:
            errs.append("RT pointer at 0x%X -> 0x%X: its string is not all RT's" % (slot, t))
    # (d) the bounds
    rooms = set()
    for a, b in info["rooms"]:
        rooms |= set(range(a, b))
    for addr, room, *_ in info["saves"]:
        rooms |= set(range(addr, addr + room))
    slots = set(kinds)
    # the font's room: the RT pack only, and the whole blob lands there
    fa, fb = info["font"]
    font = set(range(fa, fa + len(fb)))
    if not (tp.RT_FONT_ADDR <= fa and fa + len(fb) <= tp.RT_FONT_END):
        errs.append("the RT font blob 0x%X+%d is outside its room" % (fa, len(fb)))
    if g.ram.read(fa, len(fb)) != fb:
        errs.append("the RT pack does not leave the font's code and glyphs in their room")
    for p, recs in list(sel_packs.items()) + list(rt_packs.items()):
        b_, p_ = tp.footprint(recs)
        if p == tp.PACK_RT:
            b_ = b_ - font
        elif b_ & font:
            errs.append("pack %s writes the RT font's room" % tp.PACK_NAMES[p])
        if not b_ <= rooms:
            x = sorted(b_ - rooms)
            errs.append("pack %s writes outside the strings / rooms at 0x%X (+%d)" % (tp.PACK_NAMES[p], x[0], len(x)))
        if not p_ <= slots:
            errs.append("pack %s writes pointers outside the string slots: %s" % (tp.PACK_NAMES[p], [hex(x) for x in sorted(p_ - slots)[:4]]))
    # the strings rewritten: nothing else in DRA refers into them
    bad_refs = tp.foreign_refs(tp.Ram(dra, dub), syms, info["ents"], info["segs"], len(dra))
    if bad_refs:
        errs.append("DRA words point into the rewritten strings at %s" % [hex(a) for a in bad_refs[:4]])
    if quiet:
        return errs
    for e in errs:
        fail(e)
    if not errs:
        print("OK   text packs: retranslation round trips: %d dub pairs x (Default -> RT -> Default, "
              "RT -> Default -> RT, loads cut after each chunk) restore DRA + g_ModDub byte for byte; "
              "RT the same from every dub; %d RT pointers land in RT's own strings; every write in "
              "DRA's rewritten strings (%d B), the overflow rooms or %d save message literals, every "
              "pointer in the %d string slots; the RT font (%d B) whole in its room, written by the "
              "RT pack only" % (steps, nptr, sum(b - a for a, b in info["segs"]),
                                len(info["saves"]), len(slots), len(info["font"][1])))
        # the check catches a restore pack missing one pointer (one the
        # dub packs do not write)
        rest = list(sel_packs[tp.PACK_RESTORE])
        dubp = tp.footprint(sel_packs[0])[1]
        k = next(i for i, r in enumerate(rest) if r[0] == "ptr" and r[1] + 4 * r[3][0][0] not in dubp)
        rest[k] = ("ptr", rest[k][1], rest[k][2], rest[k][3][1:])
        mut = dict(sel_packs)
        mut[tp.PACK_RESTORE] = rest
        if not rt_proof(d, syms, dra, dub, tp.encode_chunks(mut, d), rt_chunks, mut, rt_packs, info, quiet=True):
            fail("the round-trip proof does not catch a restore pack missing one pointer")
        else:
            print("OK   text packs: mutation (a restore pack missing one pointer) is caught")


def string_slots(syms, ram):
    """every name / description pointer slot: (slot, kind)"""
    out = []
    eq, acc, en, rel, menu = (syms[t] for t in tp.TABLES)
    for i in range(217):
        out += [(eq + i * 0x34, "s"), (eq + i * 0x34 + 4, "c")]
    for i in range(90):
        out += [(acc + i * 0x20, "s"), (acc + i * 0x20 + 4, "c")]
    i = 0
    while en + i * 0x28 < acc + 0x10000 and ram.u32(en + i * 0x28) >= tp.DRA_BASE and i < 420:
        out.append((en + i * 0x28, "s"))
        i += 1
    for i in range(30):
        out += [(rel + i * 0x10, "c"), (rel + i * 0x10 + 4, "c")]
    for i in range(110):
        if ram.u32(menu + 4 * i) >= tp.DRA_BASE:
            out.append((menu + 4 * i, "s"))
    return out


def ref_proof(ref, d, syms, dra, dub, chunks):
    rsyms = nm(os.path.join(ref, "dra.elf"))
    rdra = tp.dra_image(os.path.join(ref, "DRA.BIN"), rsyms)
    rsel = open(os.path.join(ref, "SEL.BIN"), "rb").read()
    # the frozen tables are step 3's compiled ones
    fx = b"".join(struct.pack("<BBHBBBx", *r) for r in LEGACY["fixed"])
    dx = b"".join(struct.pack("<BxHBx", *r) for r in LEGACY["dub"])
    for what, b in (("fixed rows", fx), ("fixed bytes", bytes.fromhex(LEGACY["fixed_bytes"])),
                    ("dub rows", dx), ("dub bytes", bytes.fromhex(LEGACY["dub_bytes"]))):
        if rsel.count(b) != 1:
            fail("--ref: the legacy %s are not in step 3's SEL.BIN once" % what)
    if rsyms["g_ModDub"] != dub or rsyms["g_MenuStr"] != LEGACY["menu_str"]:
        fail("--ref: g_ModDub / g_MenuStr moved")
    delta = syms["g_RelicDefs"] - rsyms["g_RelicDefs"]
    if syms["g_SpellDefs"] - rsyms["g_SpellDefs"] != delta:
        fail("--ref: rodata did not move as one block")
    data_end = 0x800DB3B4
    total = {}
    for psp in (0, 1):
        old = tp.Ram(rdra, dub)
        legacy_apply(old, rsyms, dub, psp)
        new = tp.Ram(dra, dub)
        tp.apply_pack(new, chunks, psp, d)
        ob, nb = old.regions[0][1], new.regions[0][1]
        # DRA data: every word equal, or a pointer into the moved rodata
        bad_words, other = [], []
        for i in range(0, data_end - tp.DRA_BASE, 4):
            o, n = struct.unpack_from("<I", ob, i)[0], struct.unpack_from("<I", nb, i)[0]
            if o != n and not (rsyms["g_ModDraPad"] <= o < 0x80140000 and n == o + delta):
                # a word the two builds differ in that neither mechanism
                # writes (e.g. ST_SEL_BIN_LEN: SEL's length)
                if rdra[i:i + 4] == ob[i:i + 4] and dra[i:i + 4] == nb[i:i + 4]:
                    other.append(tp.DRA_BASE + i)
                else:
                    bad_words.append(tp.DRA_BASE + i)
        total["other"] = other
        if bad_words:
            fail("--ref dub %s: DRA data differs at %s" % (tp.PACK_NAMES[psp], ", ".join(map(hex, bad_words[:8]))))
        # every string slot: same bytes, same place (moved with rodata or the
        # same g_ModDub address)
        lo_s, hi_s, n_slots, n_dub = 1 << 32, 0, 0, 0
        for slot, kind in string_slots(rsyms, old):
            op = old.u32(slot)
            np_ = new.u32(slot + (syms["g_RelicDefs"] - rsyms["g_RelicDefs"] if slot >= rsyms["g_ModDraPad"] else 0))
            if op < tp.DRA_BASE:
                continue
            os_, ns = old.cstr(op, kind), new.cstr(np_, kind)
            if os_ != ns:
                fail("--ref dub %s: slot 0x%X string %r vs %r" % (tp.PACK_NAMES[psp], slot, os_, ns))
            if dub <= op < dub + 4096:
                n_dub += 1
                if np_ != op:
                    fail("--ref dub %s: slot 0x%X -> 0x%X vs 0x%X" % (tp.PACK_NAMES[psp], slot, op, np_))
            else:
                if np_ != op + delta:
                    fail("--ref dub %s: slot 0x%X -> 0x%X vs 0x%X (+%d)" % (tp.PACK_NAMES[psp], slot, op, np_, delta))
                lo_s, hi_s = min(lo_s, op), max(hi_s, op + len(os_))
            n_slots += 1
        # the whole string pool, byte for byte (moved)
        pool_o = ob[lo_s - tp.DRA_BASE:hi_s - tp.DRA_BASE]
        pool_n = nb[lo_s + delta - tp.DRA_BASE:hi_s + delta - tp.DRA_BASE]
        diff = [i for i in range(len(pool_o)) if pool_o[i] != pool_n[i]]
        # (the relic / spell tables sit inside the pool: their string
        # pointers moved too)
        realdiff = []
        for i in diff:
            w = (i // 4) * 4
            if w + 4 <= len(pool_o):
                o = struct.unpack_from("<I", pool_o, w)[0]
                n = struct.unpack_from("<I", pool_n, w)[0]
                if n == o + delta and rsyms["g_ModDraPad"] <= o < 0x80140000:
                    continue
            realdiff.append(lo_s + i)
        if realdiff:
            fail("--ref dub %s: string pool differs at %s" % (tp.PACK_NAMES[psp], ", ".join(map(hex, realdiff[:8]))))
        a = d["MOD_TEXT_OVF_A_OFF"]
        if old.regions[1][1][a:a + d["MOD_TEXT_OVF_A_LEN"]] != new.regions[1][1][a:a + d["MOD_TEXT_OVF_A_LEN"]]:
            fail("--ref dub %s: g_ModDub's fixed strings differ" % tp.PACK_NAMES[psp])
        total = {"other": total.get("other", []), "slots": n_slots, "in g_ModDub": n_dub, "pool": "0x%X-0x%X (%d B)" % (lo_s, hi_s, hi_s - lo_s)}
    if not bad:
        print("OK   text packs --ref %s: both dubs = step 3 (DRA data words, %d string slots (%d into g_ModDub), "
              "pool %s moved by %+d, g_ModDub strings; untouched words that differ between the builds: %s)"
              % (ref, total["slots"], total["in g_ModDub"], total["pool"], delta,
                 ", ".join(map(hex, total["other"])) or "none"))


def synth_test(d, syms, dra, dub):
    """every name / description string rewritten (random lengths, +30%) and
    repointed: in place where it fits the pool, the rest in the overflow
    rooms; encoded, cut into chunks, applied, compared with a direct write"""
    rnd = random.Random(1)
    ram = tp.Ram(dra, dub)
    slots = string_slots(syms, ram)
    pool = sorted({ram.u32(s) for s, _ in slots})
    lo = pool[0]
    hi = max(ram.u32(s) + len(ram.cstr(ram.u32(s), k)) for s, k in slots)
    rooms = [(lo, hi - lo)] + [(dub + d["MOD_TEXT_OVF_%s_OFF" % r], d["MOD_TEXT_OVF_%s_LEN" % r]) for r in "ABC"]
    want = tp.Ram(dra, dub)
    recs, ptrs = [], {}
    ri, used = 0, 0
    texts = {}
    for s, k in slots:
        p = ram.u32(s)
        if p not in texts:
            n = max(2, int(len(ram.cstr(p, k)) * rnd.uniform(0.8, 1.5)))
            texts[p] = bytes(rnd.randrange(1, 0x7F) for _ in range(n - 1)) + b"\0"
    placed = {}
    blobs = {}
    for p, t in texts.items():
        while used + len(t) > rooms[ri][1]:
            ri, used = ri + 1, 0
            if ri == len(rooms):
                raise SystemExit("synthetic text larger than the pool + rooms")
        placed[p] = (ri, used)
        blobs.setdefault(ri, bytearray()).extend(t)
        used += len(t)
    for r, b in blobs.items():
        recs.append(("copy", rooms[r][0], bytes(b)))
        want.write(rooms[r][0], bytes(b))
    by = {}
    for s, _ in slots:
        r, off = placed[ram.u32(s)]
        base = rooms[r][0]
        table = max(syms[t] for t in tp.TABLES if syms[t] <= s)
        by.setdefault((table, base), []).append(((s - table) // 4, off))
        want.w32(s, base + off)
    for (table, base), items in sorted(by.items()):
        recs.append(("ptr", table, base, items))
    chunks = tp.encode_chunks({2: recs}, d)
    got = tp.Ram(dra, dub)
    tag = tp.apply_pack(got, chunks, 2, d)
    total = sum(len(t) for t in texts.values())
    if tag != 0x54585402 or got.regions != want.regions:
        fail("synthetic retranslation-sized pack does not round-trip")
    else:
        print("OK   text packs: synthetic %d-string %d B pack + %d pointers round-trips in %d chunk(s) "
              "(pool 0x%X-0x%X %d B + rooms %d B)" % (len(texts), total, len(slots), len(chunks), lo, hi,
                                                      hi - lo, sum(r[1] for r in rooms[1:])))


if __name__ == "__main__":
    main()
