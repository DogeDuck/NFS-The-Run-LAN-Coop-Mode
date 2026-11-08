"""Offline evidence for the repeated bridge crash. No process access or patching.

The original allocation CALL adds8 argument bytes, CALL4, PUSH EDI4. At the
fault, native caller locals thus live at captured ESP+16. The lookup output at
locals+1C and the node value at+10 are verified against exact native code.
"""
import argparse
import hashlib
import json
from pathlib import Path
from inspect_cinematic_crash import inspect
from minidump_memory import DumpMemory,MissingMemory
from pe_image_readonly import PE32

CLIENT_HASHES={'2cb4570c34e46cc74ccded44f8f38338c12a0edfbb33a74572b72fc6e11ad249',
               '8140947e9b11cdfa4cac5d3c7f05820a96246f447399ed6adc6187355910d5c6',
               'c9d48e500ef82efc642edf2db848a9072e56fbc114e283173d6e7e58bac634a6',
               # NOGUARD candidate: all native lookup/stack CONTRACT bytes verified.
               '25167583c71ec9ad530a3636e4b3607a4707ef7105a4cd5daabe65ac295f8b9b'}
CONTRACT={
 0x4CD08E:bytes.fromhex('5752ffd05fc20800'),
 0x23E3B98:bytes.fromhex('30022102'),
 0x2210230:bytes.fromhex('b8c857a902c3'),
 0x2214149:bytes.fromhex('8d7e10c7460cd4097602'),
 0x45AD90:bytes.fromhex('83ec10535556578b7c242c'),
 0x45AEB7:bytes.fromhex('8b4c241c8b4424288b138b69108b4c82fc'),
 0x45AEEF:bytes.fromhex('8b4d686a106a24e875210700'),
 0x44CFF0:bytes.fromhex('8b410c83e0fe8d5104578b7c240c8bca7416568b3739700c72078bc88b4004eb028b0085c075ee5e3bca74118b073b410c720a8b44240889085fc208008b44240889105fc20800'),
 0x4CD070:bytes.fromhex('578b7c240c83ff047705bf04000000f64104018b542408740d8b018b4004')}

def verify_client(data):
    digest=hashlib.sha256(data).hexdigest()
    if digest not in CLIENT_HASHES:raise ValueError('Unsupported native code source')
    image=PE32(data)
    for address,expected in CONTRACT.items():
        if image.read(address,len(expected))!=expected:raise ValueError('Native lookup/stack contract differs')
    return digest

def lookup_fault_context(memory, crash):
    if crash.get('exception') != '0xc0000005':
        return None
    if crash.get('address') == '0x4cd08b':
        return crash
    # An invalid indirect allocation target can fault AFTER CALL EAX. Only
    # normalize this verified native frame, not arbitrary execute violations.
    if crash.get('exception_parameters', [])[:1] != ['0x8']:
        return None
    registers = crash.get('registers', {})
    if registers.get('eax') != crash.get('address'):
        return None
    try:
        sp = int(registers['esp'], 16)
        if (memory.u32(sp), memory.u32(sp+4), memory.u32(sp+8), memory.u32(sp+16)) != (0x4CD092, 0x24, 0x10, 0x45AEFB):
            return None
    except (MissingMemory, OSError, ValueError, KeyError):
        return None
    result = dict(crash, address='0x4cd08b', registers=dict(registers, esp=hex(sp+12)))
    result['normalized_indirect_call_frame'] = True
    return result


def analyze_lookup(memory,crash):
    result=dict(applicable=False,missing_lookup_observed=False,
                caution='Dump evidence only. A missing lookup does not identify its key or the first invalid registration. '
                'Do not substitute a global allocator or silently discard the referenced mission object.')
    original_fault = crash.get('address')
    crash = lookup_fault_context(memory, crash)
    if crash is None:
        result['reason']='Different fault site';return result
    if crash.get('normalized_indirect_call_frame'):
        result.update(original_fault=original_fault, normalized_indirect_call_frame=True,
                      stack_adjustment_bytes=12)
    regs={key:int(value,16) for key,value in crash['registers'].items()}
    try:
        sp=regs['esp'];table=regs['ebx'];locals_sp=sp+16
        ret,size,alignment=(memory.u32(sp+i) for i in (4,8,12))
        if (ret,size,alignment)!=(0x45AEFB,0x24,0x10):
            result['reason']='Caller stack does not match verified native allocation';return result
        node=memory.u32(locals_sp+0x1C);owner=regs['ebp'];sentinel=table+0x14
        result.update(applicable=True,table=hex(table),lookup_output=hex(node),end_sentinel=hex(sentinel),
                      requested_key_raw=hex(memory.u32(locals_sp+0x2C)),owner_register=hex(owner),
                      allocation_receiver=hex(regs['ecx']),allocation_bytes=size,allocation_alignment=alignment)
        # The parent's EDI is saved by45AD90. At its confirmed caller45B104 it
        # points to the serialized20-byte descriptor, still inside the stack.
        descriptor=memory.u32(locals_sp)
        raw=memory.optional(descriptor,20) if memory.u32(locals_sp+0x20)==0x45B109 else None
        if raw is not None:
            import struct
            index,unknown,type_token,parent_token=struct.unpack_from('<4I',raw)
            result['parent_descriptor']=dict(address=hex(descriptor),index=index,
                field_4_raw=hex(unknown),type_token=hex(type_token),parent_token=hex(parent_token),flag_byte_raw=raw[16],
                caution='Opaque native tokens; no type/actor name is identified by these numbers.')
        if node!=sentinel:
            result['reason']='Lookup output is not the end sentinel';return result
        sentinel_value=memory.u32(node+0x10)
        receiver=memory.u32(owner+0x68)
        result.update(sentinel_value=hex(sentinel_value),owner_matches_sentinel_value=owner==sentinel_value,
                      receiver_matches_owner_field=receiver==regs['ecx'],
                      receiver_capture=memory.describe(receiver),vtable_register=hex(regs['eax']))
        result['missing_lookup_observed']=(owner==sentinel_value and receiver==regs['ecx'])
        if result['missing_lookup_observed']:
            result['reason']='Native end sentinel was consumed as a normal node value before allocation'
    except MissingMemory as exc:result['reason']='Required dump memory not captured: '+str(exc)
    return result

def analyze(path,client_hash):
    crash=inspect(path);result=analyze_lookup(DumpMemory(path.read_bytes()),crash)
    result.update(file=path.name,native_contract_source_sha256=client_hash,
                  dump_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),fault=crash['fault_module'])
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dumps',nargs='+',type=Path);parser.add_argument('--client',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    digest=verify_client(args.client.read_bytes());reports=[analyze(path,digest) for path in args.dumps]
    # The disk hash verifies the disassembly source, not every byte of a dump's
    # runtime image. Keep that distinction in exported evidence.
    document=dict(reports=reports,caution='Exact current disk code validates the interpretation; it does not prove identical runtime images across older dumps.')
    with args.output.open('x',encoding='utf-8') as out:json.dump(document,out,indent=2)
    print(json.dumps(document,indent=2))

if __name__=='__main__':main()
