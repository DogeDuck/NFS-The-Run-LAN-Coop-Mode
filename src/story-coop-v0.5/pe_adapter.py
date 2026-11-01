"""Append separate RX adapter code and RW diagnostics to a known PE32 image."""
import struct

def align(value,boundary):return (value+boundary-1)//boundary*boundary

def append_adapter(base,code_factory,code_name=b'.cooptmr',data_name=b'.cooptmd'):
    data=bytearray(base)
    pe=struct.unpack_from('<I',data,0x3C)[0];opt=pe+24
    count=struct.unpack_from('<H',data,pe+6)[0]
    opt_size=struct.unpack_from('<H',data,pe+20)[0]
    if data[:2]!=b'MZ' or data[pe:pe+4]!=b'PE\0\0' or struct.unpack_from('<H',data,opt)[0]!=0x10B:
        raise ValueError('Expected PE32 image')
    image_base=struct.unpack_from('<I',data,opt+28)[0]
    section_align,file_align=struct.unpack_from('<II',data,opt+32)
    if image_base!=0x400000 or section_align!=0x1000 or file_align not in (0x200,0x1000):raise ValueError('Unsupported PE layout')
    table=opt+opt_size;sections=[]
    for i in range(count):
        vs,rva,size,raw=struct.unpack_from('<4I',data,table+i*40+8)
        sections.append((rva,vs,size,raw))
    headers=table+count*40
    first_raw=min(raw for rva,vs,size,raw in sections if size)
    if headers+80>first_raw or any(data[headers:headers+80]):raise ValueError('No free section-header space')
    code_rva=align(max(rva+max(vs,size) for rva,vs,size,raw in sections),section_align)
    stats_rva=code_rva+section_align
    code=code_factory(image_base+code_rva,image_base+stats_rva)
    if len(code)>=section_align:raise ValueError('Adapter too large')
    code_size=align(len(code),file_align);stats_size=file_align
    raw_code=align(len(data),file_align);raw_stats=raw_code+code_size
    data.extend(b'\0'*(raw_code-len(data)))
    data.extend(code+b'\xcc'*(code_size-len(code)))
    data.extend(b'\0'*stats_size)
    for index,(name,vs,rva,size,raw,flags) in enumerate((
        (code_name,len(code),code_rva,code_size,raw_code,0x60000020),
        (data_name,8,stats_rva,stats_size,raw_stats,0xC0000040))):
        struct.pack_into('<8sIIIIIIHHI',data,headers+40*index,name.ljust(8,b'\0'),vs,rva,size,raw,0,0,0,0,flags)
    struct.pack_into('<H',data,pe+6,count+2)
    struct.pack_into('<I',data,opt+4,struct.unpack_from('<I',data,opt+4)[0]+code_size)
    struct.pack_into('<I',data,opt+8,struct.unpack_from('<I',data,opt+8)[0]+stats_size)
    struct.pack_into('<I',data,opt+56,stats_rva+section_align)
    struct.pack_into('<I',data,opt+64,0)
    return data,dict(adapter=image_base+code_rva,counter=image_base+stats_rva,adapterSize=len(code)),code,sections
