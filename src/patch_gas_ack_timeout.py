"""DRAFT builder: append gas_ack_timeout_adapter to a server image and point VT slot 259528C at it."""
import struct
from pe_adapter import append_adapter
from patch_headless_reset import file_offset, digest
import gas_ack_timeout_adapter as a


def build(base, limit=a.DEFAULT_LIMIT):
    offset = file_offset(base, a.VTABLE_SLOT)
    if struct.unpack_from('<I', base, offset)[0] != a.NATIVE:
        raise ValueError('Server level vtable slot changed')
    layout = {}

    def factory(code, stats):
        layout.update(adapter=code, stats=stats)
        return a.adapter_code(code, stats, limit)

    patched, info, code, _ = append_adapter(base, factory, b'.gasack', b'.gasstat')
    offset = file_offset(patched, a.VTABLE_SLOT)
    struct.pack_into('<I', patched, offset, layout['adapter'])
    return bytes(patched), code, dict(sha256=digest(patched), layout={k: hex(v) for k, v in layout.items()},
                                      vtable_slot=hex(a.VTABLE_SLOT), limit=limit, gameplay_verified=False, draft=True,
                                      stats='FORCED +0, COUNTER +4, LAST_80C +8, CALLS +C',
                                      limitations='Continues the server bundle queue after LIMIT calls without client acks; '
                                                  'clients may lack the bundle. Not tested in game.')
