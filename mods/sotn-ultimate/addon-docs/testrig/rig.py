import ctypes as C, struct, os, sys
HERE=os.path.dirname(os.path.abspath(__file__))
LIB=os.path.join(HERE,'..','pcsx_rearmed','pcsx_rearmed_libretro.so')
BTN=dict(X=0,SQ=1,SEL=2,START=3,UP=4,DOWN=5,LEFT=6,RIGHT=7,O=8,TRI=9,L1=10,R1=11,L2=12,R2=13)
class GameInfo(C.Structure): _fields_=[('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]
class Var(C.Structure): _fields_=[('key',C.c_char_p),('value',C.c_char_p)]
ENV=C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p)
VID=C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t)
AUD=C.CFUNCTYPE(None,C.c_int16,C.c_int16)
AUDB=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
POLL=C.CFUNCTYPE(None)
INP=C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint)
class Emu:
    def __init__(self, image, card=None, opts=None, quiet=True):
        self.l=l=C.CDLL(LIB); self.pix=0; self.frame=None; self.fw=self.fh=self.fp=0; self.pad=0; self.opts=opts or {}
        self._sys=os.path.join(HERE,'sys').encode(); self._keep=[]
        def env(cmd,data):
            cmd&=0xFFFF
            if cmd in (9,31):
                C.cast(data,C.POINTER(C.c_char_p))[0]=self._sys; return True
            if cmd==10:
                self.pix=C.cast(data,C.POINTER(C.c_int))[0]; return True
            if cmd==15:
                v=C.cast(data,C.POINTER(Var))[0]
                k=v.key.decode() if v.key else ''
                if k in self.opts:
                    b=C.c_char_p(self.opts[k].encode()); self._keep.append(b)
                    C.cast(data,C.POINTER(Var))[0].value=b; return True
                return False
            if cmd==17:
                C.cast(data,C.POINTER(C.c_bool))[0]=False; return True
            return False
        def vid(data,w,h,pitch):
            if data:
                self.frame=C.string_at(data,pitch*h); self.fw,self.fh,self.fp=w,h,pitch
        def inp(port,dev,idx,id):
            if port==0 and dev==1:
                if id==256: return self.pad
                return (self.pad>>id)&1
            return 0
        self.cb=(ENV(env),VID(vid),AUD(lambda a,b:None),AUDB(lambda d,n:n),POLL(lambda:None),INP(inp))
        l.retro_set_environment(self.cb[0]); l.retro_set_video_refresh(self.cb[1]); l.retro_set_audio_sample(self.cb[2])
        l.retro_set_audio_sample_batch(self.cb[3]); l.retro_set_input_poll(self.cb[4]); l.retro_set_input_state(self.cb[5])
        l.retro_init()
        gi=GameInfo(image.encode(),None,0,None)
        l.retro_load_game.argtypes=[C.POINTER(GameInfo)]; l.retro_load_game.restype=C.c_bool
        assert l.retro_load_game(C.byref(gi))
        l.retro_get_memory_data.restype=C.c_void_p; l.retro_get_memory_size.restype=C.c_size_t
        l.retro_serialize_size.restype=C.c_size_t
        self.ramp=l.retro_get_memory_data(2); self.ramsz=l.retro_get_memory_size(2)
        self.ram=(C.c_ubyte*self.ramsz).from_address(self.ramp)
        if card:
            p=l.retro_get_memory_data(0); n=l.retro_get_memory_size(0)
            d=open(card,'rb').read()
            if p and n>=len(d): C.memmove(p,d,len(d))
            else: print('no card mem',p,n)
        self.wlog=(C.c_uint*6*4096).in_dll(l,'dbg_watch_log'); self.wn=C.c_uint.in_dll(l,'dbg_watch_n')
        self.wlo=C.c_uint.in_dll(l,'dbg_watch_lo'); self.whi=C.c_uint.in_dll(l,'dbg_watch_hi')
        self.cdlog=(C.c_uint*8*8192).in_dll(l,'dbg_cd_log'); self.cdn=C.c_uint.in_dll(l,'dbg_cd_n'); self.dfr=C.c_uint.in_dll(l,'dbg_frame')
        self.cdseen=0; self.wseen=0
    def run(self,n=1,*btns):
        self.pad=0
        for b in btns: self.pad|=1<<BTN[b]
        for _ in range(n):
            self.dfr.value+=1; self.l.retro_run()
        self.pad=0
    def tap(self,b,hold=3,wait=10):
        self.run(hold,b); self.run(wait)
    def r8(self,a): return self.ram[a&0x1FFFFF]
    def r16(self,a): a&=0x1FFFFF; return self.ram[a]|self.ram[a+1]<<8
    def r32(self,a): a&=0x1FFFFF; return struct.unpack('<I',bytes(self.ram[a:a+4]))[0]
    def rb(self,a,n): a&=0x1FFFFF; return bytes(self.ram[a:a+n])
    def w8(self,a,v): self.ram[a&0x1FFFFF]=v&255
    def w32(self,a,v):
        a&=0x1FFFFF
        for i,b in enumerate(struct.pack('<I',v&0xFFFFFFFF)): self.ram[a+i]=b
    def watch(self,lo,hi): self.wlo.value=lo&0x1FFFFF; self.whi.value=hi&0x1FFFFF
    def watch_new(self):
        out=[]
        while self.wseen<self.wn.value:
            e=self.wlog[self.wseen&4095]; out.append(tuple(e)); self.wseen+=1
        return out
    def cd_new(self):
        out=[]
        while self.cdseen<self.cdn.value:
            e=self.cdlog[self.cdseen&8191]; out.append(tuple(e)); self.cdseen+=1
        return out
    def save(self,name):
        n=self.l.retro_serialize_size(); b=C.create_string_buffer(n)
        self.l.retro_serialize.argtypes=[C.c_void_p,C.c_size_t]; self.l.retro_serialize.restype=C.c_bool
        assert self.l.retro_serialize(b,n); open(os.path.join(HERE,'states',name),'wb').write(b.raw)
    def load(self,name):
        d=open(os.path.join(HERE,'states',name),'rb').read(); b=C.create_string_buffer(d,len(d))
        self.l.retro_unserialize.argtypes=[C.c_void_p,C.c_size_t]; self.l.retro_unserialize.restype=C.c_bool
        assert self.l.retro_unserialize(b,len(d))
    def shot(self,name):
        from PIL import Image
        if not self.frame: print('no frame'); return
        w,h,p=self.fw,self.fh,self.fp
        if self.pix==1:
            im=Image.frombuffer('RGBA',(w,h),self.frame,'raw','BGRA',p,1).convert('RGB')
        else:
            import numpy as np
            a=np.frombuffer(self.frame,dtype='<u2').reshape(h,p//2)[:,:w]
            if self.pix==2: r=(a>>11)&31; g=(a>>5)&63; b=a&31; rgb=np.dstack([r<<3,g<<2,b<<3])
            else: r=(a>>10)&31; g=(a>>5)&31; b=a&31; rgb=np.dstack([r<<3,g<<3,b<<3])
            im=Image.fromarray(rgb.astype('uint8'))
        fn=os.path.join(HERE,'shots',name+'.png'); im.save(fn); return fn
CDN={1:'Nop',2:'Setloc',3:'Play',6:'ReadN',7:'MotorOn',8:'Stop',9:'Pause',10:'Init',11:'Mute',12:'Demute',13:'Setfilter',14:'Setmode',16:'GetlocL',17:'GetlocP',19:'GetTN',20:'GetTD',21:'SeekL',22:'SeekP',25:'Test',26:'ID',27:'ReadS'}
def cdfmt(e):
    cmd,pc_,par,pc,ra,cyc,fr,busy=e
    ps=' '.join('%02X'%((par>>(8*i))&255) for i in range(min(pc_,4)))
    return 'f%-6d %-9s %-12s pc=%08X ra=%08X busy=%X'%(fr,CDN.get(cmd,hex(cmd)),ps,pc,ra,busy)
