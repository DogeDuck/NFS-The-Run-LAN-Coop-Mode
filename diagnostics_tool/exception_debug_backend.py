"""Explicit Win64 -> WOW64 exception observation. Importing never attaches.

Official contracts: DebugActiveProcess, DebugSetProcessKillOnExit(FALSE),
WaitForDebugEvent/ContinueDebugEvent, Wow64GetThreadContext (Microsoft Learn).
Debug events suspend the target temporarily. This backend sets no breakpoints,
writes no target memory/context, and never calls TerminateProcess.
"""
import ctypes as c
import os

U32=c.c_uint32
U64=c.c_uint64
DBG_CONTINUE=0x10002
DBG_EXCEPTION_NOT_HANDLED=0x80010001
ACCESS_VIOLATION=0xC0000005

class ExceptionRecord(c.Structure):
    _fields_=[('code',U32),('flags',U32),('record',U64),('address',U64),
              ('count',U32),('alignment',U32),('parameters',U64*15)]

class ExceptionInfo(c.Structure):
    _fields_=[('record',ExceptionRecord),('first_chance',U32)]

class EventUnion(c.Union):
    _fields_=[('exception',ExceptionInfo),('raw',c.c_ubyte*160),('alignment',U64)]

class DebugEvent(c.Structure):
    _fields_=[('kind',U32),('pid',U32),('tid',U32),('data',EventUnion)]

class Wow64Context(c.Structure):
    _fields_=[('flags',U32),('debug',U32*6),('floating',c.c_ubyte*112),
              ('segments',U32*4),('edi',U32),('esi',U32),('ebx',U32),('edx',U32),
              ('ecx',U32),('eax',U32),('ebp',U32),('eip',U32),('cs',U32),
              ('eflags',U32),('esp',U32),('ss',U32),('extended',c.c_ubyte*512)]

def check_layouts():
    if (c.sizeof(ExceptionRecord),c.sizeof(ExceptionInfo),c.sizeof(DebugEvent),DebugEvent.data.offset)!=(152,160,176,16):
        raise ValueError('Unexpected Win64 debugger structure alignment')
    if c.sizeof(Wow64Context)!=716 or Wow64Context.eip.offset!=184 or Wow64Context.esp.offset!=196:
        raise ValueError('Unexpected WOW64 register layout')

class WindowsExceptionDebugger:
    def __init__(self,pid):
        check_layouts()
        if os.name!='nt' or c.sizeof(c.c_void_p)!=8:raise ValueError('64-bit Windows Python required')
        if type(pid) is not int or pid<=0:raise ValueError('Positive process ID required')
        self.pid=pid;self.attached=False;self.pending=None;self.process_handle=None;self.threads={};self.initial_breakpoint_pending=True
        self.k=c.WinDLL('kernel32',use_last_error=True)
        specs={
            'DebugActiveProcess':([U32],c.c_int),
            'DebugActiveProcessStop':([U32],c.c_int),
            'DebugSetProcessKillOnExit':([c.c_int],c.c_int),
            'WaitForDebugEvent':([c.POINTER(DebugEvent),U32],c.c_int),
            'ContinueDebugEvent':([U32,U32,U32],c.c_int),
            'OpenThread':([U32,c.c_int,U32],c.c_void_p),
            'Wow64GetThreadContext':([c.c_void_p,c.POINTER(Wow64Context)],c.c_int),
            'CloseHandle':([c.c_void_p],c.c_int),
            'GetProcessId':([c.c_void_p],U32),
            'GetThreadId':([c.c_void_p],U32),
        }
        for name,(args,result) in specs.items():
            function=getattr(self.k,name);function.argtypes=args;function.restype=result

    def attach(self):
        if self.attached:raise ValueError('Already attached')
        if not self.k.DebugActiveProcess(self.pid):raise c.WinError(c.get_last_error())
        self.attached=True
        if not self.k.DebugSetProcessKillOnExit(False):
            error=c.WinError(c.get_last_error())
            self.detach()
            raise error

    def wait(self,milliseconds=100):
        if not self.attached or self.pending is not None:raise ValueError('Debugger not ready for another event')
        event=DebugEvent()
        if not self.k.WaitForDebugEvent(c.byref(event),milliseconds):
            error=c.get_last_error()
            if error==121:return None
            raise c.WinError(error)
        record=dict(kind=int(event.kind),pid=int(event.pid),tid=int(event.tid),continue_status=DBG_CONTINUE)
        self.pending=record
        # Close only file handles here. Process/thread debug handles are closed
        # automatically on their exit events; retain them until then or detach.
        raw=bytes(event.data.raw)
        if event.kind in (3,6):
            file_handle=int.from_bytes(raw[:8],'little')
            if file_handle:self.k.CloseHandle(file_handle)
        if event.kind==3:
            self.process_handle=int.from_bytes(raw[8:16],'little')
            self.threads[int(event.tid)]=int.from_bytes(raw[16:24],'little')
        elif event.kind==2:self.threads[int(event.tid)]=int.from_bytes(raw[:8],'little')
        elif event.kind==1:
            info=event.data.exception;exception=info.record
            record.update(code=int(exception.code),address=int(exception.address),first_chance=bool(info.first_chance),
                          parameters=[int(value) for value in exception.parameters[:min(exception.count,15)]])
            # Only the first exception can be the attach handshake. Never later
            # acknowledge a game's own breakpoint because its code was unseen.
            attach_breakpoint=(self.initial_breakpoint_pending and bool(info.first_chance)
                               and exception.code in (0x80000003,0x4000001F))
            self.initial_breakpoint_pending=False
            if attach_breakpoint:
                record['attach_breakpoint']=True
            else:record['continue_status']=DBG_EXCEPTION_NOT_HANDLED
        if event.pid!=self.pid:
            raise ValueError('Unexpected process in debug session')
        return record

    def context(self,tid):
        if self.pending is None or self.pending['tid']!=tid:raise ValueError('Thread is not stopped at the pending event')
        handle=self.k.OpenThread(0x8,False,tid)
        if not handle:raise c.WinError(c.get_last_error())
        try:
            context=Wow64Context();context.flags=0x10007
            if not self.k.Wow64GetThreadContext(handle,c.byref(context)):raise c.WinError(c.get_last_error())
            return {name:int(getattr(context,name)) for name in ('edi','esi','ebx','edx','ecx','eax','ebp','eip','esp','eflags')}
        finally:self.k.CloseHandle(handle)

    def continue_event(self):
        if self.pending is None:return
        event=self.pending
        if not self.k.ContinueDebugEvent(event['pid'],event['tid'],event['continue_status']):
            raise c.WinError(c.get_last_error())
        self.pending=None
        if event['kind']==4:self.threads.pop(event['tid'],None)
        elif event['kind']==5:
            self.threads.clear();self.process_handle=None;self.attached=False

    def detach(self):
        if not self.attached:return
        if self.pending is not None:self.continue_event()
        if not self.attached:return
        if not self.k.DebugActiveProcessStop(self.pid):raise c.WinError(c.get_last_error())
        self.attached=False
        # Only close retained handles still identifying our target/thread. Never
        # close a handle number which the system has recycled for another object.
        if self.process_handle and self.k.GetProcessId(self.process_handle)==self.pid:
            self.k.CloseHandle(self.process_handle)
        self.process_handle=None
        for tid,handle in self.threads.items():
            if handle and self.k.GetThreadId(handle)==tid:self.k.CloseHandle(handle)
        self.threads.clear()
