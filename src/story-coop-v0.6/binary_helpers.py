import hashlib,struct
SPECS=((0x99128D,0x802000),(0x9912A4,0x802030))

def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_offset(data, address):
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    assert data[:2] == b'MZ' and data[pe:pe+4] == b'PE\0\0', 'Invalid executable'
    assert struct.unpack_from('<H', data, pe+4)[0] == 0x14C, 'Expected x86 executable'
    base = struct.unpack_from('<I', data, pe+52)[0]
    count = struct.unpack_from('<H', data, pe+6)[0]
    opt_size = struct.unpack_from('<H', data, pe+20)[0]
    for index in range(count):
        section = pe+24+opt_size+40*index
        _, rva, size, raw = struct.unpack_from('<4I', data, section+8)
        if base+rva <= address < base+rva+size:
            return raw+address-base-rva
    raise ValueError('Instruction is outside file-backed sections')


class Code:
    def __init__(self, base):
        self.base, self.data, self.labels, self.fixups = base, bytearray(), {}, []

    def emit(self, value):
        self.data += bytes.fromhex(value)

    def branch(self, opcode, target):
        self.emit(opcode)
        self.fixups.append((len(self.data), target))
        self.data += bytes(4)

    def label(self, name):
        self.labels[name] = self.base + len(self.data)

    def finish(self):
        for offset, target in self.fixups:
            dest = self.labels[target] if isinstance(target, str) else target
            struct.pack_into('<i', self.data, offset, dest - (self.base + offset + 4))
        return bytes(self.data)


def call_bytes(site, target):
    return b'\xe8' + struct.pack('<i', target - site - 5)

