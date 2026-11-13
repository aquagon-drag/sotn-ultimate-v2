#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Text packs: DRA's item / enemy / relic / menu names and descriptions for
one script, applied over DRA's own strings at run time
(include/game_mod.h MOD_TEXT_*, applier mods/sotn-ultimate/src/menu/
text_pack.h: SEL at every game start / load, the System screen's popup in
Alucard games when the Dub or Script row changes).

Packs built today (the text the mod already had, from the PSP port; the user
picked these changes 2026-10-24):

FIXED, the same in every pack (Natto, "[2 handed]", "Restores HP", the
Silver Ring's "...in...Room", the Medal's "ATT+1", the Faerie Scroll's stray
space, the enemy name fixes): each new string is written into the overflow
room A of g_ModDub (DRA BSS, resident in every game) and the table entry
points at it.

FOLLOWS THE DUB (pack 0 "PS1": the PS1 script's words; pack 1 "PSP": the
PSP's): every PSP string fits in the bytes of the PS1 string it replaces, so
the pack writes the chosen version over DRA's own string, in place.

A pack is a whole state over every byte and pointer any pack writes (both
packs carry the fixed strings and both versions' spans), so applying one
gives the same RAM whatever was applied before.

Usage:
  text_packs.py            build the packs from the built DRA, print a report
  text_packs.py --apply    ... and write the chunk(s) into build/us/SEL.BIN's
                           dead config copy (after SEL's final link; prints
                           "SEL.BIN" when it changed the file)

The chunk format and the run-time applier are mirrored by apply_chunk()
below; mods/sotn-ultimate/tools/check_text_packs.py checks both against the
retired per-frame mechanism of step 3 (text_packs_legacy.json).

Names are stored in the game's _S encoding (each character - 0x20, a space
is 0, then 0xFF 0); descriptions as raw bytes, punctuation as Shift-JIS
pairs."""
import json
import os
import re
import struct
import subprocess
import sys

from mod_work import read_src

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
BUILD = os.path.join(ROOT, "build/us")
OUT_JSON = os.path.join(BUILD, "text_packs.json")
DRA_BASE = 0x800A0000
SEL_BASE = 0x80180000
# SEL's dead copy of DRA's config tables (src/st/sel/config_us.c): file
# offsets [0x25FC, 0x25FC + 0x7F10), the first MOD_CREDITS_PSP_AREA bytes of
# it the staff roll of Ending = PSP (a live table: a reference to it is fine)
DEAD_START, DEAD_END = 0x25FC + 0x5A0, 0x25FC + 0x7F10
PACK_NAMES = {0: "PS1", 1: "PSP"}

# tables: 0 g_EquipDefs (0x34 per record), 1 g_AccessoryDefs (0x20),
# 2 g_EnemyDefs (0x28), 3 g_RelicDefs (0x10), 4 g_MenuStr (4)
TABLES = ["g_EquipDefs", "g_AccessoryDefs", "g_EnemyDefs", "g_RelicDefs", "g_MenuStr"]
STRIDE = {0: 0x34, 1: 0x20, 2: 0x28, 3: 0x10, 4: 4}

# --- fixed: (table, index, field offset, change) -------------------------
# change: a new name, or [(old bytes, new bytes)] in the retail description
HAND2 = [(b" hand\x81\x6E", b" handed\x81\x6E")]  # "[2 hand]" -> "[2 handed]"
FIXED = [
    (0, 0x03B, 0, "Natto"),
    *[(0, k, 4, HAND2) for k in (0x15, 0x1A, 0x1B, 0x54, 0x5F, 0x64, 0x65, 0x8B, 0x8D)],
    (1, 0x2A, 4, [(b"Heals", b"Restores")]),
    (1, 0x49, 4, [(b"Tower", b"Room")]),
    (1, 0x52, 4, [(b"ATT\x20\x81\x7B", b"ATT\x81\x7B")]),
    (3, 15, 4, [(b"name ", b"name")]),  # Faerie Scroll: the stray space
    (2, 0x059, 0, "Medusa Head"),  # unused record (no stage uses it)
    (2, 0x08E, 0, "Orobourous"),
    (2, 0x08F, 0, "Orobourous Rider"),  # 16: fits BottomCornerText; not listed
    (2, 0x108, 0, "Tin Man"),
    (2, 0x10F, 0, "Cloaked Knight"),
    (2, 0x11D, 0, "Balloon Pod"),
    (2, 0x126, 0, "Scylla Wyrm"),
    (2, 0x144, 0, "Beelzebub"),
    (2, 0x16B, 0, "Cerberus"),
]
# The cut Outer Wall skull (record 0xB1), placed only when the build defines
# MOD_OUTER_WALL_GHOST: retail leaves its name empty, so the Faerie Scroll
# would show an empty box when it is hit. The PSP port names it "Ghost", but
# retail already has a Ghost (0x09C, the Library one), so the mod calls it
# "Ghost Skull" (Faerie Scroll + its Library entry No.165,
# mods/sotn-ultimate/tools/gen_saturn_bestiary.py).
GHOST = re.search(r"^#define MOD_OUTER_WALL_GHOST *$",
                  read_src("include/game.h"), re.M) is not None
if GHOST:
    FIXED.append((2, 0x0B1, 0, "Ghost Skull"))

# --- follows the dub: (table, index, field, PS1 text, PSP text, kind) -----
# kind: "s" _S name, "c" plain C string
DUB = [
    (0, 0x000, 0, "Empty hand", "Unarmed", "s"),
    (1, 0x00, 0, "----", "none", "s"),  # one string for the 4 empty slots
    (2, 0x0CB, 0, "Minotaurus", "Minotaur", "s"),
    (3, 23, 0, "Sprite Card", "Fairy Card", "c"),
    (3, 23, 4, "Summons ””Pixie”” familiar", "Summons ””Fairy”” familiar", "c"),
    (3, 24, 0, " Nosedevil Card", " N Demon Card", "c"),
    (3, 24, 4, "Summons ””Nose−devil”” familiar", "Summons ””N Demon”” familiar", "c"),
    (4, 51, 0, "Sprite", "Fairy", "s"),
    (4, 52, 0, "N.Devil", "N Demon", "s"),
]
SJIS = {"”": b"\x81\x68", "−": b"\x81\x7C", "’": b"\x81\x66"}


def s_bytes(text):
    """the _S encoding: each character - 0x20 (a space is 0), then 0xFF 0 (a
    name ends at 0xFF followed by 0: src/st/popup.h BottomCornerText)"""
    assert all(0x20 <= ord(c) < 0x80 for c in text), text
    return bytes(ord(c) - 0x20 for c in text) + b"\xff\0"


def c_bytes(text):
    return b"".join(SJIS[c] if c in SJIS else c.encode("ascii") for c in text) + b"\0"


# --- constants shared with the C side -------------------------------------
def c_defines():
    """the MOD_TEXT_* numbers of include/game_mod.h and the SEL sector of
    include/lba_us.h, as the C code computes them"""
    src = open(os.path.join(ROOT, "mods/sotn-ultimate/include/game_mod.h"), encoding="utf-8").read()
    d = {k: int(v, 0) for k, v in re.findall(r"#define (MOD_TEXT_\w+|MOD_DUB_STATE_ADDR) +(0x[0-9A-Fa-f]+|\d+)\b", src)}
    lba = open(os.path.join(ROOT, "include/lba_us.h")).read()
    d["ST_SEL_BIN_OFF"] = int(re.search(r"#define ST_SEL_BIN_OFF (0x[0-9A-Fa-f]+)", lba)[1], 16)
    first = d["MOD_TEXT_BLOB_FIRST"]
    sector = first + ((d["MOD_TEXT_DEMOKEY_LBA"] - d["ST_SEL_BIN_OFF"] - first) & 3)
    d["SECTOR"] = sector
    d["CD_IDX"] = (d["ST_SEL_BIN_OFF"] + sector - d["MOD_TEXT_DEMOKEY_LBA"]) // 4
    assert d["ST_SEL_BIN_OFF"] + sector - d["MOD_TEXT_DEMOKEY_LBA"] == 4 * d["CD_IDX"]
    assert first * 0x800 >= DEAD_START and (first - 1) * 0x800 < DEAD_START
    return d


def chunk_room(d, c):
    """the bytes chunk c may use: its 4 sectors, cut at the dead copy's end"""
    off = (d["SECTOR"] + 4 * c) * 0x800
    return max(0, min(d["MOD_TEXT_CHUNK_LEN"], DEAD_END - off))


def dra_symbols(elf=None):
    out = subprocess.run(["mipsel-linux-gnu-nm", elf or os.path.join(BUILD, "dra.elf")],
                         capture_output=True, text=True, check=True).stdout
    return {p[2]: int(p[0], 16) for p in (l.split() for l in out.splitlines()) if len(p) == 3}


# --- a little RAM model: DRA's image + g_ModDub ---------------------------
def dra_image(path, syms):
    """DRA as loaded: its data, rodata and code (the file goes on past the
    BSS start; the model keeps g_ModDub, in the BSS, apart)"""
    return open(path, "rb").read()[:syms["dra_BSS_START"] - DRA_BASE]


class Ram:
    def __init__(self, dra, dub_addr, dub=None):
        assert DRA_BASE + len(dra) <= dub_addr
        self.regions = [(DRA_BASE, bytearray(dra)), (dub_addr, bytearray(dub or bytes(4096)))]

    def _at(self, addr, n):
        for base, buf in self.regions:
            if base <= addr and addr + n <= base + len(buf):
                return buf, addr - base
        raise IndexError("0x%08X+%d is outside the model" % (addr, n))

    def read(self, addr, n):
        buf, o = self._at(addr, n)
        return bytes(buf[o:o + n])

    def write(self, addr, data):
        buf, o = self._at(addr, len(data))
        buf[o:o + len(data)] = data

    def u32(self, addr):
        return struct.unpack("<I", self.read(addr, 4))[0]

    def w32(self, addr, v):
        self.write(addr, struct.pack("<I", v & 0xFFFFFFFF))

    def cstr(self, addr, kind):
        """a string's bytes with its end: "s" up to 0xFF 0, "c" up to 0"""
        out = b""
        while True:
            b = self.read(addr + len(out), 1)
            out += b
            if kind == "c" and b == b"\0":
                return out
            if kind == "s" and out[-2:] == b"\xff\0":
                return out


# --- the packs -----------------------------------------------------------
def build_packs(ram, syms, d):
    """the records of each pack, from the DRA image in ram (unapplied):
    [("copy", dst, bytes) | ("ptr", slots, base, [(word, off)])]"""
    tbl = [syms[t] for t in TABLES]
    dub = syms["g_ModDub"]
    ovf_a = dub + d["MOD_TEXT_OVF_A_OFF"]
    slot = lambda t, i, f: tbl[t] + i * STRIDE[t] + f
    # fixed: the new strings one after the other in room A, each
    # word-aligned (step 3's g_ModDub.fixedText layout: same addresses)
    blob, ptrs, touched = b"", {}, set()
    for table, idx, field, change in FIXED:
        s = slot(table, idx, field)
        assert s not in touched, ("slot twice", table, hex(idx))
        touched.add(s)
        if isinstance(change, str):
            if table == 2:
                assert len(change) <= (16 if idx == 0x08F else 15), change
            new = s_bytes(change)
        else:
            old = ram.cstr(ram.u32(s), "c")
            (a, b), = change
            assert old.count(a) == 1, (table, hex(idx), a, old)
            new = old.replace(a, b)
        new += bytes(-len(new) % 4)
        ptrs.setdefault(table, []).append(((s - tbl[table]) // 4, len(blob)))
        blob += new
    assert len(blob) <= d["MOD_TEXT_OVF_A_LEN"], len(blob)
    common = [("copy", ovf_a, blob)]
    common += [("ptr", tbl[t], ovf_a, sorted(ptrs[t])) for t in sorted(ptrs)]
    # the dub's strings: per version, the span where the versions differ,
    # over DRA's own string (the retail bytes are the PS1 version's)
    spans = {0: [], 1: []}
    for table, idx, field, ps1, psp, kind in DUB:
        s = slot(table, idx, field)
        assert s not in touched, ("slot twice", table, hex(idx))
        touched.add(s)
        enc = s_bytes if kind == "s" else c_bytes
        a, b = enc(ps1), enc(psp)
        assert len(b) <= len(a), (ps1, psp)
        b += bytes(len(a) - len(b))  # zeros: a name ends at 0xFF then 0
        at = ram.u32(s)
        assert ram.read(at, len(a)) == a, ("DRA's string is not the PS1 text", ps1, ram.read(at, len(a)))
        diff = [k for k in range(len(a)) if a[k] != b[k]]
        lo, hi = diff[0], diff[-1] + 1
        spans[0].append(("copy", at + lo, a[lo:hi]))
        spans[1].append(("copy", at + lo, b[lo:hi]))
    packs = {p: common + spans[p] for p in (0, 1)}
    fp = [footprint(packs[p]) for p in (0, 1)]
    assert fp[0] == fp[1], "the packs must touch the same bytes and pointers"
    return packs


def footprint(recs):
    bytes_, ptrs = set(), set()
    for r in recs:
        if r[0] == "copy":
            bytes_ |= set(range(r[1], r[1] + len(r[2])))
        else:
            ptrs |= {r[1] + 4 * w for w, _ in r[3]}
    return bytes_, ptrs


def enc_record(r):
    if r[0] == "copy":
        _, dst, data = r
        assert len(data) < 0x10000
        return struct.pack("<HHI", 1, len(data), dst) + data + bytes(-len(data) % 4)
    _, slots, base, items = r
    return struct.pack("<HHII", 2, len(items), slots, base) + b"".join(
        struct.pack("<HH", w, o) for w, o in items)


def split_record(r, room):
    """r cut so that its first part encodes in room bytes (or None)"""
    if r[0] == "copy":
        n = (room - 8) & ~3
        if n < 4:
            return None
        return ("copy", r[1], r[2][:n]), ("copy", r[1] + n, r[2][n:])
    n = (room - 12) // 4
    if n < 1:
        return None
    return ("ptr", r[1], r[2], r[3][:n]), ("ptr", r[1], r[2], r[3][n:])


def encode_chunks(packs, d):
    """the chunk stream: each pack's records in order, a chunk filled before
    the next (a record cut where it does not fit)"""
    npk = d["MOD_TEXT_PACKS"]
    hdr = 0x10 + 2 * npk
    chunks = []  # per chunk: {pack: [encoded records]}
    used = []

    def new_chunk():
        chunks.append({})
        used.append(hdr)

    new_chunk()
    for p in sorted(packs):
        todo = list(packs[p])
        while todo:
            r = todo.pop(0)
            c = len(chunks) - 1
            # its records here + their end marker
            start = 0 if p in chunks[c] else 4
            room = chunk_room(d, c) - used[c] - start
            e = enc_record(r)
            if len(e) <= room:
                chunks[c].setdefault(p, []).append(e)
                used[c] += len(e) + start
                continue
            cut = split_record(r, room)
            if cut:
                chunks[c].setdefault(p, []).append(enc_record(cut[0]))
                used[c] += len(enc_record(cut[0])) + start
                todo.insert(0, cut[1])
            else:
                todo.insert(0, r)
            new_chunk()
            if chunk_room(d, len(chunks) - 1) < hdr + 16:
                sys.exit("text packs: %d bytes do not fit SEL's dead config copy" % sum(used))
    out = []
    for c, ch in enumerate(chunks):
        body, offs, mask = b"", [0] * npk, [0] * npk
        for p in sorted(ch):
            offs[p] = hdr + len(body)
            body += b"".join(ch[p]) + struct.pack("<HH", 0, 0)
        for p in packs:
            mask[p] = sum(1 << k for k, chk in enumerate(chunks) if p in chk)
        size = hdr + len(body)
        h = struct.pack("<BBBB", c, len(chunks), len(packs), 1) + bytes(mask) + \
            struct.pack("<%dH" % npk, *offs)
        payload = h + body
        assert len(payload) % 2 == 0
        csum = sum(struct.unpack("<%dH" % (len(payload) // 2), payload)) & 0xFFFF
        blob = struct.pack("<IHH", d["MOD_TEXT_MAGIC"], size, csum) + payload
        assert len(blob) == size <= chunk_room(d, c)
        out.append(blob)
    return out


# --- the run-time applier, byte for byte (text_pack.h) ---------------------
def chunk_ok(c, d):
    """ModTextChunkOk"""
    if len(c) < 8:
        return False
    magic, size, csum = struct.unpack_from("<IHH", c)
    if magic != d["MOD_TEXT_MAGIC"] or size > d["MOD_TEXT_CHUNK_LEN"] or size < 0x18 or size > len(c):
        return False
    return sum(struct.unpack_from("<%dH" % ((size - 8) // 2), c, 8)) & 0xFFFF == csum


def apply_chunk(ram, c, pack):
    """ModTextRun: pack's records in chunk c, applied to ram"""
    n = struct.unpack_from("<H", c, 0x10 + 2 * pack)[0]
    if not n:
        return
    r = n
    while True:
        kind, n = struct.unpack_from("<HH", c, r)
        if kind == 1:
            dst = struct.unpack_from("<I", c, r + 4)[0]
            ram.write(dst, c[r + 8:r + 8 + n])
            r += 8 + ((n + 3) & ~3)
        elif kind == 2:
            slots, base = struct.unpack_from("<II", c, r + 4)
            r += 12
            for _ in range(n):
                w, off = struct.unpack_from("<HH", c, r)
                ram.w32(slots + 4 * w, base + off)
                r += 4
        else:
            break


def apply_pack(ram, chunks, pack, d):
    """the SEL / sysopt drivers: every chunk in order, checked first; the
    tag only once all applied (returns it, or 0)"""
    for i, c in enumerate(chunks):
        if not chunk_ok(c, d) or c[8] != i:
            return 0
        apply_chunk(ram, c, pack)
        if i + 1 >= c[9]:
            break
    return 0x54585400 | pack


def make(write=False):
    d = c_defines()
    syms = dra_symbols()
    dra = dra_image(os.path.join(BUILD, "DRA.BIN"), syms)
    ram = Ram(dra, syms["g_ModDub"])
    packs = build_packs(ram, syms, d)
    chunks = encode_chunks(packs, d)
    edits = []
    changed = False
    sel_path = os.path.join(BUILD, "SEL.BIN")
    if write:
        sel = bytearray(open(sel_path, "rb").read())
        for c, blob in enumerate(chunks):
            off = (d["SECTOR"] + 4 * c) * 0x800
            assert DEAD_START <= off and off + len(blob) <= DEAD_END
            if sel[off:off + len(blob)] != blob:
                sel[off:off + len(blob)] = blob
                changed = True
            edits.append([off, len(blob)])
        if changed:
            open(sel_path, "wb").write(sel)
    info = {
        "sector": d["SECTOR"], "cd_idx": d["CD_IDX"], "sel_off": d["ST_SEL_BIN_OFF"],
        "sel_edits": edits or [[(d["SECTOR"] + 4 * c) * 0x800, len(b)] for c, b in enumerate(chunks)],
        "chunks": [b.hex() for b in chunks],
    }
    json.dump(info, open(OUT_JSON, "w"), indent=1)
    return d, packs, chunks, changed


def main():
    write = "--apply" in sys.argv[1:]
    d, packs, chunks, changed = make(write)
    per = {p: sum(len(enc_record(r)) for r in packs[p]) for p in packs}
    print("text packs: %s; %d chunk(s) %s at SEL sector %d (file 0x%X, g_LoadOvlIdx %d)%s" % (
        ", ".join("%s %d B" % (PACK_NAMES[p], per[p]) for p in sorted(per)),
        len(chunks), "+".join(str(len(c)) for c in chunks), d["SECTOR"], d["SECTOR"] * 0x800,
        d["CD_IDX"], (" (SEL.BIN)" if changed else " (already)") if write else ""))


if __name__ == "__main__":
    main()
