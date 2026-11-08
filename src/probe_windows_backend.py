"""Explicit Windows backend; importing this module never opens a process."""
from contextlib import contextmanager
from pathlib import Path
import ctypes as c
from ctypes import wintypes as w
import hashlib


class UnsafePatchError(RuntimeError):
    pass


class PatchBackend:
    """Injectable API allows real rollback logic to be tested without Windows/game."""
    def __init__(self, api, digest):
        self.api, self.digest = api, digest
        self.suspended = False
        self.unsafe = False

    def build_hash(self):
        return self.digest

    def read(self, address, size):
        return self.api.read(address, size)

    @contextmanager
    def paused(self):
        if self.suspended or self.unsafe:
            raise RuntimeError('Backend already suspended or unsafe')
        self.api.suspend()
        self.suspended = True
        try:
            yield
        finally:
            # If rollback cannot be verified, do not resume into a partial instruction.
            if not self.unsafe:
                self.api.resume()
                self.suspended = False

    def replace(self, address, before, after):
        if not self.suspended or len(before) != len(after):
            raise ValueError('Requires suspended process and equal patch lengths')
        if self.read(address, len(before)) != before:
            raise ValueError('Expected bytes changed')
        old = self.api.protect(address, len(before), 0x40)
        failure = None
        try:
            self.api.write(address, after)
            if self.read(address, len(after)) != after:
                raise OSError('Patch readback mismatch')
            self.api.flush(address, len(after))
        except Exception as exc:
            failure = exc
            try:
                self.api.write(address, before)
                if self.read(address, len(before)) != before:
                    raise OSError('Rollback readback mismatch')
                self.api.flush(address, len(before))
            except Exception as rollback:
                self.unsafe = True
                failure = UnsafePatchError('Rollback failed; target kept suspended: ' + str(rollback))
        try:
            self.api.protect(address, len(before), old)
        except Exception as exc:
            self.unsafe = True
            failure = UnsafePatchError('Protection restore failed; target kept suspended: ' + str(exc))
        if failure:
            raise failure


class WindowsAPI:
    def __init__(self, pid, expected_path):
        self.k = c.WinDLL('kernel32', use_last_error=True)
        self.nt = c.WinDLL('ntdll')
        signatures = {
            'OpenProcess': ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            'CloseHandle': ([w.HANDLE], w.BOOL),
            'QueryFullProcessImageNameW': ([w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)], w.BOOL),
            'ReadProcessMemory': ([w.HANDLE, c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_size_t)], w.BOOL),
            'WriteProcessMemory': ([w.HANDLE, c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_size_t)], w.BOOL),
            'VirtualProtectEx': ([w.HANDLE, c.c_void_p, c.c_size_t, w.DWORD, c.POINTER(w.DWORD)], w.BOOL),
            'VirtualAllocEx': ([w.HANDLE, c.c_void_p, c.c_size_t, w.DWORD, w.DWORD], c.c_void_p),
            'FlushInstructionCache': ([w.HANDLE, c.c_void_p, c.c_size_t], w.BOOL),
            'GetProcessTimes': ([w.HANDLE, c.POINTER(w.FILETIME), c.POINTER(w.FILETIME), c.POINTER(w.FILETIME), c.POINTER(w.FILETIME)], w.BOOL),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.k, name)
            fn.argtypes, fn.restype = args, result
        for name in ('NtSuspendProcess', 'NtResumeProcess'):
            fn = getattr(self.nt, name)
            fn.argtypes, fn.restype = [w.HANDLE], c.c_long
        self.h = self.k.OpenProcess(0xC38, False, pid)
        if not self.h:
            raise c.WinError(c.get_last_error())
        try:
            name, n = c.create_unicode_buffer(32768), w.DWORD(32768)
            if not self.k.QueryFullProcessImageNameW(self.h, 0, name, c.byref(n)):
                raise c.WinError(c.get_last_error())
            if name.value.casefold() != str(expected_path).casefold():
                raise ValueError('Process path mismatch')
            self.path = Path(name.value)
            times = [w.FILETIME() for _ in range(4)]
            if not self.k.GetProcessTimes(self.h, *(c.byref(t) for t in times)):
                raise c.WinError(c.get_last_error())
            self.creation_time = times[0].dwLowDateTime | times[0].dwHighDateTime << 32
        except BaseException:
            self.close()
            raise

    def read(self, address, size):
        b, n = c.create_string_buffer(size), c.c_size_t()
        if not self.k.ReadProcessMemory(self.h, address, b, size, c.byref(n)) or n.value != size:
            raise c.WinError(c.get_last_error())
        return b.raw

    def write(self, address, data):
        n = c.c_size_t()
        if not self.k.WriteProcessMemory(self.h, address, data, len(data), c.byref(n)) or n.value != len(data):
            raise c.WinError(c.get_last_error())

    def protect(self, address, size, flags):
        old = w.DWORD()
        if not self.k.VirtualProtectEx(self.h, address, size, flags, c.byref(old)):
            raise c.WinError(c.get_last_error())
        return old.value

    def flush(self, address, size):
        if not self.k.FlushInstructionCache(self.h, address, size):
            raise c.WinError(c.get_last_error())

    def suspend(self):
        if self.nt.NtSuspendProcess(self.h) != 0:
            raise OSError('Cannot suspend target')

    def resume(self):
        if self.nt.NtResumeProcess(self.h) != 0:
            raise OSError('Cannot resume target')

    def allocate(self, size):
        base = self.k.VirtualAllocEx(self.h, None, size, 0x3000, 4)
        if not base or base + size >= 0x80000000:
            raise OSError('Unsupported low-address allocation')
        return base

    def close(self):
        if self.h:
            self.k.CloseHandle(self.h)
            self.h = None


def open_backend(pid, expected_path, expected_hash):
    api = WindowsAPI(pid, expected_path)
    try:
        digest = hashlib.sha256(api.path.read_bytes()).hexdigest()
        if digest.upper() != expected_hash.upper():
            raise ValueError('Unsupported server hash')
        return PatchBackend(api, digest)
    except BaseException:
        api.close()
        raise
