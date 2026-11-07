"""Backend-independent CALL patch lifecycle. No process APIs or automatic deployment.

Backend contract: paused() context must stop target threads and always resume;
replace(address,before,after) must compare, write, read back, restore protection
and flush instruction cache, or roll back before raising. Caller keeps allocated
adapter pages alive until target exit; restoring CALL does not quiesce old frames.
"""
from dataclasses import dataclass
import struct


def call_bytes(site, target):
    return b'\xe8' + struct.pack('<i', target - site - 5)


@dataclass
class CallProbe:
    backend: object
    site: int
    target: int
    adapter: int
    expected_build: str
    installed: bool = False

    def original_bytes(self):
        return call_bytes(self.site, self.target)

    def adapter_bytes(self):
        return call_bytes(self.site, self.adapter)

    def install(self):
        if self.installed:
            raise ValueError('Probe already installed')
        if self.backend.build_hash().upper() != self.expected_build.upper():
            raise ValueError('Unsupported build')
        before = self.original_bytes()
        after = self.adapter_bytes()
        with self.backend.paused():
            if self.backend.read(self.site, len(before)) != before:
                raise ValueError('Original CALL mismatch')
            self.backend.replace(self.site, before, after)
            self.installed = True

    def restore(self):
        if not self.installed:
            return 'not_installed'
        with self.backend.paused():
            original = self.original_bytes()
            ours = self.adapter_bytes()
            current = self.backend.read(self.site, len(original))
            if current == original:
                self.installed = False
                return 'already_original'
            if current != ours:
                # Never overwrite someone else's hook, even during error cleanup.
                return 'ownership_conflict'
            self.backend.replace(self.site, ours, original)
            self.installed = False
            return 'restored'


class PointerProbe(CallProbe):
    """Owned, version-checked vtable slot replacement; native ABI is unchanged."""
    def original_bytes(self):
        return struct.pack('<I', self.target)

    def adapter_bytes(self):
        return struct.pack('<I', self.adapter)
