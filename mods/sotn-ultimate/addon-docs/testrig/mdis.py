import sys,struct
from capstone import *
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN)
U="/mnt/user-data/uploads/Castlevania Symphony of the Night (Ultimate v1.4)(JP Script Add-on)/_analysis/step6e_extracted/"
files={'DRA':(U+'DRA.BIN',0x800A0000,0),'SEL':(U+'ST_SEL_SEL.BIN',0x80180000,0),'MAIN':(U+'SLUS_000.67',0x80010000,0x800)}
n,a,b=sys.argv[1],int(sys.argv[2],16),int(sys.argv[3],16)
p,base,off=files[n]; d=open(p,'rb').read()[off:]
for i in md.disasm(d[a-base:b-base],a): print('%08x  %-8s %s'%(i.address,i.mnemonic,i.op_str))
