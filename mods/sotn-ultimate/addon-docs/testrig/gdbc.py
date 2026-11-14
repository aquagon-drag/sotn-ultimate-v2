import socket, struct, time, select, sys
class G:
    def __init__(s,port=2345):
        s.s=socket.create_connection(('127.0.0.1',port),timeout=10); s.buf=b''
    def send(s,p):
        d=p.encode(); c=sum(d)&255; s.s.sendall(b'$'+d+b'#'+('%02x'%c).encode())
    def recv(s,timeout=5):
        end=time.time()+timeout
        while True:
            i=s.buf.find(b'$')
            if i>=0:
                j=s.buf.find(b'#',i)
                if j>=0 and len(s.buf)>=j+3:
                    p=s.buf[i+1:j]; s.buf=s.buf[j+3:]; s.s.sendall(b'+'); return p.decode()
            t=end-time.time()
            if t<=0: return None
            r,_,_=select.select([s.s],[],[],t)
            if r:
                d=s.s.recv(65536)
                if not d: return None
                s.buf+=d
    def cmd(s,p,timeout=5): s.send(p); return s.recv(timeout)
    def mem(s,a,n):
        r=s.cmd('m%x,%x'%(a,n)); return bytes.fromhex(r) if r and not r.startswith('E') else None
    def r32(s,a): return struct.unpack('<I',s.mem(a,4))[0]
    def regs(s):
        r=s.cmd('g'); b=bytes.fromhex(r); return struct.unpack('<%dI'%(len(b)//4),b)
