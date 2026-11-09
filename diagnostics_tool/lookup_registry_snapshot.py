"""Bounded read-only snapshots of the two native ID -> pointer registries.

These addresses/layouts come from440030 and its two confirmed callers. Payload
previews are uninterpreted bytes: do not claim a string/type from a raw pointer.
"""
import struct

REGISTRIES={'lookup_keys':0x27147B0,'parent_keys':0x2714B30}

def read_registry(reader,address,previews=False):
    result=dict(complete=False,entries=[])
    try:
        bounds=reader.read(address,8);begin,end=struct.unpack('<II',bounds)
        if end<begin or (end-begin)%8 or end-begin>2048*8 or (not begin and end):
            raise ValueError('Invalid registry bounds')
        raw=reader.read(begin,end-begin) if end>begin else b''
        previous=-1
        for token,pointer in struct.iter_unpack('<II',raw):
            if token<=previous:raise ValueError('Registry tokens are not strictly ordered')
            previous=token;entry=dict(token=hex(token),pointer=hex(pointer))
            if previews and pointer:
                try:entry['payload_preview_hex']=reader.read(pointer,32).hex()
                except OSError:entry['preview_unavailable']=True
            result['entries'].append(entry)
        if reader.read(address,8)!=bounds or (raw and reader.read(begin,len(raw))!=raw):
            raise ValueError('Registry changed while reading')
        result['complete']=True
    except (OSError,ValueError,struct.error) as exc:
        result['unavailable']=str(exc)
    return result

def snapshot_registries(reader,previews=False):
    return dict(registries={name:read_registry(reader,address,previews) for name,address in REGISTRIES.items()},
                caution='Local native registries only. Preview bytes have no verified text/type interpretation; '
                'initial capture may predate a later missing token.')
