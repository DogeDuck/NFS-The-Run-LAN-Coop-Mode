"""Bounds-checked offline minidump memory access; absent memory stays absent."""
import struct

class MissingMemory(ValueError):
    pass

class DumpMemory:
    def __init__(self,data):
        self.data=data;self.streams={};self.ranges=[]
        if len(data)<32 or data[:4]!=b'MDMP':raise ValueError('Invalid minidump header')
        count,directory=self.unpack('<II',8)
        if count>128:raise ValueError('Too many minidump streams')
        self.file_bytes(directory,count*12)
        for index in range(count):
            kind,size,rva=self.unpack('<III',directory+index*12)
            if kind==0 and size==0:continue
            self.file_bytes(rva,size)
            if kind in self.streams:raise ValueError('Duplicate minidump stream')
            self.streams[kind]=(rva,size)
        if 5 in self.streams:
            rva,size=self.streams[5]
            if size<4:raise ValueError('Truncated memory-list header')
            count=self.unpack('<I',rva)[0]
            if count>1000000 or 4+count*16>size:raise ValueError('Truncated memory-list descriptors')
            for index in range(count):
                base,length,offset=self.unpack('<QII',rva+4+index*16)
                self.add_range(base,length,offset)
        if 9 in self.streams:
            rva,size=self.streams[9]
            if size<16:raise ValueError('Truncated memory64 header')
            count,offset=self.unpack('<QQ',rva)
            if count>1000000 or 16+count*16>size:raise ValueError('Truncated memory64 descriptors')
            for index in range(count):
                base,length=self.unpack('<QQ',rva+16+index*16)
                self.add_range(base,length,offset);offset+=length
        self.ranges.sort()
        # Mixed MemoryList/Memory64 streams may overlap. Accept identical copies,
        # reject contradictory snapshots instead of silently picking one.
        active=[]
        for item in self.ranges:
            base,length,offset=item
            active=[prior for prior in active if prior[0]+prior[1]>base]
            if len(active)>=256:raise ValueError('Too many overlapping captured ranges')
            for a,n,off in active:
                end=min(a+n,base+length)
                if self.file_bytes(off+base-a,end-base)!=self.file_bytes(offset,end-base):
                    raise ValueError('Conflicting captured memory ranges')
            active.append(item)

    def file_bytes(self,offset,size):
        if offset<0 or size<0 or offset>len(self.data) or size>len(self.data)-offset:
            raise ValueError('Truncated minidump data')
        return self.data[offset:offset+size]

    def unpack(self,fmt,offset):
        return struct.unpack(fmt,self.file_bytes(offset,struct.calcsize(fmt)))

    def add_range(self,base,length,offset):
        if base+length>1<<64:raise ValueError('Virtual memory range overflow')
        self.file_bytes(offset,length)
        if length:self.ranges.append((base,length,offset))

    def read(self,address,size):
        if type(address) is not int or type(size) is not int or address<0 or size<0 or size>1024*1024 or address+size>1<<64:
            raise ValueError('Invalid or oversized memory request')
        cursor=address;end=address+size;chunks=[]
        while cursor<end:
            covering=[r for r in self.ranges if r[0]<=cursor<r[0]+r[1]]
            if not covering:raise MissingMemory('Address not captured: '+hex(cursor))
            base,length,offset=max(covering,key=lambda r:r[0]+r[1])
            stop=min(end,base+length)
            chunks.append(self.file_bytes(offset+cursor-base,stop-cursor));cursor=stop
        return b''.join(chunks)

    def optional(self,address,size):
        try:return self.read(address,size)
        except MissingMemory:return None

    def u32(self,address):return struct.unpack('<I',self.read(address,4))[0]

    def describe(self,address):
        matches=[dict(base=hex(base),size=length,file_offset=offset) for base,length,offset in self.ranges if base<=address<base+length]
        return dict(address=hex(address),captured=bool(matches),captured_ranges=matches,
                    caution='Not captured does not mean unmapped or freed in the crashed process.')
