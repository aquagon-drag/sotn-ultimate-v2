#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Saturn port mod: check the literal sector numbers (LBAs) the code keeps
# against the built disc image. lba_us.h is regenerated from the image by
# make disk, but these are plain numbers in the source: src/dra/cd.c's US
# CdFiles and familiar tables, SEL's movie table (src/st/sel/stream_info.c).
# They only stay right while every file before them keeps its place (the
# mod's new files go after the stage directories); a file added or grown
# ahead of them would make the loads read the wrong sectors.
# Usage: check_cd_lba.py [build/sotn.us.bin]
import re
import struct
import sys

from mod_work import read_src

img = sys.argv[1] if len(sys.argv) > 1 else "build/sotn.us.bin"
f = open(img, "rb")


def data(n):
    f.seek(n * 2352 + 24)
    return f.read(2048)


files = {}


def walk(lba, size, path):
    for i in range((size + 2047) // 2048):
        d, p = data(lba + i), 0
        while p < 2048 and d[p]:
            r = d[p:p + d[p]]
            p += d[p]
            elba, esz = struct.unpack_from("<I", r, 2)[0], struct.unpack_from("<I", r, 10)[0]
            name = r[33:33 + r[32]]
            if name in (b"\x00", b"\x01"):
                continue
            name = name.decode().split(";")[0]
            if r[25] & 2:
                walk(elba, esz, path + name + "/")
            else:
                files[path + name] = (elba, esz)


root = data(16)[156:156 + 34]
walk(struct.unpack_from("<I", root, 2)[0], struct.unpack_from("<I", root, 10)[0], "")

src = read_src("src/dra/cd.c")
us = src[src.index("#if defined(VERSION_US)"):src.index("#elif defined(VERSION_HD)")]
CDFILES = {
    "g_LbaBinTitle": "BIN/F_TITLE0.BIN",
    "g_LbaBinProlo": "BIN/F_PROLO0.BIN",
    "g_LbaSdAlkVh": "VAB/SD_ALK.VH",
    "g_LbaSdAlkVb": "VAB/SD_ALK.VB",
    "g_LbaSdRihVh": "VAB/SD_RIH.VH",
    "g_LbaSdRihVb": "VAB/SD_RIH.VB",
    "g_LbaSdMarVh": "VAB/SD_MAR.VH",
    "g_LbaSdMarVb": "VAB/SD_MAR.VB",
    "g_LbaSdJ010_1_Vh": "SD_J010.VH",
    "g_LbaSdJ010_1_Vb": "SD_J010.VB",
    "g_LbaSdJ010_2_Vh": "SD_J010.VH",
    "g_LbaSdJ010_2_Vb": "SD_J010.VB",
    "g_LbaSdJ010_3_Vh": "SD_J010.VH",
    "g_LbaSdJ010_3_Vb": "SD_J010.VB",
    "g_LbaBinWeapon0": "BIN/WEAPON0.BIN",
    "g_LbaBinWeapon1": "BIN/WEAPON1.BIN",
    "g_LbaBinMonster": "BIN/MONSTER.BIN",
    "g_LbaBinDemokey": "BIN/DEMOKEY.BIN",
    "g_LbaBinRichter": "BIN/RIC.BIN",
    "g_LbaBinAlucard": "BIN/ARC_F.BIN",
    "g_LbaOpnWsStr": "OPN_WS.STR",
    "g_LbaBinGo": "BIN/F_GO.BIN",
    "g_LbaBinEnd": "BIN/F_END.BIN",
}
SERVANTS = ["BAT", "GHOST", "FAIRY", "DEVIL", "SWORD", "FAIR2", "DEVI2"]
fails, n = [], 0


def want(what, value, path, field=0):
    global n
    n += 1
    if path not in files:
        fails.append(f"{what}: {path} is not on the disc")
    elif files[path][field] != value:
        fails.append(f"{what} = {value:#x}, {path} {'is at' if field == 0 else 'is'} "
                     f"{files[path][field]:#x}")


for name, path in CDFILES.items():
    m = re.search(r"CdFile %s = \{(0x[0-9A-Fa-f]+)," % name, us)
    if not m:
        fails.append(f"{name}: not found in cd.c")
        continue
    want(name, int(m.group(1), 16), path)


def table(name):
    m = re.search(r"%s\[\] = \{([^}]*)\}" % name, us)
    return [int(x, 0) for x in m.group(1).replace("\n", " ").split(",") if x.strip()]


for i, x in enumerate(table("g_LbaServantChrOff")):
    want(f"g_LbaServantChrOff[{i}]", x, "SERVANT/FT_%03d.BIN" % i)
for i, x in enumerate(table("g_LbaServantVhOff")):
    want(f"g_LbaServantVhOff[{i}]", x, f"SERVANT/SD_{SERVANTS[i]}.VH")
for i, x in enumerate(table("g_LbaServantVhLen")):
    want(f"g_LbaServantVhLen[{i}]", x, f"SERVANT/SD_{SERVANTS[i]}.VH", 1)
for i, x in enumerate(table("g_LbaServantVbOff")):
    want(f"g_LbaServantVbOff[{i}]", x, f"SERVANT/SD_{SERVANTS[i]}.VB")
for i, x in enumerate(table("g_LbaServantVbLen")):
    want(f"g_LbaServantVbLen[{i}]", x, f"SERVANT/SD_{SERVANTS[i]}.VB", 1)

# SEL's movies, in table order
movies = ["LOGO15XA.STR", "OPN_WS.STR", "TYK_WS.STR", "END_WS.STR"]
offs = [int(x, 0) for x in re.findall(r"\.cdOffset = (0x[0-9a-fA-F]+)",
                                      open("src/st/sel/stream_info.c").read())]
if len(offs) != len(movies):
    fails.append(f"stream_info.c: {len(offs)} cdOffsets, expected {len(movies)}")
for i, (x, path) in enumerate(zip(offs, movies)):
    want(f"stream_info.c movie {i}", x, path)

# Runway after every file the game reads through DRA's CdFile_DemoKey path
# (SEL's text chunks, the RT pack's chunks): the drive keeps reading ahead of
# a finished 4-sector read until CdlPause is accepted, and at the lead-out it
# stops for good (the loader then hangs). So at least RUNWAY ordinary data
# sectors (sync, MODE2 form 1) must follow each such file's last sector, and
# nothing but the padding file may sit that close to the end of the image.
RUNWAY = 600
f.seek(0, 2)
total = f.tell() // 2352
n += 1
for path in ("ST/SEL/SEL.BIN", "SD/TXT_RT.BIN"):
    if path not in files:
        fails.append(f"runway: {path} is not on the disc")
        continue
    elba, esz = files[path]
    end = elba + (esz + 2047) // 2048
    # the last 4-sector read may run past the file's end by up to 3 sectors
    end += -(end - files["BIN/DEMOKEY.BIN"][0]) % 4
    if total - end < RUNWAY:
        fails.append(f"runway: only {total - end} sectors follow the last chunk of {path} "
                     f"(read through CdFile_DemoKey), need {RUNWAY}")
        continue
    for s in range(end, end + RUNWAY):
        f.seek(s * 2352)
        h = f.read(24)
        if h[:12] != b"\x00" + b"\xff" * 10 + b"\x00" or h[18] & 0x20 or not h[18] & 0x08:
            fails.append(f"runway: sector {s} after {path} is not a MODE2 form 1 data sector")
            break
last = max(files.items(), key=lambda kv: kv[1][0] + (kv[1][1] + 2047) // 2048)[0]
for path, (elba, esz) in files.items():
    if (elba + (esz + 2047) // 2048 + RUNWAY > total and path != "SD/TXT_PAD.BIN"
            and not path.endswith("TXT_RT.BIN")):
        fails.append(f"runway: {path} ends within {RUNWAY} sectors of the image end")
if last != "SD/TXT_PAD.BIN":
    fails.append(f"runway: the last file on the disc is {last}, expected SD/TXT_PAD.BIN")

if fails:
    for s in fails:
        print("FAIL cd lba:", s)
    sys.exit(1)
print(f"OK   cd lba: {n} literal sectors / lengths in cd.c and SEL match the disc; "
      f"{RUNWAY}+ data sectors follow every CdFile_DemoKey-read file")
