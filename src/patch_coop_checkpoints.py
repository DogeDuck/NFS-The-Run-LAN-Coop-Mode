"""Reversible, version-locked server checkpoint patch. Default is offline check.

Registers both human racers and publishes the furthest racer's remaining time.
No distributed game binaries. Does not claim to fix intro spawn or story progression.
"""
from pathlib import Path
import argparse
import json
import os
import struct
from checkpoint_humans_adapter import PREDICATE_SITE, CONTINUE_SITE, ORIGINAL_PREDICATE, ORIGINAL_CONTINUE, make_predicate, make_continue
from checkpoint_team_timer_adapter import SITES, ORIGINAL, make_code
from teleport_probe_adapter import SERVER_SHA256
from patch_headless_reset import file_offset, digest, require_game_closed
from pe_adapter import append_adapter

ROOT = Path(__file__).resolve().parent
EXE = Path(r'X:\EA Games\Need for Speed The Run\Need for Speed The Run\NFSTR_Server.exe')
BACKUP = ROOT / 'backups/NFSTR_Server.exe.before-coop-checkpoints'


def specifications():
    return [(PREDICATE_SITE, ORIGINAL_PREDICATE, make_predicate),
            (CONTINUE_SITE, ORIGINAL_CONTINUE, make_continue)] + [
                (site, ORIGINAL, lambda address, site=site: make_code(address, site)) for site in SITES]


def build(base):
    if digest(base).upper() != SERVER_SHA256:
        raise ValueError('Unsupported baseline server')
    specs = specifications()
    for site, original, factory in specs:
        off = file_offset(base, site)
        if base[off:off + len(original)] != original:
            raise ValueError('Native checkpoint code mismatch')

    def combined(address, unused_stats):
        code = bytearray()
        for index, (_, _, factory) in enumerate(specs):
            code += b'\xcc' * (index * 512 - len(code))
            part = factory(address + index * 512)
            if len(part) > 512:
                raise ValueError('Adapter exceeds reserved slot')
            code += part
        return bytes(code)

    patched, layout, code, sections = append_adapter(base, combined, b'.coopchk', b'.coopckd')
    ranges = []
    for index, (site, original, _) in enumerate(specs):
        offset = file_offset(base, site)
        target = layout['adapter'] + index * 512
        patched[offset:offset + len(original)] = b'\xe9' + struct.pack('<i', target - site - 5) + b'\x90' * (len(original) - 5)
        ranges.append((offset, offset + len(original)))
    for _, _, size, raw in sections:
        cursor = raw
        for start, end in sorted((a, b) for a, b in ranges if raw <= a < raw + size):
            if patched[cursor:start] != base[cursor:start]:
                raise ValueError('Unrelated section bytes changed')
            cursor = end
        if patched[cursor:raw + size] != base[cursor:raw + size]:
            raise ValueError('Unrelated section tail changed')
    return bytes(patched), code, dict(base_sha256=digest(base), patched_sha256=digest(patched),
                                    layout=layout, sites=[hex(site) for site, _, _ in specs],
                                    validation='Earlier prototype: HOST checkpoint + both timers observed. New DriverKind0 guard emulated only; updated package needs gameplay test.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--install', action='store_true')
    mode.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    current = EXE.read_bytes()
    base = BACKUP.read_bytes() if BACKUP.exists() else current
    patched, code, report = build(base)
    if current not in (base, patched):
        raise ValueError('Unknown installed server state')
    report['installed'] = current == patched
    if args.install or args.restore:
        require_game_closed()
        if not BACKUP.exists():
            with BACKUP.open('xb') as stream:
                stream.write(base)
        if BACKUP.read_bytes() != base:
            raise ValueError('Backup verification failed')
        replacement = base if args.restore else patched
        if current != replacement:
            temporary = EXE.with_name(EXE.name + '.checkpoint-tmp')
            with temporary.open('xb') as stream:
                stream.write(replacement)
                stream.flush()
                os.fsync(stream.fileno())
            if temporary.read_bytes() != replacement or EXE.read_bytes() != current:
                raise ValueError('Staged executable verification failed')
            os.replace(temporary, EXE)
        report['installed'] = replacement == patched
    (ROOT / 'outputs/coop-checkpoint-adapter.bin').write_bytes(code)
    (ROOT / 'outputs/coop-checkpoint-patch.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
