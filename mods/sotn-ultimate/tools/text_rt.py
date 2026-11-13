#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The fan retranslation's DRA text (Script = Retrans), derived at build time
from the builder's own copy of the patched Japanese disc.

The retranslation (romhacking.net #1427, Gemini and Tom) patches the Japanese
PS1 disc (SLPM-86023 Rev 2). Its text is NOT in this repository: like the
Saturn and PSP content, the build reads it from the builder's files,
disks/jpre/ (gitignored: the files of the patched disc, extracted like
disks/us; this step reads only disks/jpre/DRA.BIN, checked by SHA-1 so a
wrong file fails loudly). What is committed here is only: file offsets of
the Japanese DRA's tables, the Japanese -> US index mapping, the decoding of
the patch's two encodings, the re-encoding rules for the US renderers, the
fit limits of the US drawing code, and the mod's own names for the
Saturn-only entries.

Without disks/jpre/DRA.BIN the build still succeeds: no retranslation pack
is made, SD/TXT_RT.BIN is an empty placeholder, and Script = Retrans shows
the dub's text (MOD_TEXT_RT_ON() is 0: include/game_mod.h).

What it covers (the strings the US DRA draws, all through tables, so the
pack only rewrites strings and table pointers; no code changes):
  equipment (228 in the mod: retail 0..168, Saturn 169..175, the retail
  special records moved to 176..223, Saturn specials 224..227) and
  accessory (93: retail 0..89, Saturn 90..92) names and descriptions,
  relic (32: retail 0..29, Saturn Godspeed Shoes 30, blank 31) names and
  descriptions, spell names and descriptions (combos stay: the same
  inputs), enemy names (426: retail 0..399, Saturn 400..425), g_MenuStr
  (110: retail 0..84 = Japanese 0..84; the US-only 85..109 from the
  patch's two menu word lists), the System screen's help lines, and the
  save point's memory card messages (code literals: rewritten in place
  only, when the new text fits the literal's bytes).

Encodings out (the US engine's, unchanged): names, enemy names and menu
words in the 8x8 font (_S: each character - 0x20, end 0xFF 0); relic and
spell names, descriptions, help lines and the save messages through the
BIOS-font renderer (func_800F99B8: ASCII letters and space, everything else
as Shift-JIS pairs). With the RT pack applied, that renderer draws them with
the patch's own 12 px font instead (mods/sotn-ultimate/src/menu/rt_font.c;
its glyphs and widths: rt_font() below, from the same DRA.BIN), so their
fit is measured with it (rt_draw).

Usage:
  text_rt.py              print a summary (or "no inputs")
  text_rt.py --report F   also write the fit / mapping report (markdown)
                          to F (outside the repository: it quotes the text)
"""
import hashlib
import os
import re
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
INPUT_DIR = os.environ.get("MOD_JPRE_DIR") or os.path.join(ROOT, "disks", "jpre")
JP_DRA = os.path.join(INPUT_DIR, "DRA.BIN")
US_DRA = os.path.join(ROOT, "disks", "us", "DRA.BIN")
# the user's wording decisions (gitignored: it holds translation text);
# format in mods/sotn-ultimate/tools/text_rt_overrides.template.tsv
OVERRIDES = os.path.join(INPUT_DIR, "rt_overrides.tsv")
# SHA-1 of DRA.BIN of SLPM-86023 Rev 2 with the #1427 patch applied
JP_DRA_SHA1 = "3d038c447f75bb705fd39e8744c150959da9208c"
US_DRA_SHA1 = None  # (the US disc is checked by the builder already)
DRA_BASE = 0x800A0000

# --- the patched Japanese DRA (file offsets) ------------------------------
JP_EQUIP = (0x4B70, 217, 0x34)  # {name ENC8, desc ENC12, ...}
JP_ACC = (0x7784, 90, 0x20)  # {name ENC8, desc ENC12, ...}
JP_MENU = (0x82C4, 85)  # g_MenuStr, ENC8
JP_SPELL = (0x8418, 28, 0x1C)  # {name ENC12, combo ENC8, desc ENC12, ...}
JP_RELIC = (0x8728, 30, 0x10)  # {name ENC12, desc ENC12, ...}
JP_ENEMY = (0x8908, 400, 0x28)  # {name ENC8, ...}
JP_HELP = 0x2D48  # 7 help lines, then the two menu word lists (ENC12, 0x01 = new line)
JP_SAVEMSG = (0x3CEA8, 22)  # save messages (ENC12)
JP_DTE = 0x40C50  # 128 two-glyph pairs for ENC12 bytes 0x80-0xFF
# --- the retail US DRA (disks/us), for the alignment proof -----------------
US_EQUIP, US_ACC, US_MENU, US_SPELL, US_RELIC, US_ENEMY = 0x4B04, 0x7718, 0x8258, 0x8410, 0x8720, 0x8900
# equipment field 0x1A differs between the Japanese and US records of these
# swords (a balance value); every other non-string byte of every record of
# the five tables is equal (checked below)
EQUIP_FIELD_1A = {104, 105, 106, 108, 110, 111, 112, 113, 115, 116, 117, 118, 122, 123, 124,
                  125, 126, 139, 140, 141, 168}

# --- ENC8 / ENC12 (the patch's encodings) -----------------------------------
# ENC8: 0x01-0x5E = ASCII - 0x20 with these slots redrawn, 0x5F = space,
# 0x60-0x6F two-letter tiles; 0x00 / 0xFF end
ENC8_SUB = {0x07: ",", 0x1B: "'", 0x20: "è", 0x3B: "à", 0x3C: "è", 0x3D: "é", 0x3E: "ì", 0x3F: "ò",
            0x40: "ù", 0x5B: "ä", 0x5C: "ō", 0x5D: "ū", 0x5E: "ü", 0x5F: " ",
            0x60: "ae", 0x61: "ë", 0x62: "il", 0x63: "ll", 0x64: "li", 0x65: "a ", 0x66: "e ",
            0x68: "o ", 0x69: " d", 0x6A: "el", 0x6C: "di", 0x6D: " c", 0x6E: "ti", 0x6F: "ri"}
# ENC12: 0x00 end, 0x01 new line, 0x20-0x7F glyph (b - 0x20), 0x80-0xFF a
# DTE pair from the table at JP_DTE
ENC12_SET = " !\"(),'àèéìòùÈ:?-.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
ENC12_EXTRA = {0x70: "+", 0x72: "↓", 0x73: "↑", 0x74: "→", 0x75: "↘", 0x77: "%"}

# --- the US encodings ------------------------------------------------------
# characters the US 8x8 font (F_GAME, the _S table of tools/sotn_str) and
# the BIOS font renderer cannot show, and what they become (listed in the
# report)
PLAIN = {"à": "a", "ä": "a", "è": "e", "é": "e", "ë": "e", "ì": "i", "ò": "o", "ō": "o",
         "ù": "u", "ū": "u", "ü": "u", "È": "E"}
S_CHARS = " !\"#$%&'()+,-./0123456789:=?ABCDEFGHIJKLMNOPQRSTUVWXYZ[]_abcdefghijklmnopqrstuvwxyz~"
S_CODE = {"\"": 0x02, "'": 0x07}
# BIOS renderer: Shift-JIS for everything but letters and space; a double
# quote is two 0x8168 pairs (the renderer skips the second, as US text does)
SJIS = {",": b"\x81\x43", ".": b"\x81\x44", ":": b"\x81\x46", "?": b"\x81\x48", "!": b"\x81\x49",
        "/": b"\x81\x5E", "'": b"\x81\x66", "\"": b"\x81\x68\x81\x68", "(": b"\x81\x69",
        ")": b"\x81\x6A", "[": b"\x81\x6D", "]": b"\x81\x6E", "+": b"\x81\x7B", "-": b"\x81\x7C",
        "%": b"\x81\x93", "→": b"\x81\xA8", "←": b"\x81\xA9", "↑": b"\x81\xAA", "↓": b"\x81\xAB",
        # no diagonal arrow in JIS X 0208: the full-width reverse solidus
        "↘": b"\x81\x5F"}
for _d in range(10):
    SJIS[str(_d)] = bytes([0x82, 0x4F + _d])


def to_s(text):
    """the US 8x8 _S bytes (no terminator)"""
    out = b""
    for c in text:
        c = PLAIN.get(c, c)
        assert c in S_CHARS, "no 8x8 glyph for %r in %r" % (c, text)
        out += bytes([S_CODE.get(c, ord(c) - 0x20)])
    return out


def to_bios(text):
    """the BIOS renderer's bytes (no terminator)"""
    out = b""
    for c in text:
        c = PLAIN.get(c, c)
        if c == " " or ("a" <= c <= "z") or ("A" <= c <= "Z"):
            out += c.encode()
        else:
            assert c in SJIS, "no BIOS mapping for %r in %r" % (c, text)
            out += SJIS[c]
    return out


def from_s(b):
    """US _S bytes -> text (ASCII part only; other glyphs as {xx})"""
    inv = {v: k for k, v in S_CODE.items()}
    return "".join(inv.get(c) or (chr(c + 0x20) if c < 0x5F and chr(c + 0x20) in S_CHARS else "{%02X}" % c)
                   for c in b)


def from_bios(b):
    inv = {v: k for k, v in SJIS.items()}
    inv[b"\x81\x68"] = "\""
    out, i = "", 0
    while i < len(b):
        c = b[i]
        if c < 0x80:
            out += chr(c)
            i += 1
        else:
            p = b[i:i + 2]
            out += inv.get(p) or p.decode("shift_jis", "replace")
            i += 4 if p == b"\x81\x68" else 2
    return out


# --- BIOS font widths (approximate) -----------------------------------------
# Advance in pixels of each character through func_800F99B8 (the glyph is the
# BIOS's 16x15 Shift-JIS glyph scaled to 12 px by func_80106A28, left blank
# columns trimmed in pairs, its right edge rounded up to a byte, + one byte if
# narrower than 12 px; a space is 6 px). Measured with the same algorithm on
# the public-domain Shinonome 14-dot font of PCSX-Redux's OpenBIOS, not on the
# real BIOS font (not available to the build): an estimate. With it the
# widest US help line measures 288 px and the widest US relic name 120 px,
# exactly the renderer's limits.
BIOS_W = {" ": 6}
for _c, _w in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [12, 10, 10, 10, 10, 10, 12, 10, 6, 8, 10, 10, 12,
                                                    10, 12, 10, 12, 10, 8, 10, 10, 12, 12, 12, 10, 12]):
    BIOS_W[_c] = _w
for _c, _w in zip("abcdefghijklmnopqrstuvwxyz", [8, 8, 8, 8, 8, 8, 8, 8, 6, 6, 8, 6, 10,
                                                    8, 8, 8, 8, 8, 10, 8, 8, 10, 12, 8, 8, 8]):
    BIOS_W[_c] = _w
BIOS_W_SJIS = {b"\x81\x43": 4, b"\x81\x44": 4, b"\x81\x46": 4, b"\x81\x48": 8, b"\x81\x49": 4,
               b"\x81\x5E": 12, b"\x81\x5F": 12, b"\x81\x66": 4, b"\x81\x68": 8, b"\x81\x69": 6,
               b"\x81\x6A": 6, b"\x81\x6D": 6, b"\x81\x6E": 6, b"\x81\x7B": 12, b"\x81\x7C": 12,
               b"\x81\x93": 12, b"\x81\xA8": 12, b"\x81\xA9": 12, b"\x81\xAA": 8, b"\x81\xAB": 8,
               b"\x81\x40": 6}
for _d in range(10):
    BIOS_W_SJIS[bytes([0x82, 0x4F + _d])] = 6 if _d == 1 else 8


def bios_width(b):
    """estimated pixels of BIOS-renderer bytes b (None: a glyph not in the
    table)"""
    w, i = 0, 0
    while i < len(b):
        c = b[i]
        if c < 0x80:
            if chr(c) not in BIOS_W:
                return None
            w += BIOS_W[chr(c)]
            i += 1
        else:
            p = b[i:i + 2]
            if p not in BIOS_W_SJIS:
                return None
            w += BIOS_W_SJIS[p]
            i += 4 if p == b"\x81\x68" else 2
    return w


# --- the retranslation's 12 px font (Script = Retrans) ----------------------
# DRA's func_800F99B8 hands its strings to mods/sotn-ultimate/src/menu/
# rt_font.c ModRtText while the RT pack is applied; that pack carries the
# code and the patch's font, read here from the builder's DRA.BIN. This is a
# pixel-exact model of ModRtText (the fit limits and the preview use it).
JP_FONT = 0x40710  # 8x12, 1 bit per pixel (bit 7 = left), 12 bytes a glyph
JP_FONT_W = 0x40DC0  # the advance of each glyph, pixels
RT_GLYPHS = 112
RT_SRC = os.path.join(ROOT, "mods/sotn-ultimate/src/menu/rt_font.c")
RT_ROW0, RT_BODY, RT_SHADOW = 2, 7, 1  # as rt_font.c


def rt_font():
    """(widths, glyphs): the patch's width table and glyph bytes"""
    d = open(JP_DRA, "rb").read()
    return d[JP_FONT_W:JP_FONT_W + RT_GLYPHS], d[JP_FONT:JP_FONT + 12 * RT_GLYPHS]


def rt_sjis81():
    """rt_font.c's g_ModRtSjis81: {Shift-JIS 0x81xx: glyph}"""
    src = open(RT_SRC, encoding="utf-8").read()
    body = re.search(r"g_ModRtSjis81\[\]\[2\] = \{(.*?)\};", src, re.S)[1]
    return {0x8100 + int(a, 16): int(g) for a, g in re.findall(r"\{(0x[0-9A-Fa-f]+), (\d+)\}", body)}


RT_SJIS81 = rt_sjis81()


def rt_glyphs(b):
    """ModRtNext over b (no terminator): the glyph indices, or None when the
    font lacks a character (the BIOS font draws that string)"""
    out, i = [], 0
    while i < len(b):
        c = b[i]
        i += 1
        if c == 0x20:
            out.append(0)
        elif 0x41 <= c <= 0x5A:
            out.append(c - 0x41 + 28)
        elif 0x61 <= c <= 0x7A:
            out.append(c - 0x61 + 54)
        else:
            c = (c << 8) | (b[i] if i < len(b) else 0)
            i += 1
            if c == 0x8168:
                i += 2
            if 0x824F <= c < 0x824F + 10:
                out.append(c - 0x824F + 18)
            elif 0x8260 <= c < 0x8260 + 26:
                out.append(c - 0x8260 + 28)
            elif 0x8281 <= c < 0x8281 + 26:
                out.append(c - 0x8281 + 54)
            elif c in RT_SJIS81:
                out.append(RT_SJIS81[c])
            else:
                return None
    return out


def rt_draw(b, w, font=None):
    """ModRtText: the 16 rows of 2 * w pixel values (0, RT_SHADOW, RT_BODY)
    of b drawn into a cleared line of w bytes a row, and the string's
    extent (the first column right of every lit pixel, uncut); None when
    the font lacks a character"""
    widths, glyphs = font or rt_font()
    gs = rt_glyphs(b)
    if gs is None:
        return None
    end = 2 * w
    px = [[0] * end for _ in range(16)]
    pen = extent = 0
    for g in gs:
        prev = 0
        for r in range(13):
            m = glyphs[12 * g + r] << 8 if r < 12 else 0
            sh = ((m | prev) >> 1) | prev
            prev = m
            for k in range(9):
                bit = 0x8000 >> k
                v = RT_BODY if m & bit else RT_SHADOW if sh & bit else 0
                if v:
                    extent = max(extent, pen + k + 1)
                    if pen + k < end:
                        px[RT_ROW0 + r][pen + k] |= v
        pen += widths[g]
    return px, extent


_RT_FONT = None


def rt_width(b):
    """pixels b spans in the retranslation's font (None: it lacks a
    character)"""
    global _RT_FONT
    if _RT_FONT is None:
        _RT_FONT = rt_font()
    r = rt_draw(b, 0x90, _RT_FONT)
    return None if r is None else r[1]


def line_width(b):
    """what func_800F99B8 spans with the RT pack applied: the RT font, or
    the BIOS font (estimate) for a string the RT font cannot draw"""
    w = rt_width(b)
    return bios_width(b) if w is None else w


# --- fit limits of the US drawing code (see the report) --------------------
# (unit, limit, where)
LIMITS = {
    "item_name": ("chars", 15, "item lists (menu.c func_800F8990: the count right-aligned at "
                  "+128, 2 digits from +120); Equip screen name at x=112, a consumable's "
                  "(count) at x=224 (DrawConsumableCount): 14 for consumables; the cursor bar is "
                  "113 px"),
    "enemy_name": ("chars", 25, "Faerie Scroll box (st/popup.h BottomCornerText, right-aligned "
                   "at x=212, left cap at x-6 >= 0)"),
    "enemy_lib": ("chars", 15, "Librarian's enemy list (LIB e_shop.c: columns 120 px apart; "
                  "an overlay, listed only)"),
    "relic_name": ("px", 120, "Relic screen (func_800F9E18: func_800F99B8 with a 0x3C-byte "
                   "line = 120 px, cut where it ends)"),
    "spell_name": ("px", 240, "Spell screen (func_800F9F40: 288 px line shown by a 240 px "
                   "sprite); also <= 31 bytes (func_800F9DD0 copies 16 pairs)"),
    "desc": ("px", 288, "info bar (ShowText = func_800F99B8, 0x90-byte line = 288 px, cut "
             "where it ends)"),
    "menu": ("chars", None, "per string, below (MENU_LIMIT)"),
    "combo": ("chars", None, "spell inputs (kept)"),
    "savemsg": ("px", None, "the message box's width (62DEC.c), and the literal's bytes"),
}
# g_MenuStr: the characters (8 px) each index has where menu.c draws it,
# up to the next thing drawn on its row (the smallest where it is drawn
# twice); absent: not drawn by the US code
MENU_LIMIT = {}
for _ids, _n in [((0, 42), 15),  # status: name at x=128, LEVEL at x=248
                 ((1, 2, 3, 4), 3),  # STR..LCK: value right-aligned 3 digits at x+44
                 ((5, 8, 43, 44), 6),  # EXP / LEVEL: familiar labels at x+56, number at x+112
                 ((6, 7), 9),  # NEXT / GOLD at x=32, 6 digits right-aligned at x=144
                 ((15,), 14), ((9,), 6), ((10, 11), 8),  # STATUS; TIME (hours at x+56); ROOMS / KILLS
                 ((12, 13, 14), 6),  # HP / MP / HEART at x=96, 4 digits right-aligned at x=168
                 ((16, 17, 18, 32, 35, 36), 16),  # System rows at x=32, cursor 128 px
                 ((20, 21), 9),  # cloak colour rows at x=176, the R / G / B at x=248
                 ((22, 23, 24, 25, 26, 27, 28), 11),  # button rows at x=152, buttons from x=240
                 ((30, 31), 7), ((33, 34), 6),  # cloak lining box (65 px), sound box (57 px)
                 ((37, 38, 39, 40), 12),  # status word at x=260 (window 360)
                 ((46, 47, 48, 49, 50, 51, 52), 7),  # familiar name, its LEVEL label at x+56
                 (tuple(range(53, 80)), 29),  # time attack: x+21, the time from x+252
                 (tuple(range(85, 92)), 11),  # Equip slot label at x=8, icons from x=96
                 ((92, 93, 94, 95), 7), ((96,), 9),  # main menu window (76 px): words at +14 / +18 / +2
                 ((97,), 30), ((98,), 32),  # list titles at x=120 / x=104 (window 360)
                 (tuple(range(99, 110)), 9)]:  # Equip sort box (77 px, words at +4)
    for _i in _ids:
        MENU_LIMIT[_i] = _n
# US strings kept whatever the patch has: decorative or drawn by renderers
# that only have a few glyphs
MENU_KEEP = {19: "decorative dots", 41: "time attack blank row (30 dashes)", 80: "empty",
             81: "empty", 82: "empty", 83: "empty", 84: "empty"}
# g_MenuStr 85..109 (US only) <- (list, line) of the patch's menu word lists
# (JP_HELP + 7 and + 8, drawn there as texture strips); None: no matching
# line (the US text stays)
MENU_US_ONLY = {85: (7, 7), 86: (7, 8), 87: (7, 9), 88: (7, 10), 89: (7, 11), 90: (7, 12),
                91: (7, 12), 92: (7, 0), 93: (7, 1), 94: (7, 2), 95: (7, 3), 96: (7, 4),
                97: (7, 13), 98: (7, 14), 99: (8, 0), 100: (8, 1), 101: (8, 2), 102: (8, 3),
                103: (8, 4), 104: (8, 5), 105: (8, 12), 106: None, 107: (8, 11), 108: (8, 9),
                109: None}
# (lines 5 and 6 of list 7 are the US ATT / DEF of D_800A2D68, drawn from a
# 5-glyph sheet: not text. Lines 8 and 10 of list 8 are probably Bomb and
# Medicine, but nothing proves it: listed in the report as candidates)
MENU_CANDIDATES = {106: (8, 8), 109: (8, 10)}
# the save messages: US literal (62DEC.c) <- patch message, box width (px)
# (the lines of one message change together; box None: the US line's
# leading spaces, in the small Yes / No / slot boxes)
SAVEMSG = [
    ("Data saved\x81\x44", 0, 96, "saved"), ("Memory Card", 1, 96, "card"),
    ("  not found\x81\x44", 2, 96, "absent"), ("is Defective\x81\x44", 3, 96, "damaged"),
    ("Memory Card is", 4, 120, "unformatted"), ("not formatted\x81\x44", 5, 120, "unformatted"),
    ("Cannot", 6, 112, "cannot"), ("overwrite file\x81\x44", 7, 112, "cannot"),
    ("No game", 8, 112, "nodata"), ("data found\x81\x44", 9, 112, "nodata"),
    ("   \x82\x4F memory", 10, 112, "full"), ("blocks available\x81\x44", 11, 112, "full"),
    ("  Memory card", 12, 120, "formaterr"), ("  format error\x81\x44", 13, 120, "formaterr"),
    ("  Select the slot\x81\x44", 14, 144, "select"), (" Slot \x82\x50", 15, None, "slot1"),
    (" Slot \x82\x51", 16, None, "slot2"), (" Wish to format\x81\x48", 17, 144, "format"),
    (" Overwrite data\x81\x48", 18, 144, "overwrite"), ("   Wish to save\x81\x48", 19, 144, "save")]
# "Memory Card" opens both "absent" and "damaged" (one literal)
SAVEMSG_WITH = {"absent": "card", "damaged": "card"}
# Saturn-only entries (the mod's names, Title Case in this pack): by table
# and mod index
SATURN = {"equip": list(range(169, 176)), "acc": [90, 91, 92], "relic": [30],
          "enemy": list(range(400, 426))}


def title_case(text):
    return " ".join(w[:1].upper() + w[1:] for w in text.split(" "))


# --- reading ---------------------------------------------------------------
class Jp:
    def __init__(self, data):
        self.d = data
        self.dte = [(data[JP_DTE + 2 * i], data[JP_DTE + 2 * i + 1]) for i in range(128)]

    def u32(self, off):
        return struct.unpack_from("<I", self.d, off)[0]

    def enc8(self, ptr):
        o, out = ptr - DRA_BASE, ""
        while self.d[o] not in (0, 0xFF):
            c = self.d[o]
            if c in ENC8_SUB:
                out += ENC8_SUB[c]
            elif c < 0x5F:
                out += chr(c + 0x20)
            else:
                raise ValueError("ENC8 0x%02X at 0x%X" % (c, o))
            o += 1
        return out

    def g12(self, c):
        if c in ENC12_EXTRA:
            return ENC12_EXTRA[c]
        if 0x20 <= c < 0x20 + len(ENC12_SET):
            return ENC12_SET[c - 0x20]
        raise ValueError("ENC12 glyph 0x%02X" % c)

    def enc12(self, ptr):
        o, out = ptr - DRA_BASE, ""
        while self.d[o]:
            c = self.d[o]
            if c == 1:
                out += "\n"
            elif c >= 0x80:
                a, b = self.dte[c - 0x80]
                out += self.g12(a) + self.g12(b)
            else:
                out += self.g12(c)
            o += 1
        return out


def sha1(path):
    return hashlib.sha1(open(path, "rb").read()).hexdigest()


def inputs_state():
    """(ok, message)"""
    if not os.path.exists(JP_DRA):
        return False, "no %s: Script = Retrans shows the dub's text" % os.path.relpath(JP_DRA, ROOT)
    h = sha1(JP_DRA)
    if h != JP_DRA_SHA1:
        sys.exit("text_rt: %s has SHA-1 %s, expected %s (the DRA.BIN of SLPM-86023 Rev 2 with "
                 "the romhacking.net #1427 English patch)" % (JP_DRA, h, JP_DRA_SHA1))
    return True, "retranslation from %s (SHA-1 ok)" % os.path.relpath(JP_DRA, ROOT)


def alignment_proof(jp, us):
    """every non-string byte of every Japanese record equals the retail US
    record with the same index (the tables line up entry by entry)"""
    out = []

    def cmp(name, jo, uo, n, st, skip, allow=lambda i, k: False):
        bad = []
        for i in range(n):
            a = jp[jo + i * st:jo + (i + 1) * st]
            b = us[uo + i * st:uo + (i + 1) * st]
            diff = [k for k in range(skip, st) if a[k] != b[k] and not allow(i, k)]
            if diff:
                bad.append((i, diff))
        assert not bad, "%s: Japanese and US records differ: %s" % (name, bad[:5])
        out.append("%s: %d records, bytes 0x%X-0x%X equal" % (name, n, skip, st))

    cmp("equipment", JP_EQUIP[0], US_EQUIP, 217, 0x34, 8,
        lambda i, k: k in (0x1A,) and i in EQUIP_FIELD_1A)
    cmp("accessories", JP_ACC[0], US_ACC, 90, 0x20, 8)
    cmp("spells", JP_SPELL[0], US_SPELL, 28, 0x1C, 12)
    cmp("relics", JP_RELIC[0], US_RELIC, 30, 0x10, 8)
    cmp("enemies", JP_ENEMY[0], US_ENEMY, 400, 0x28, 4)
    # the US table offsets are right: their first names
    assert us[struct.unpack_from("<I", us, US_EQUIP)[0] - DRA_BASE:][:10] == bytes(
        ord(c) - 0x20 for c in "Empty hand")
    return out


# --- the entries -----------------------------------------------------------
class Entry:
    """one table slot: (table, mod index, field)"""

    def __init__(self, table, idx, field, slot, kind, context, us):
        self.table, self.idx, self.field, self.slot = table, idx, field, slot
        self.kind, self.context, self.us = kind, context, us  # us: bytes, no terminator
        self.rt = None  # the retranslation's text (or the Saturn name)
        self.source = None  # "rt", "saturn", "keep", "none"
        self.new = None  # final bytes, no terminator
        self.action = None  # "rt", "us (fallback)", "override", ...
        self.measure = None
        self.limit = None
        self.note = ""
        self.consumable = False

    def key(self):
        return "%s\t%d\t%s" % (self.table, self.idx, self.field)

    def term(self):
        return b"\xff\x00" if self.kind == "s" else b"\x00"


def s_text(ram, addr):
    out = b""
    while True:
        b = ram.read(addr + len(out), 2)
        if b == b"\xff\x00":
            return out
        out += b[:1]


def c_text(ram, addr):
    out = b""
    while True:
        b = ram.read(addr + len(out), 1)
        if b == b"\x00":
            return out
        out += b


def us_entries(ram, syms):
    """every string slot the pack may rewrite, with the built DRA's text"""
    out = []

    def add(table, sym, n, stride, fields):
        for i in range(n):
            for fo, field, kind, ctx in fields:
                slot = syms[sym] + i * stride + fo
                p = ram.u32(slot)
                us = s_text(ram, p) if kind == "s" else c_text(ram, p)
                out.append(Entry(table, i, field, slot, kind, ctx, us))

    add("equip", "g_EquipDefs", 228, 0x34, [(0, "name", "s", "item_name"), (4, "desc", "c", "desc")])
    add("acc", "g_AccessoryDefs", 93, 0x20, [(0, "name", "s", "item_name"), (4, "desc", "c", "desc")])
    add("relic", "g_RelicDefs", 32, 0x10, [(0, "name", "c", "relic_name"), (4, "desc", "c", "desc")])
    # (the combos stay as they are: the same inputs; they are entries so
    # the strings they share with others move with them)
    add("spell", "g_SpellDefs", 28, 0x1C, [(0, "name", "c", "spell_name"), (4, "combo", "s", "combo"),
                                          (8, "desc", "c", "desc")])
    add("enemy", "g_EnemyDefs", 426, 0x28, [(0, "name", "s", "enemy_name")])
    for e in out:
        if e.table == "equip":
            e.consumable = ram.read(e.slot - (e.slot - syms["g_EquipDefs"]) % 0x34 + 0x19, 1) != b"\0"
    add("menu", "g_MenuStr", 110, 4, [(0, "str", "s", "menu")])
    add("help", "D_800A2D48", 7, 4, [(0, "str", "c", "desc")])
    return out


def equip_jp(mod_idx):
    """the Japanese (= retail) index of a mod equipment record, or None"""
    if mod_idx < 169:
        return mod_idx
    if 176 <= mod_idx < 224:
        return mod_idx - 7
    return None


def build(ram, syms, report=None):
    """the retranslation strings for this build's DRA: (entries, saves,
    notes) or None without inputs. entries: every Entry (new = the bytes
    the pack writes); saves: [(addr, room, us bytes, new bytes or None, ...)]"""
    ok, msg = inputs_state()
    if not ok:
        return None
    jp = Jp(open(JP_DRA, "rb").read())
    us_retail = open(US_DRA, "rb").read()
    notes = [msg] + alignment_proof(jp.d, us_retail)
    ents = us_entries(ram, syms)
    by = {(e.table, e.idx, e.field): e for e in ents}

    # the mod's records for retail entries hold the retail strings
    def us_name(off):
        p = struct.unpack_from("<I", us_retail, off)[0] - DRA_BASE
        e = p
        while us_retail[e:e + 2] != b"\xff\x00":
            e += 1
        return us_retail[p:e]
    for i in range(217):
        m = i if i < 169 else i + 7
        assert by[("equip", m, "name")].us == us_name(US_EQUIP + i * 0x34), ("equipment", i, m)
    for i in range(90):
        assert by[("acc", i, "name")].us == us_name(US_ACC + i * 0x20), ("accessory", i)
    for i in range(400):
        assert by[("enemy", i, "name")].us == us_name(US_ENEMY + i * 0x28), ("enemy", i)
    notes.append("mod tables: retail equipment 0-168 = mod 0-168, 169-216 = mod 176-223; "
                 "accessories, enemies, relics, spells, g_MenuStr 0-84: same index (names checked)")

    # the patch's text per mod entry
    lists = {k: jp.enc12(jp.u32(JP_HELP + 4 * k)).split("\n") for k in (7, 8)}
    for e in ents:
        t, i, f = e.table, e.idx, e.field
        rt = None
        if t == "equip":
            j = equip_jp(i)
            if j is not None:
                rt = (jp.enc8 if f == "name" else jp.enc12)(jp.u32(JP_EQUIP[0] + j * 0x34 + (0 if f == "name" else 4)))
        elif t == "acc" and i < 90:
            rt = (jp.enc8 if f == "name" else jp.enc12)(jp.u32(JP_ACC[0] + i * 0x20 + (0 if f == "name" else 4)))
        elif t == "relic" and i < 30:
            rt = jp.enc12(jp.u32(JP_RELIC[0] + i * 0x10 + (0 if f == "name" else 4)))
        elif t == "spell" and f == "combo":
            rt = None
        elif t == "spell":
            rt = jp.enc12(jp.u32(JP_SPELL[0] + i * 0x1C + (0 if f == "name" else 8)))
        elif t == "enemy" and i < 400:
            rt = jp.enc8(jp.u32(JP_ENEMY[0] + i * 0x28))
        elif t == "menu":
            if i in MENU_KEEP:
                rt = None
            elif i < 85:
                rt = jp.enc8(jp.u32(JP_MENU[0] + 4 * i))
            elif MENU_US_ONLY.get(i):
                k, line = MENU_US_ONLY[i]
                rt = lists[k][line]
        elif t == "help":
            rt = jp.enc12(jp.u32(JP_HELP + 4 * i))
        sat = i in SATURN.get(t, ()) and f == "name"
        if sat:
            e.rt = title_case(from_s(e.us) if e.kind == "s" else e.us.decode())
            e.source = "saturn"
        elif i in SATURN.get(t, ()) or (t == "menu" and i in MENU_KEEP) or (t == "menu" and i >= 85 and not MENU_US_ONLY.get(i)):
            e.source = "keep"
        elif rt is None:
            e.source = "keep"
        else:
            e.rt, e.source = rt, "rt"
        if t == "menu" and i in MENU_CANDIDATES:
            k, line = MENU_CANDIDATES[i]
            e.note = "candidate: list %d line %d %r" % (k, line, lists[k][line])
    # the US relic names' leading spaces (alternate rows) and the right-
    # aligned equip slot labels stay as the US has them
    for e in ents:
        if e.source != "rt":
            continue
        if e.table == "relic" and e.field == "name":
            lead = len(e.us) - len(e.us.lstrip(b" "))
            e.rt = " " * lead + e.rt.strip()
        if e.table == "menu" and 85 <= e.idx <= 91:
            e.rt = e.rt.strip().rjust(len(e.us))
        # a mod fix on an empty retail record (none today) stays
        if e.rt == "" and e.us:
            e.note = "the patch has no text here; the mod's text stays"
            e.source = "keep"
    overrides = read_overrides()
    for e in ents:
        decide(e, overrides)
    saves = save_messages(ram, syms, jp)
    return ents, saves, notes


def measure(e, data):
    """(value, limit) for the context, or (None, None)"""
    unit, lim, _ = LIMITS[e.context]
    if e.context == "menu":
        lim = MENU_LIMIT.get(e.idx)
        return (len(data), lim) if lim else (len(data), None)
    if e.context == "item_name" and e.consumable:
        return len(data), 14
    if unit == "chars":
        return len(data), lim
    w = line_width(data)
    if e.context == "spell_name" and len(data) > 31:
        return 999, lim
    return w, lim


def encode(e, text):
    return to_s(text) if e.kind == "s" else to_bios(text)


def decide(e, overrides):
    """e.new / e.action from the text, the limit and the overrides"""
    if e.source == "keep":
        e.new, e.action = e.us, "keep"
        e.measure, e.limit = measure(e, e.us)
        return
    data = encode(e, e.rt)
    e.measure, e.limit = measure(e, data)
    over = e.limit is not None and (e.measure is None or e.measure > e.limit)
    ov = overrides.get(e.key())
    if ov:
        act, text = ov
        if act == "text":
            e.new, e.action = encode(e, text), "override text"
            e.measure, e.limit = measure(e, e.new)
            return
        if act == "us":
            e.new, e.action = e.us, "override: US text"
            return
        if act == "rt":
            e.new, e.action = data, "override: retranslation as is"
            return
    if over and e.context in ("item_name", "relic_name", "spell_name", "desc", "menu"):
        # provisional: the US text (the room is shared with other drawing,
        # or the renderer cuts the line)
        e.new, e.action = e.us, "us (does not fit)"
    else:
        e.new = data
        e.action = "rt" if not over else "rt (overflows: %s)" % e.context
    if e.source == "saturn":
        e.action = "saturn title case"


def read_overrides():
    """table<TAB>index<TAB>field<TAB>action[<TAB>text]; action: rt, us, text"""
    out = {}
    if not os.path.exists(OVERRIDES):
        return out
    for n, line in enumerate(open(OVERRIDES, encoding="utf-8"), 1):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        p = line.split("\t")
        if len(p) < 4 or p[3] not in ("rt", "us", "text") or (p[3] == "text") != (len(p) >= 5):
            sys.exit("text_rt: %s line %d: table<TAB>index<TAB>field<TAB>rt|us|text[<TAB>text]"
                     % (OVERRIDES, n))
        out["%s\t%d\t%s" % (p[0], int(p[1], 0), p[2])] = (p[3], p[4] if len(p) >= 5 else None)
    return out


def save_messages(ram, syms, jp):
    """[(addr, room, us, new or None, rt text, width, box, why)]: the save
    messages, rewritten in place where the new text fits the literal"""
    msgs = [jp.enc12(jp.u32(JP_SAVEMSG[0] + 4 * k)) for k in range(JP_SAVEMSG[1])]
    lo, hi = DRA_BASE, syms["dra_BSS_START"]
    img = ram.read(lo, hi - lo)
    refs = code_refs(img)
    out = []
    for us_s, k, box, grp in SAVEMSG:
        us = us_s.encode("latin-1") + b"\0"
        # the literal itself: 4-aligned or preceded by the end of another
        at = [m.start() for m in re.finditer(re.escape(us), img) if not m.start() & 3 or img[m.start() - 1] == 0]
        assert len(at) == 1, ("save message literal", us_s, at)
        a = at[0]
        room = len(us)
        # + the zeros up to the next 4-aligned object
        end = (a + room + 3) & ~3
        if img[a + room:end] == bytes(end - a - room):
            room = end - a
        # the code reads it from its start only
        inside = sorted({t for t in refs if lo + a <= t < lo + a + room})
        assert inside == [lo + a], ("save message literal referenced inside", us_s, [hex(t) for t in inside])
        text = msgs[k]
        body = to_bios(text)
        w = line_width(body)
        if box is None:
            pad = len(us) - len(us.lstrip(b" "))
        else:
            # centred like the US text, with leading spaces (the RT font's
            # space; the BIOS font's is 6 px)
            sp = rt_font()[0][0] if rt_width(body) is not None else 6
            pad = max(0, (box - w) // 2 // sp) if w is not None else 0
        new = b" " * pad + body
        why = ""
        if w is None or (box is not None and w > box):
            why, new = "wider than its box (%s px of %d)" % (w, box), None
        elif len(new) + 1 > room:
            # as centred as the literal's bytes allow
            if len(body) + 1 <= room:
                new = b" " * (room - 1 - len(body)) + body
            else:
                why, new = "%d bytes, the literal has %d" % (len(body) + 1, room), None
        if new is not None:
            new = new + bytes(room - len(new))
        out.append([lo + a, room, us, new, text, w, box, why, grp])
    # a message changes only if all its lines do
    bad = {r[8] for r in out if r[3] is None}
    bad |= {g for g, w in SAVEMSG_WITH.items() if w in bad}
    for r in out:
        if r[3] is not None and (r[8] in bad or any(SAVEMSG_WITH.get(g) == r[8] and g in bad for g in SAVEMSG_WITH)
                                 and all(SAVEMSG_WITH.get(g) != r[8] or g in bad for g in SAVEMSG_WITH)):
            r[3], r[7] = None, "another line of the message does not fit"
    return out


def code_refs(img):
    """the addresses lui + addiu / load / store pairs in img (DRA from
    DRA_BASE) resolve to"""
    n = len(img) // 4
    w = struct.unpack("<%dI" % n, img[:n * 4])
    out = []
    for i, v in enumerate(w):
        if v >> 26 != 0xF:
            continue
        rt, top = (v >> 16) & 31, (v & 0xFFFF) << 16
        for k in range(i + 1, min(i + 12, n)):
            x = w[k]
            op, rs = x >> 26, (x >> 21) & 31
            if rs == rt and op in (0x09, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B):
                out.append((top + (x & 0xFFFF) - ((x & 0x8000) << 1)) & 0xFFFFFFFF)
            dst = (x >> 11) & 31 if op == 0 else (x >> 16) & 31 if 0x08 <= op <= 0x26 else -1
            if dst == rt:
                break
    return out


def summary(res):
    ents, saves, notes = res
    from collections import Counter
    c = Counter((e.table, e.field, e.action.split(" (")[0] if e.action else "?") for e in ents)
    return c


def main():
    import text_packs as tp
    syms = tp.dra_symbols()
    dra = tp.dra_image(os.path.join(tp.BUILD, "DRA.BIN"), syms)
    ram = tp.Ram(dra, syms["g_ModDub"])
    res = build(ram, syms)
    if res is None:
        print("text_rt: " + inputs_state()[1])
        return
    ents, saves, notes = res
    for n in notes:
        print("text_rt: " + n)
    c = summary(res)
    for k in sorted(c):
        print("  %-6s %-5s %-24s %d" % (k + (c[k],)))
    print("  save messages: %d in place, %d kept" % (sum(1 for s in saves if s[3]), sum(1 for s in saves if not s[3])))
    if "--report" in sys.argv:
        import text_rt_report
        text_rt_report.write(sys.argv[sys.argv.index("--report") + 1], res)


if __name__ == "__main__":
    main()
