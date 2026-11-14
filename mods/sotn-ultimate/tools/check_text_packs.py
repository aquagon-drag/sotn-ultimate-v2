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

    # 6. the CD readers (SEL's ModTextReady, sysopt's SysOptText): where
    # SEL's runs, the DRA addresses it reads, and their state machines with
    # reads that end, fail their check or never end (timeouts)
    cd_reader_check(d, syms, sel_syms, chunks, rt_chunks, rt_packs, dra, dub)

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


# --- the CD readers' state machines (sel_text_cd.c, sysopt.c SysOptText) --
def text_pack_h_defines():
    src = open(os.path.join(ROOT, "mods/sotn-ultimate/src/menu/text_pack.h")).read()
    return {k: int(v, 0) for k, v in re.findall(r"#define (MOD_TEXT_CD_\w+) +(\d+)", src)}


class Cd:
    """DRA's loader as the readers see it: a read started (g_CdStep =
    CdStep_LoadInit) ends 3 frames later with the chunk (ok) or a buffer
    that fails the check (bad), or never (stall: CdStep_5 waiting); the
    readers' MOD_TEXT_CD_STOP ends it at once. g_IsUsingCd follows g_CdStep
    one frame late (UpdateCd copies it first)."""

    def __init__(self, outcomes):
        self.outcomes, self.step, self.using, self.left, self.got = list(outcomes), 0, 0, 0, None
        self.reads = 0

    def start(self):
        assert self.step == 0 and not self.using, "a read started while the CD is busy"
        self.reads += 1
        self.got = self.outcomes.pop(0) if self.outcomes else "ok"
        self.step, self.left = 1, 3

    def stop(self):
        self.step = 0

    def frame(self):  # UpdateCd, after the reader
        self.using = self.step
        if self.step and self.got != "stall":
            self.left -= 1
            if not self.left:
                self.step = 0


def sel_reader(n, outcomes, gate_frames, W, T, trace=None):
    """sel_text_cd.c ModTextReady, line by line; returns (result, chunks
    applied, frames, reads)"""
    cd = Cd(outcomes)
    v = dict(cd=0, ovl=0, t0=0, tr=0, nxt=0, gate=0, fail=0)
    tag, applied, now = 0, 0, 1000
    for frame in range(100000):
        now += 1
        snd = frame < gate_frames  # an XA command queued / running
        r = 0
        c = v["cd"] - 1
        if tag == "RT":
            r = 1
        elif cd.step or cd.using:
            if c >= 0 and now - v["t0"] > W:
                cd.stop()
                v["cd"] = 0
                v["tr"] += 1
                if v["tr"] >= T:
                    v["fail"] = 2
        elif v["fail"]:
            tag, r = "dub", 1
        else:
            go = True
            if c >= 0:
                v["cd"] = 0
                if cd.got == "bad":
                    v["fail"] = 1
                    tag, r, go = "dub", 1, False
                else:
                    assert applied == c, "chunk %d applied after %d" % (c, applied)
                    applied += 1
                    c += 1
                    if c >= n:
                        tag, r, go = "RT", 1, False
                    else:
                        v["nxt"], v["tr"] = c, 0
            if go:
                if snd:
                    v["gate"] += 1
                if snd and v["gate"] < W:
                    pass
                else:
                    c = v["nxt"]
                    if not c:
                        tag = 0
                    cd.start()
                    v["cd"], v["t0"] = c + 1, now
        if r:
            return tag, applied, frame, cd.reads
        cd.frame()
    return None, applied, frame, cd.reads


def sysopt_reader(n_rt, n_sel, outcomes, W, from_tag="dub"):
    """sysopt.c SysOptText with Script switched to Retrans (from a dub, or
    from a half-applied state); returns (final tag, passes as
    [(pack, chunks applied)], reads)"""
    cd = Cd(outcomes)
    load = pack = nxt = ovl = fails = t0 = 0
    tag = from_tag
    passes = []
    now = 1000
    for frame in range(100000):
        now += 1
        if load:
            if cd.step or cd.using:
                if now - t0 > W:
                    cd.stop()
                    load = 0
                    fails += 1
                cd.frame()
                continue
            c = load - 1
            load = 0
            if cd.got == "bad":
                fails += 1
                cd.frame()
                continue
            passes[-1][1] += 1
            n = n_rt if pack == "RT" else n_sel
            if c + 1 < n:
                c += 1
            elif nxt:
                pack, nxt, c = nxt, 0, 0
                passes.append([pack, 0])
            else:
                tag = pack
                cd.frame()
                continue
        else:
            want = "RT"
            if fails >= 2:
                want = "dub"
            if tag == want or fails >= 4 or cd.step or cd.using:
                if tag == want or fails >= 4:
                    return tag, passes, cd.reads, fails
                cd.frame()
                continue
            pack, nxt = want, 0
            if want != "RT" and tag != "dub":
                pack, nxt = "restore", "dub"
            tag = 0
            c = 0
            passes.append([pack, 0])
        cd.start()
        load, t0 = c + 1, now
        cd.frame()
    return None, passes, cd.reads, fails


def cd_reader_check(d, syms, sel_syms, chunks, rt_chunks, rt_packs, dra, dub):
    h = text_pack_h_defines()
    W, T = h["MOD_TEXT_CD_WAIT"], h["MOD_TEXT_CD_TRIES"]
    # DRA's CD sound command state, which SEL reads at fixed addresses
    src = open(os.path.join(ROOT, "mods/sotn-ultimate/include/game_mod.h")).read()
    for macro, sym in (("MOD_CD_SND_QUEUE_POS", "g_CdSoundCommandQueuePos"), ("MOD_CD_SND_BUSY", "D_801390A0")):
        a = int(re.search(r"#define %s \(\*\(volatile \w+\*\)(0x[0-9A-Fa-f]+)\)" % macro, src)[1], 16)
        if syms.get(sym) != a:
            fail("game_mod.h %s 0x%X, dra.elf %s 0x%X" % (macro, a, sym, syms.get(sym, 0)))
    # where SEL's reader runs: its area after the staff roll, before the
    # first chunk, and the code SEL calls in it
    area = sel_syms.get("g_ModTextCdArea")
    fn = sel_syms.get("ModTextReady")
    if area is None or fn is None:
        fail("SEL has no g_ModTextCdArea / ModTextReady (src/st/sel/mod_text_cd.inc)")
    else:
        end = area + d["MOD_TEXT_CD_AREA"]
        used = max(v for k, v in sel_syms.items() if area <= v < end) + 4 - area
        if not (fn == area and end <= tp.SEL_BASE + d["SECTOR"] * 0x800):
            fail("SEL's reader at 0x%X-0x%X, the first chunk at 0x%X" % (area, end, tp.SEL_BASE + d["SECTOR"] * 0x800))
        else:
            print("OK   text packs: SEL's reader (ModTextReady + state) at 0x%X, %d of %d B, before the "
                  "first chunk at 0x%X" % (area, used, d["MOD_TEXT_CD_AREA"], tp.SEL_BASE + d["SECTOR"] * 0x800))
    # SEL: every pattern of reads per chunk (0..T-1 stalls then ok / bad,
    # or T stalls), XA commands busy for 0 / 30 / for ever
    n = max(len(rt_chunks), 1)
    pats = []

    def walk(k, seq):
        if k == n:
            pats.append(seq)
            return
        for st in range(T):
            walk(k + 1, seq + ["stall"] * st + ["ok"])
            pats.append(seq + ["stall"] * st + ["bad"])
        pats.append(seq + ["stall"] * T)
    walk(0, [])
    worst = 0
    errs = []
    cases = set()
    for g in (0, 30, 10 ** 6):
        for p in pats:
            res, k, frames, reads = sel_reader(n, p, g, W, T)
            if res is None:
                errs.append("SEL's reader never returns 1 (%s, XA busy %d)" % (p, g))
                continue
            ok_all = k == n
            if ok_all != (res == "RT") or (res == "dub" and k >= n):
                errs.append("SEL's reader: %s after %d chunk(s) (%s)" % (res, k, p))
            if reads > n * T:
                errs.append("SEL's reader: %d reads for %d chunks" % (reads, n))
            cases.add((res, k))
            worst = max(worst, frames)
    # sysopt: up to 4 failed reads anywhere (bad or stall), the rest ok
    n_sel = max(len(chunks), 1)
    soutc = set()
    seqs = [[]]
    for _ in range(4):
        seqs += [s + ["ok"] * i + [f] for s in seqs for i in range(max(n, n_sel) + 1)
                 for f in ("bad", "stall")]
        seqs = [list(x) for x in {tuple(s) for s in seqs}]
    for from_tag in ("dub", 0):
        for sq in seqs:
            tag, passes, reads, fails = sysopt_reader(n, n_sel, sq, W, from_tag)
            if tag is None:
                errs.append("sysopt's reader never ends (%s)" % sq)
                continue
            if tag not in ("RT", "dub") and fails < 4:
                errs.append("sysopt's reader ends with tag %s after %d fails" % (tag, fails))
            if tag == "RT" and fails >= 2:
                errs.append("sysopt's reader: RT applied after giving it up")
            soutc.add((from_tag, tag, tuple((p, k) for p, k in passes)))
    # the RAM of every way they end: the dub fallbacks are restore + dub
    # after any cut, which rt_proof covers chunk by chunk; here every pass
    # chain sysopt can run, on the real packs
    ram_runs = 0
    if rt_packs:
        for pk in (0, 1):
            ref = Game(dra, dub, chunks, rt_chunks, d)
            ref.default(pk)
            want = ref.state()
            rt = Game(dra, dub, chunks, rt_chunks, d)
            rt.default(pk)
            rt.retrans()
            rt_state = rt.state()
            for res, k in sorted(cases, key=str):
                g = Game(dra, dub, chunks, rt_chunks, d)
                g.default(pk)
                g.retrans(upto=k)
                if res == "dub":
                    g.default(pk)
                ram_runs += 1
                if g.state() != (rt_state if res == "RT" else want):
                    errs.append("SEL: %s after %d RT chunk(s): RAM not the %s state" % (res, k, res))
            for from_tag, tag, passes in sorted(soutc, key=str):
                g = Game(dra, dub, chunks, rt_chunks, d)
                g.default(pk)
                if from_tag == 0:  # (an RT pass cut after its first chunk)
                    run_pack(g.ram, rt_chunks, tp.PACK_RT, d, 1)
                for p, k in passes:
                    full = k >= (n if p == "RT" else n_sel)
                    if p == "RT":
                        g.tag = 0
                        run_pack(g.ram, rt_chunks, tp.PACK_RT, d, None if full else k)
                    elif p == "restore":
                        g.tag = 0
                        run_pack(g.ram, chunks, tp.PACK_RESTORE, d, None if full else k)
                    else:
                        run_pack(g.ram, chunks, pk, d, None if full else k)
                ram_runs += 1
                if tag == "RT" and g.state() != rt_state or tag == "dub" and g.state() != want:
                    errs.append("sysopt: passes %s end in %s, RAM not that state" % (passes, tag))
    for e in errs[:8]:
        fail(e)
    if not errs:
        print("OK   text packs: CD readers: SEL %d read patterns x XA busy 0/30/never (stalls, bad chunks, "
              "%d tries of %d vblanks) all return within %d frames with RT or the dub's text; sysopt %d "
              "fail patterns end RT / dub / given up after 4; %d end states' RAM checked; SEL reads "
              "g_CdSoundCommandQueuePos 0x%X, D_801390A0 0x%X" % (len(pats), T, W, worst, len(seqs),
                                                                 ram_runs, syms["g_CdSoundCommandQueuePos"],
                                                                 syms["D_801390A0"]))


if __name__ == "__main__":
    main()
