import sys,subprocess,time; sys.path.insert(0,'/home/claude/ds')
from gdbc import *
def regs(g):
    r=g.cmd('g'); out=[]
    for i in range(0,len(r),8):
        try: out.append(struct.unpack('<I',bytes.fromhex(r[i:i+8]))[0])
        except ValueError: out.append(None)
    return out
g=G(); print('attach',g.cmd('?'))
for spec in sys.argv[2:]:
    print('set',spec,g.cmd(spec))
g.send('c')
subprocess.Popen(['/home/claude/ds/k.sh','x','0.15','0'])
end=time.time()+float(sys.argv[1]); n=0
while time.time()<end and n<60:
    p=g.recv(1.0)
    if p is None: continue
    r=regs(g); n+=1
    loc=g.mem(0x80137F58,0x28)
    print('%-28s pc=%08X ra=%08X v0=%08X a0=%08X a1=%08X step=%d cbready=%08X blk=%s'%(p,r[37],r[31],r[2],r[4],r[5],g.r32(0x8006C398),g.r32(0x80032AA8),loc.hex(' ',4)))
    g.send('c')
