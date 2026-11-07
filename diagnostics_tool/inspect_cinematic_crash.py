"""Read local Windows game minidumps without modifying processes or settings."""
from pathlib import Path,PureWindowsPath
import struct, json
from minidump_memory import DumpMemory

def inspect(path):
    data=path.read_bytes();memory=DumpMemory(data);streams=memory.streams
    if 6 not in streams or streams[6][1]<168:raise ValueError('Exception stream missing or truncated')
    def read(addr,size):
        return memory.optional(addr,size) or b''
    def words(addr,n):
        b=read(addr,n*4)
        return [hex(v) for v in struct.unpack('<'+'I'*(len(b)//4),b)]
    e,_=streams[6]
    code=struct.unpack_from('<I',data,e+8)[0]
    address=struct.unpack_from('<Q',data,e+24)[0]
    parameter_count=struct.unpack_from('<I',data,e+32)[0]
    parameters=list(struct.unpack_from('<'+'Q'*min(parameter_count,15),data,e+40))
    contextsize,context=struct.unpack_from('<II',data,e+160)
    if contextsize<200 or context+contextsize>len(data) or not struct.unpack_from('<I',data,context)[0]&0x10000:
        raise ValueError('Only valid x86 exception contexts are supported')
    regs={name:struct.unpack_from('<I',data,context+off)[0] for name,off in [('edi',156),('esi',160),('ebx',164),('edx',168),('ecx',172),('eax',176),('ebp',180),('eip',184),('esp',196)]}
    modules=[]
    if 4 in streams:
        module_rva,module_size=streams[4]
        module_count=struct.unpack_from('<I',data,module_rva)[0]
        if module_count>4096 or module_count*108+4>module_size:raise ValueError('Invalid module list')
        for index in range(module_count):
            base,size,_,stamp,name=struct.unpack_from('<QIIII',data,module_rva+4+index*108)
            length=struct.unpack_from('<I',data,name)[0]
            if length>32768 or name+4+length>len(data) or length%2:raise ValueError('Invalid module name')
            filename=PureWindowsPath(data[name+4:name+4+length].decode('utf-16-le')).name
            modules.append(dict(name=filename,base=base,size=size,timestamp=stamp))
    fault_module=next((dict(name=m['name'],offset=hex(address-m['base']),timestamp=hex(m['timestamp']),image_size=m['size']) for m in modules if m['base']<=address<m['base']+m['size']),None)
    return {'file':path.name,'exception':hex(code),'address':hex(address),'fault_module':fault_module,'exception_parameters':[hex(v) for v in parameters],'registers':{k:hex(v) for k,v in regs.items()},'stack':words(regs['esp'],96),'esiObject':words(regs['esi'],28),'global288ac40':words(0x288ac40,1),'frames':[{'ebp':hex(regs['ebp']),'words':words(regs['ebp'],8)}]}

def compare(first,second):
    a,b=first.get('fault_module'),second.get('fault_module')
    if not a or not b:return dict(comparable=False,reason='Fault module unresolved')
    same_image=(a['name'].casefold(),a['timestamp'],a['image_size'])==(b['name'].casefold(),b['timestamp'],b['image_size'])
    same_site=same_image and a['offset']==b['offset'] and first['exception']==second['exception']
    return dict(comparable=same_image,same_site=same_site,first_module_offset=a['offset'],second_module_offset=b['offset'],
                caution='Module timestamp/size do not prove identical mod hashes; same fault site does not prove the same root cause.')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dumps',nargs='*',type=Path)
    parser.add_argument('--output',type=Path,default=Path(__file__).with_name('outputs')/'cinematic-crash-summary.json')
    parser.add_argument('--compare',action='store_true',help='Compare the module-relative sites of exactly two dumps')
    args=parser.parse_args()
    root=Path.home()/'AppData/Local/CrashDumps'
    paths=args.dumps or [root/name for name in ('Need For Speed The Run.exe.46428.dmp','Need For Speed The Run.exe.34876.dmp','NFSTR_Server.exe.56284.dmp')]
    results=[inspect(path) for path in paths]
    if args.compare and len(results)!=2:parser.error('--compare requires exactly two dumps')
    report=dict(dumps=results,comparison=compare(*results)) if args.compare else results
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
