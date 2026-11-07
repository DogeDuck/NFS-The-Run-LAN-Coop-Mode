"""Opt-in client fix: acknowledge a completed native bundle unload, never a timeout.

E5711F calls E55260 after the client load queue is done. Snapshot unload state
before that call; send the original BlueprintBundleClientBundleUnloadedMessage
only after native success, while the original pending state still exists.
The post-send cleanup matches E4CF6F..E4CF83 (level reset, string, message).
LAN only; no server counters, fabricated resource completion or forced results.
"""
import struct
from checkpoint_humans_adapter import Code

SITE, NATIVE = 0xE5711F, 0xE55260
ONLINE = 0x2888F7C
CTOR, COPY_NAME = 0x22D4360, 0x494C00
GET_SENDER, SEND = 0xE93700, 0xEDA970
RESET_PENDING, DESTROY_NAME, DESTROY_MSG = 0xE4C5A0, 0x48C2C0, 0x18507E0
CALLS, UNLOADS, SENT, SKIPPED_CALLBACK, SKIPPED_NETWORK = 0, 4, 8, 12, 16
CODE_SECTION, DATA_SECTION = b'.gasunld', b'.gasust'


def absolute(c, op, address):
    c.emit(op)
    c.data += struct.pack('<I', address)


def make_code(base, stats, tracepoints=None):
    c = Code(base)
    # Locals: -4 level, -8 was_unload, -C saved post-native regs ESP,
    # -10 aligned FXSAVE area, -14 original unload ref. All per-call.
    c.emit('5589e583ec209c60')                      # frame; pushfd; pushad
    c.emit('894dfcc745f800000000')                  # level=ecx; was_unload=0
    absolute(c, 'ff05', stats + CALLS)
    c.emit('83b9fc07000001'); c.branch('0f85', 'call_native')
    c.emit('8b811808000085c0'); c.branch('0f84', 'call_native')
    c.emit('8945ec')
    c.emit('c745f801000000')
    absolute(c, 'ff05', stats + UNLOADS)
    c.label('call_native')
    c.emit('619d')
    c.branch('e8', NATIVE)                         # exactly once, same ECX
    c.emit('9c60')                                 # retain all native outputs
    c.emit('837df800'); c.branch('0f84', 'done')
    c.emit('807c241c00'); c.branch('0f84', 'done')  # saved native AL == 0
    c.emit('8b75fc')                               # esi = level
    c.emit('83befc07000002'); c.branch('0f85', 'already_completed')
    c.emit('8b45ec3b8618080000'); c.branch('0f85', 'already_completed')
    # A callback inside E55260 can already have sent/cleared the unload.
    # Do not send twice or accidentally acknowledge a subsequent bundle.
    absolute(c, 'a1', ONLINE)
    c.emit('85c0'); c.branch('0f84', 'no_network')
    c.emit('80780800'); c.branch('0f85', 'no_network')
    c.emit('83b8a400000003'); c.branch('0f85', 'no_network')
    c.emit('83781c00'); c.branch('0f84', 'no_network')
    c.emit('80be1c08000000'); c.branch('0f84', 'no_network')
    c.emit('83be0408000000'); c.branch('0f84', 'no_network')
    # Additional native message calls must not change E55260's return value,
    # registers, flags, x87/SSE state or caller stack.
    c.emit('8965f481ec1002000083e4f00fae04248965f0fc')
    c.emit('83ec4089e789f9')                       # 64-byte message; edi=msg
    if tracepoints is not None:
        tracepoints['ctor_call'] = c.base + len(c.data)
    c.branch('e8', CTOR)
    c.emit('8b960408000089d031db')                 # edx=name, eax=cursor
    c.label('strlen')
    c.emit('803c1800'); c.branch('0f84', 'copy_name')
    c.emit('43'); c.branch('e9', 'strlen')
    c.label('copy_name')
    c.emit('53528d4f38'); c.branch('e8', COPY_NAME) # (source,len), RET8
    absolute(c, '8b0d', ONLINE)
    c.emit('85c9'); c.branch('0f84', 'destroy')
    c.emit('57'); c.branch('e8', GET_SENDER)        # getter leaves msg arg
    c.emit('85c0'); c.branch('0f84', 'no_sender')
    c.emit('89c1')
    if tracepoints is not None:
        tracepoints['send_call'] = c.base + len(c.data)
    c.branch('e8', SEND)                          # native consumes msg arg
    absolute(c, 'ff05', stats + SENT)
    c.emit('8d8efc070000'); c.branch('e8', RESET_PENDING)
    c.branch('e9', 'destroy')
    c.label('no_sender')
    c.emit('83c404')                              # discard unsent msg arg
    c.label('destroy')
    c.emit('8d4f38'); c.branch('e8', DESTROY_NAME)
    c.emit('89f9'); c.branch('e8', DESTROY_MSG)
    c.emit('8b45f00fae088b65f4')                   # FXRSTOR; saved regs ESP
    c.branch('e9', 'done')
    c.label('already_completed')
    absolute(c, 'ff05', stats + SKIPPED_CALLBACK)
    c.branch('e9', 'done')
    c.label('no_network')
    absolute(c, 'ff05', stats + SKIPPED_NETWORK)
    c.label('done')
    c.emit('619d89ec5dc3')                         # native outputs; frame; RET
    return c.finish()
