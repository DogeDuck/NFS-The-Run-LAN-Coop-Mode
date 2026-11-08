"""Small, replayable memory snapshot at a stopped native exception.

No complete process dump, process writes, inferred type names or network upload.
All addresses come from the verified bridge path and two native registries.
"""
import struct
from bridge_crash_analysis import analyze_lookup
from lookup_registry_snapshot import snapshot_registries
from minidump_memory import DumpMemory,MissingMemory

MAX_BYTES=128*1024
MAX_READS=1024
WORLD_PART_DATA_VTABLE=0x23E3B98

class CaptureMemory:
    def __init__(self,reader):
        self.reader=reader;self.ranges=[];self.missing=[];self.bytes=0;self.requests=0

    def read(self,address,size,fresh=False):
        if type(address) is not int or type(size) is not int or not 0<=address<1<<32 or not 0<=size<=32768 or address+size>1<<32:
            raise ValueError('Invalid bounded x86 memory request')
        if not size:return b''
        if not fresh:
            for base,data in self.ranges:
                if base<=address and address+size<=base+len(data):return data[address-base:address-base+size]
        if self.requests>=MAX_READS or self.bytes+size>MAX_BYTES:raise ValueError('Exception snapshot budget exhausted')
        self.requests+=1
        try:data=self.reader.read(address,size)
        except OSError as exc:
            self.missing.append(dict(address=address,size=size,error=str(exc)))
            raise MissingMemory(str(exc)) from exc
        if len(data)!=size:raise ValueError('Partial remote memory read')
        self.bytes+=size;self.ranges.append((address,data));return data

    def optional(self,address,size):
        try:return self.read(address,size)
        except MissingMemory:return None

    def u32(self,address):return struct.unpack('<I',self.read(address,4))[0]

    def describe(self,address):
        self.optional(address,16)
        return dict(address=hex(address),captured=any(base<=address<base+len(data) for base,data in self.ranges),
                    caution='Snapshot read availability only; no freed/unmapped-memory inference.')

    def document(self):
        return dict(ranges=[dict(address=base,hex=data.hex()) for base,data in self.ranges],
                    missing=self.missing,bytes=self.bytes,remote_read_requests=self.requests,
                    byte_limit=MAX_BYTES,request_limit=MAX_READS)

def memory_from_document(document):
    ranges=document['ranges']
    if not isinstance(ranges,list) or len(ranges)>MAX_READS:raise ValueError('Too many captured ranges')
    decoded=[];total=0
    for item in ranges:
        address=item['address']
        if type(address) is not int or not 0<=address<1<<32:raise ValueError('Invalid capture address')
        value=item['hex']
        if not isinstance(value,str) or len(value)>MAX_BYTES*2:raise ValueError('Invalid capture bytes')
        data=bytes.fromhex(value);total+=len(data)
        if total>MAX_BYTES or address+len(data)>1<<32:raise ValueError('Capture exceeds x86/byte bounds')
        decoded.append((address,data))
    # A minimal in-memory MemoryList stream lets the existing checked reader
    # validate overlaps/adjacency. No .dmp file is created.
    header=bytearray(32);header[:4]=b'MDMP';struct.pack_into('<II',header,8,1,32)
    descriptors=bytearray(struct.pack('<I',len(decoded)));offset=48+16*len(decoded);payload=bytearray()
    for address,data in decoded:
        descriptors+=struct.pack('<QII',address,len(data),offset+len(payload));payload+=data
    return DumpMemory(bytes(header+struct.pack('<III',5,len(descriptors),44)+descriptors+payload))

def preview(memory,address,limit=64):
    if type(limit) is not int or not 1<=limit<=256:raise ValueError('Invalid preview bound')
    chunks=[];incomplete=False
    for _ in range(16):
        used=sum(map(len,chunks));cursor=address+used
        if used>=limit or cursor>=1<<32:break
        size=min(16,limit-used,4096-(cursor&4095),(1<<32)-cursor)
        chunk=memory.optional(cursor,size)
        if chunk is None:incomplete=True;break
        chunks.append(chunk)
        if b'\0' in chunk:break
    data=b''.join(chunks)
    if not data:return dict(available=False)
    result=dict(available=True,hex=data.hex(),read_incomplete=incomplete,interpretation='unverified payload bytes')
    prefix=data.split(b'\0',1)[0]
    if 0<len(prefix)<len(data) and all(32<=value<127 for value in prefix):
        result['ascii_preview_unverified']=prefix.decode('ascii')
    return result

def world_part_asset(memory,address):
    """Verified WorldPartData getter/factory and Asset-base name initializer.

    The key is an asset INSTANCE, not a TypeInfo/string. Its name is at+C.
    Never infer an asset name from a similarly numbered token on the server.
    """
    header=memory.optional(address,16)
    if header is None:return dict(available=False)
    vtable=struct.unpack_from('<I',header)[0]
    if vtable!=WORLD_PART_DATA_VTABLE:return dict(available=False,vtable=hex(vtable),reason='Different key class')
    name=struct.unpack_from('<I',header,12)[0]
    body=memory.optional(address,0x2C)
    result=dict(available=True,native_class='WorldPartData',name_pointer=hex(name),object_bytes_available=body is not None,
                name=preview(memory,name,256),caution='Native asset instance. This does not prove why its runtime registration is absent.')
    if body is not None:result['object_hex']=body.hex()
    return result

def registered_types(memory,table):
    result=dict(complete=False,entries=[])
    try:
        before=memory.read(table+0x10,20)
        root=struct.unpack_from('<I',before,12)[0]&~1
        count=struct.unpack_from('<I',before,16)[0]
        if count>128:raise ValueError('Registered-type tree exceeds capture bound')
        pending=[root] if root else [];seen=set();raw_nodes=[]
        while pending:
            pointer=pending.pop()
            if not pointer:continue
            if pointer==table+0x14 or pointer in seen or len(seen)>=128:raise ValueError('Invalid registered-type tree')
            seen.add(pointer);data=memory.read(pointer,20);raw_nodes.append((pointer,data))
            left,right,parent,key,value=struct.unpack('<5I',data)
            pending.extend((left,right))
            entry=dict(key_pointer=hex(key),value_pointer=hex(value))
            metadata=memory.optional(value+0x58,32) if value else None
            if metadata is not None:
                entry.update(registration_key_pointer=hex(struct.unpack_from('<I',metadata)[0]),
                             allocator_pointer=hex(struct.unpack_from('<I',metadata,16)[0]),
                             field_70_raw=struct.unpack_from('<I',metadata,24)[0])
            result['entries'].append(entry)
        if len(seen)!=count:raise ValueError('Registered-type count differs from tree')
        # The debug-event backend stops game threads while capturing. Re-reading
        # roots still catches external writers or an incompatible native layout.
        if memory.read(table+0x10,20,fresh=True)!=before:raise ValueError('Tree changed during capture')
        if any(memory.read(pointer,20,fresh=True)!=data for pointer,data in raw_nodes):
            raise ValueError('Tree nodes changed during capture')
        result.update(complete=True,count=count)
    except (MissingMemory,OSError,ValueError,struct.error) as exc:result['unavailable']=str(exc)
    return result

def build_snapshot(reader,registers,event):
    memory=CaptureMemory(reader)
    crash=dict(address=hex(registers['eip']),exception=hex(event['code']),
               exception_parameters=[hex(value) for value in event.get('parameters',[])],
               registers={key:hex(value) for key,value in registers.items()})
    result=dict(schema=1,exception=event,crash=crash,process_writes=False,
                caution='Exception observation, not necessarily fatal. Native exception handlers remain responsible for recovery or failure.')
    from bridge_crash_analysis import lookup_fault_context
    if event['address']!=registers['eip'] or lookup_fault_context(memory,crash) is None:
        result['lookup']=dict(applicable=False,reason='Different exception/context');result['capture']=memory.document();return result
    # Prefetch the relevant caller stack; small overlapping reads are served from
    # this buffer so the exported record remains compact.
    memory.optional(registers['esp'],768)
    result['lookup']=analyze_lookup(memory,crash)
    lookup=result['lookup']
    if lookup.get('missing_lookup_observed'):
        result['registries']=snapshot_registries(memory)
        key=int(lookup['requested_key_raw'],16);result['requested_key_preview']=preview(memory,key)
        result['requested_world_part']=world_part_asset(memory,key)
        result['registered_types']=registered_types(memory,registers['ebx'])
        descriptor=lookup.get('parent_descriptor')
        if descriptor:
            token=descriptor['type_token'];registry=result['registries']['registries']['lookup_keys']
            if registry['complete']:
                matches=[entry for entry in registry['entries'] if entry['token']==token]
                result['type_token_resolution']=dict(token=token,observed=bool(matches),
                    matches_lookup_key=bool(matches and int(matches[0]['pointer'],16)==key))
    result['capture']=memory.document();return result

def replay(document):
    memory=memory_from_document(document['capture'])
    return analyze_lookup(memory,document['crash'])
