# asmble ESP32 S2 ULP code
def _parse(s):
    s=s.split()
    return (s[0], ''.join(s[1:]).split(',') if len(s)>1 else ())

_opcodes=(
    (_parse('.long I'),       lambda p:p[0]),
    (_parse('add R,R,R'),     lambda p:7<<28|0<<26|0<<21|p[0]|p[1]<<2|p[2]<<4),
    (_parse('add R,R,I'),     lambda p:7<<28|1<<26|0<<21|p[0]|p[1]<<2|(p[2]&0xffff)<<4),
    (_parse('sub R,R,R'),     lambda p:7<<28|0<<26|1<<21|p[0]|p[1]<<2|p[2]<<4),
    (_parse('sub R,R,I'),     lambda p:7<<28|1<<26|1<<21|p[0]|p[1]<<2|(p[2]&0xffff)<<4),
    (_parse('and R,R,R'),     lambda p:7<<28|0<<26|2<<21|p[0]|p[1]<<2|p[2]<<4),
    (_parse('and R,R,I'),     lambda p:7<<28|1<<26|2<<21|p[0]|p[1]<<2|(p[2]&0xffff)<<4),
    (_parse('or R,R,R'),      lambda p:7<<28|0<<26|3<<21|p[0]|p[1]<<2|p[2]<<4),
    (_parse('or R,R,I'),      lambda p:7<<28|1<<26|3<<21|p[0]|p[1]<<2|(p[2]&0xffff)<<4),
    (_parse('move R,R'),      lambda p:7<<28|0<<26|4<<21|p[0]|p[1]<<2),
    (_parse('move R,I'),      lambda p:7<<28|1<<26|4<<21|p[0]|(p[1]&0xffff)<<4),
    (_parse('lsh R,R,R'),     lambda p:7<<28|0<<26|5<<21|p[0]|p[1]<<2|p[2]<<4),
    (_parse('lsh R,R,I'),     lambda p:7<<28|1<<26|5<<21|p[0]|p[1]<<2|(p[2]&0xffff)<<4),
    (_parse('rsh R,R,R'),     lambda p:7<<28|0<<26|6<<21|p[0]|p[1]<<2|p[2]<<4),
    (_parse('rsh R,R,I'),     lambda p:7<<28|1<<26|6<<21|p[0]|p[1]<<2|(p[2]&0xffff)<<4),
    (_parse('stage_rst'),     lambda p:7<<28|2<<26|2<<21),
    (_parse('stage_inc I'),   lambda p:7<<28|2<<26|0<<21|(p[0]&0xff)<<4),
    (_parse('stage_dec I'),   lambda p:7<<28|2<<26|1<<21|(p[0]&0xff)<<4),
    (_parse('st R,R,I'),      lambda p:6<<28|4<<25|0<<7|0<<6|p[1]<<2|p[0]|(p[2]&0x7ff)<<10|p[1]<<4),
    (_parse('st_low R,R,I'),  lambda p:6<<28|4<<25|3<<7|0<<6|p[1]<<2|p[0]|(p[2]&0x7ff)<<10),
    (_parse('st_high R,R,I'), lambda p:6<<28|4<<25|3<<7|1<<6|p[1]<<2|p[0]|(p[2]&0x7ff)<<10),
    (_parse('st_offset I'),   lambda p:6<<28|3<<25|(p[2]&0x7ff)<<10),
    (_parse('st_data R,R'),   lambda p:6<<28|1<<25|0<<7|p[1]<<2|p[0]|p[1]<<4),
    (_parse('st_half R,R'),   lambda p:6<<28|1<<25|3<<7|p[1]<<2|p[0]),
    (_parse('ld R,R,I'),      lambda p:13<<28|0<<27|p[0]|p[1]<<2|(p[2]&0x7ff)<<10),
    (_parse('ld_low R,R,I'),  lambda p:13<<28|0<<27|p[0]|p[1]<<2|(p[2]&0x7ff)<<10),
    (_parse('ld_high R,R,I'), lambda p:13<<28|1<<27|p[0]|p[1]<<2|(p[2]&0x7ff)<<10),
    (_parse('jump R'),        lambda p:8<<28|1<<26|0<<22|1<<21|p[0]),
    (_parse('jump I'),        lambda p:8<<28|1<<26|0<<22|0<<21|(p[0]&0x7ff)<<2),
    (_parse('jump R,W'),      lambda p:8<<28|1<<26|{'eq':1,'ov':2}[p[1]]<<22|1<<21|p[0]),
    (_parse('jump I,W'),      lambda p:8<<28|1<<26|{'eq':1,'ov':2}[p[1]]<<22|0<<21|(p[0]&0x7ff)<<2),
    (_parse('jumpr I,I,W'),   lambda p:8<<28|0<<26|(p[0]&0x7f if p[0]>=0 else -p[0]&0x7f|0x80)<<18|{'lt':0,'gt':1,'eq':2}[p[2]]<<16|(p[1]&0xffff)),
    (_parse('jumps I,I,W'),   lambda p:8<<28|2<<26|(p[0]&0x7f if p[0]>=0 else -p[0]&0x7f|0x80)<<18|{'lt':0,'gt':1,'eq':2}[p[2]]<<16|(p[1]&0xffff)),
    (_parse('halt'),          lambda p:11<<28),
    (_parse('wake'),          lambda p:9<<28),
    (_parse('wait I'),        lambda p:4<<28|(p[0]&0xffff)),
    (_parse('tsens R,I'),     lambda p:10<<28|p[0]|(p[1]&0x3fff)<<2),
    (_parse('adc R,I,I'),     lambda p:5<<28|p[0]|(p[1]&1)<<6|(p[1]&0x0f)<<2),
    (_parse('reg_rd I,I,I'),  lambda p:2<<28|(p[0]&0x3ff)|(p[1]&0x1f)<<23|(p[2]&0x1f)<<18),
    (_parse('reg_wr I,I,I,I'),lambda p:1<<28|(p[0]&0x3ff)|(p[1]&0x1f)<<23|(p[2]&0x1f)<<18|(p[3]&0xff)<<10),
)

def _mk_param(op, lp, labels):
    ret=[]
    for o,l in zip(op, lp):
        if o=='R':
            if not l.startswith('r'):
                raise ValueError
            t=int(l[1:])
            if not 0<=t<=3:
                raise ValueError
            ret.append(t)
        elif o=='I':
            ret.append(int(eval(l, labels)))
        else:
            ret.append(l)
    return ret

def asm(s):
    lines=s.split('\n')
    labels={'pc':0}
    # pass 1, find labels
    idx=0
    for i, line in enumerate(lines):
        line=line.split('#')[0].strip().lower()
        if (t:=line.find(':'))>0:
            k=line[:t].strip()
            if k in labels:
                raise ValueError('Conflicting name '+k+' @{} {}'.format(1+i, line))
            labels[k]=idx
            line=line[t+1:].strip()
        if line.startswith('.set '):
            t=line[5:].split(',')
            if len(t)>1:
                k=t[0].strip()
                if k in labels:
                    raise ValueError('Conflicting name '+k+' @{} {}'.format(1+i, line))
                labels[k]=int(eval(t[1].strip()))
            line=''
        if line:
            idx+=1
        lines[i]=line
    # pass 2, translate codes
    idx=0
    ret=bytearray()
    for i,line in enumerate(lines):
        if not line:
            continue
        lp=_parse(line)
        for op, func in _opcodes:
            if op[0]==lp[0] and len(op[1])==len(lp[1]):
                try:
                    labels['pc']=idx
                    p=_mk_param(op[1], lp[1], labels)
                except:
                    continue
                ret.extend(func(p).to_bytes(4,'little'))
                break
        else:
            raise ValueError('Bad line @{} {}'.format(1+i, line))
        idx+=1
    return ret

def link(bs):
    # magic (4 bytes), .text offset (2 bytes), .text size (2 bytes), .data size (2 bytes), .bss size (2 bytes)
    return b'\x75\x6C\x70\x00\x0C\x00'+len(bs).to_bytes(2, 'little')+b'\x00\x00\x00\x00'+bs

if __name__=='__main__':
    import sys
    if len(sys.argv)<3:
        print(f'''\
To make ESP32 S2 ULP binary code from ASM code. 
There can only one ASM code per line (labels like 'l123:' can be included).
.data and .bss sections are not supported now. so it's recommended to place the data for exchange at the front of the .text section.
NOTICE, it's direffent from other asemble compiler, labels, address and offsets are all expressed as 32-bit words, not bytes.
    
Usage:
    python {sys.argv[0]} <ASM file name> <binary file name>
Example:
    python {sys.argv[0]} a.s a.bin
''')
        exit(1)

    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        t=f.read()
    b=link(asm(t))
    with open(sys.argv[2], 'wb') as f:
        f.write(b)
