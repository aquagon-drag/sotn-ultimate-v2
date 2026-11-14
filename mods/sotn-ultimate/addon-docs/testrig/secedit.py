"""Patch bytes of a file inside a MODE2/2352 image and fix the sector's EDC/ECC (Mode 2 Form 1).
Also emits a .secpatch (u32 LE sector index + 2352 bytes per changed sector)."""
import struct,sys
edc_t=[0]*256; f_lut=[0]*256; b_lut=[0]*256
for i in range(256):
    j=(i<<1)^(0x11D if i&0x80 else 0); f_lut[i]=j; b_lut[i^j]=i
    e=i
    for _ in range(8): e=(e>>1)^(0xD8018001 if e&1 else 0)
    edc_t[i]=e
def edc(data):
    e=0
    for b in data: e=(e>>8)^edc_t[(e^b)&0xFF]
    return e
def ecc_block(sec,major_count,minor_count,major_mult,minor_inc,dest):
    size=major_count*minor_count
    for major in range(major_count):
        idx=(major>>1)*major_mult+(major&1); a=b=0
        for _ in range(minor_count):
            t=sec[12+idx]; idx+=minor_inc
            if idx>=size: idx-=size
            a^=t; b^=t; a=f_lut[a]
        a=b_lut[f_lut[a]^b]
        sec[12+dest+major]=a; sec[12+dest+major+major_count]=a^b
def fix_m2f1(sec):
    sec=bytearray(sec)
    sec[0x818:0x81C]=struct.pack('<I',edc(sec[16:0x818]))
    hdr=bytes(sec[12:16]); sec[12:16]=b'\0\0\0\0'
    ecc_block(sec,86,24,2,86,0x81C-12)
    ecc_block(sec,52,43,86,88,0x8C8-12)
    sec[12:16]=hdr
    return bytes(sec)
def selftest(img,lba):
    with open(img,'rb') as f:
        f.seek(lba*2352); s=f.read(2352)
    return fix_m2f1(s)==s
def patch(img,file_lba,edits,secpatch=None):
    """edits: list of (file_offset, old_bytes, new_bytes)"""
    secs={}
    with open(img,'r+b') as f:
        for off,old,new in edits:
            lba=file_lba+off//2048; o=off%2048
            assert o+len(new)<=2048
            if lba not in secs:
                f.seek(lba*2352); secs[lba]=bytearray(f.read(2352))
            s=secs[lba]
            assert (s[18]&0x20)==0, 'not form 1'
            cur=bytes(s[24+o:24+o+len(old)])
            assert cur==old, 'unexpected bytes at %x: %s'%(off,cur.hex())
            s[24+o:24+o+len(new)]=new
        for lba,s in secs.items():
            s=fix_m2f1(s); secs[lba]=s
            f.seek(lba*2352); f.write(s)
    if secpatch:
        with open(secpatch,'wb') as o:
            for lba in sorted(secs): o.write(struct.pack('<I',lba)+secs[lba])
    return sorted(secs)
