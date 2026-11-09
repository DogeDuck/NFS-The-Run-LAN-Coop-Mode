"""Small checked PE32 reader for diagnostics. No mutation or process APIs."""
import struct

class PE32:
    def __init__(self,data):
        self.data=data
        if len(data)<64 or data[:2]!=b'MZ':raise ValueError('Invalid DOS image')
        pe=self.unpack('<I',60)[0]
        if self.bytes(pe,4)!=b'PE\0\0':raise ValueError('Invalid PE signature')
        machine,count=self.unpack('<HH',pe+4);opt_size=self.unpack('<H',pe+20)[0]
        if machine!=0x14c or not 1<=count<=96 or opt_size<96:raise ValueError('Unsupported PE32 header')
        opt=pe+24;self.bytes(opt,opt_size)
        if self.unpack('<H',opt)[0]!=0x10b:raise ValueError('Expected PE32 optional header')
        self.base=self.unpack('<I',opt+28)[0];self.sections=[]
        table=opt+opt_size;self.bytes(table,count*40)
        for index in range(count):
            off=table+index*40
            virtual_size,rva,raw_size,raw=self.unpack('<4I',off+8)
            flags=self.unpack('<I',off+36)[0]
            if self.base+rva+max(virtual_size,raw_size)>1<<32:raise ValueError('PE virtual range overflow')
            if raw_size:self.bytes(raw,raw_size)
            self.sections.append(dict(name=self.bytes(off,8).rstrip(b'\0').decode('ascii','replace'),
                                      rva=rva,raw=raw,size=raw_size,virtual_size=virtual_size,flags=flags))

    def bytes(self,offset,size):
        if offset<0 or size<0 or offset>len(self.data) or size>len(self.data)-offset:raise ValueError('Truncated PE image')
        return self.data[offset:offset+size]

    def unpack(self,fmt,offset):return struct.unpack(fmt,self.bytes(offset,struct.calcsize(fmt)))

    def offset(self,address,size=1):
        if type(address) is not int or type(size) is not int or size<1:raise ValueError('Invalid PE address request')
        matches=[s for s in self.sections if self.base+s['rva']<=address and address+size<=self.base+s['rva']+s['size']]
        if len(matches)!=1:raise ValueError('Unmapped or ambiguous PE address')
        section=matches[0];return section['raw']+address-self.base-section['rva']

    def read(self,address,size):return self.bytes(self.offset(address,size),size)
