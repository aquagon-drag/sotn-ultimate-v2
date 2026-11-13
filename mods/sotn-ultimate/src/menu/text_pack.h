// SPDX-License-Identifier: AGPL-3.0-or-later
// SOTN Ultimate: the text pack applier (include/game_mod.h MOD_TEXT_*),
// included by SEL (mods/sotn-ultimate/src/menu/2C048_mod_player_select.h)
// and by the System screen's popup in BIN/ARC_F2.BIN
// (mods/sotn-ultimate/src/menu/sysopt.c). The packs are made, and this code
// is simulated byte for byte, by mods/sotn-ultimate/tools/text_packs.py
// (checked by check_text_packs.py).
//
// A chunk (at most MOD_TEXT_CHUNK_LEN bytes, little endian, 4-aligned):
//   0x00 u32 MOD_TEXT_MAGIC
//   0x04 u16 size: the bytes used, this header included
//   0x06 u16 sum: of the halfwords in [8, size)
//   0x08 u8  this chunk's index; 0x09 u8 the chunks in the stream
//   0x0A u8  packs; 0x0B u8 version (1)
//   0x0C u8  per pack (MOD_TEXT_PACKS): bit c = it has records in chunk c
//   0x10 u16 per pack: the offset of its records in this chunk (0: none)
//   then the records, each 4-aligned:
//   {u16 1, u16 n, u32 dst, n bytes, padding to 4}: copy n bytes to dst
//   {u16 2, u16 n, u32 slots, u32 base, n x {u16 word, u16 off}}: the
//       pointer at slots + 4 * word becomes base + off
//   {u16 0, u16 0}: the end of the pack's records in this chunk
// The PS1 / PSP packs cover every byte and pointer either writes; the RT
// pack covers all those and its own, so applying it gives the same RAM
// whatever was applied before; the restore pack puts the built DRA's values
// back over everything RT writes, so restore + a dub's pack does too. A pack
// spread over several chunks is applied chunk by chunk, in order.
#include <lba.h>
// (the first compile, before make disk has put SD/TXT_RT.BIN in lba_us.h)
#if defined(OFF_SD_TXT_RT) && MOD_TEXT_RT_ON
#define MOD_TEXT_RT_READY 1
#else
#define MOD_TEXT_RT_READY 0
#endif
#ifndef OFF_SD_TXT_RT
#define OFF_SD_TXT_RT 0
#endif

// (STATIC_ASSERT is empty on the PS1 builds: a negative array size fails)
typedef char ModTextLayout[sizeof(ModDubState) == 4096 &&
                                   OFF(ModDubState, textOvfA) ==
                                       MOD_TEXT_OVF_A_OFF &&
                                   OFF(ModDubState, textOvfB) ==
                                       MOD_TEXT_OVF_B_OFF &&
                                   OFF(ModDubState, textOvfC) ==
                                       MOD_TEXT_OVF_C_OFF &&
                                   OFF(ModDubState, textPack) == 1224
                               ? 1
                               : -1];

// the chunk's header and sum are right and it is chunk i (a buffer the CD
// did not fill, or that something else wrote, is not applied)
static s32 ModTextChunkOk(const u8* c, s32 i) {
    const u16* h = (const u16*)c;
    const u16* w;
    u32 sum = 0;
    s32 size = h[2];

    if (*(const u32*)c != MOD_TEXT_MAGIC || c[8] != i ||
        size > MOD_TEXT_CHUNK_LEN || size < 0x18) {
        return 0;
    }
    for (w = h + 4; w < (const u16*)(c + size); w++) {
        sum += *w;
    }
    return (u16)sum == h[3];
}

// applies one pack's records found in this chunk
static void ModTextRun(const u8* c, s32 pack) {
    const u16* r;
    const u8* s;
    u8* d;
    u8* slots;
    u32 base;
    s32 n;

    n = ((const u16*)(c + 0x10))[pack];
    if (!n) {
        return;
    }
    r = (const u16*)(c + n);
    for (;;) {
        n = r[1];
        if (r[0] == 1) {
            d = *(u8**)(r + 2);
            s = (const u8*)(r + 4);
            r = (const u16*)(s + ((n + 3) & ~3));
            while (n--) {
                *d++ = *s++;
            }
        } else if (r[0] == 2) {
            slots = *(u8**)(r + 2);
            base = *(const u32*)(r + 4);
            for (r += 6; n; n--, r += 2) {
                *(u32*)(slots + r[0] * 4) = base + r[1];
            }
        } else {
            break;
        }
    }
}
