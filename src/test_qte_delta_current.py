"""Run the actual ActorController native entry, reproducing and preventing the new Vegas dump."""
import struct
import unittest
from offline_test_images import image
from patch_qte_delta_current import build
from pe_image_readonly import PE32
from test_pause_ai_adapter import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn import UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.x86_const import *

NATIVE,STACK,DATA,RET=0xB14000,0x33000000,0x32000000,0x34000000


class CurrentDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=image('client','integrated')
        cls.new,cls.report=build(cls.base)

    def run_native(self,bits,patched,solo=0,connection=3):
        p=PE32(self.new if patched else self.base)
        u=Uc(UC_ARCH_X86,UC_MODE_32)
        for address,size in ((NATIVE,0x2000),(STACK,0x10000),(DATA,0x10000),(RET,0x1000),(0x2888000,0x10000),(0x9D5000,0x1000)):
            u.mem_map(address,size)
        u.mem_write(NATIVE,p.read(NATIVE,0x2000))
        if patched:
            adapter=self.report['adapter'];counter=self.report['counter']
            u.mem_map(adapter&~0xFFF,0x2000)
            u.mem_write(adapter,p.read(adapter,self.report['adapterSize']))
        u.mem_write(0x2888F7C,struct.pack('<I',DATA))
        u.mem_write(DATA+8,bytes([solo]));u.mem_write(DATA+0xA4,struct.pack('<I',connection))
        esp=STACK+0x8000
        u.mem_write(esp,struct.pack('<4I',RET,DATA+0x2000,bits,0))
        u.reg_write(UC_X86_REG_ESP,esp);u.reg_write(UC_X86_REG_ECX,DATA+0x1000)
        u.reg_write(UC_X86_REG_EBX,0x123);u.reg_write(UC_X86_REG_EDI,0x456)
        reached=[]
        def hook(uc,addr,size,user):
            if addr==0xB14A81:
                reached.append('native_forward');uc.emu_stop()
            elif addr==0x9D54F0:
                sp=uc.reg_read(UC_X86_REG_ESP)
                back=struct.unpack('<I',uc.mem_read(sp,4))[0]
                uc.reg_write(UC_X86_REG_EAX,1)
                uc.reg_write(UC_X86_REG_ESP,sp+4);uc.reg_write(UC_X86_REG_EIP,back)
        def trap(uc,number,user):
            reached.append(('native_assert',number));uc.emu_stop()
        u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_INTR,trap)
        u.emu_start(0xB14910,0,count=1000)
        registers=tuple(u.reg_read(reg) for reg in (UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EFLAGS,UC_X86_REG_XMM0,UC_X86_REG_XMM1))
        argument=struct.unpack('<I',u.mem_read(esp+8,4))[0]
        counts=struct.unpack('<5I',u.mem_read(self.report['counter'],20)) if patched else None
        return reached,argument,counts,registers

    def test_current_real_crash_argument_reaches_original_assertion(self):
        result=self.run_native(0xBD220457,False)
        self.assertEqual(result[:2],([('native_assert',3)],0xBD220457))

    def test_same_native_entry_with_current_patch_reaches_forward_update(self):
        result=self.run_native(0xBD220457,True)
        self.assertEqual(result[:3],(['native_forward'],0,(1,1,0,0,0xBD220457)))

    def test_positive_and_zero_native_entry_registers_match(self):
        for bits in (0,0x80000000,0x3D088889,0x3F800000):
            with self.subTest(bits=bits):
                old,new=self.run_native(bits,False),self.run_native(bits,True)
                self.assertEqual(old[0],['native_forward'])
                self.assertEqual((old[0],old[1],old[3]),(new[0],new[1],new[3]))

    def test_solo_and_disconnected_retain_native_assertion(self):
        for kwargs in (dict(solo=1),dict(connection=0)):
            with self.subTest(kwargs=kwargs):
                result=self.run_native(0xBD220457,True,**kwargs)
                self.assertEqual(result[0],[('native_assert',3)])
                self.assertEqual(result[2],(1,0,1,0,0))

    def test_strict_base_and_untouched_loading_paths(self):
        for bad in (self.new,self.base[:-1]+bytes([self.base[-1]^1])):
            with self.assertRaises(ValueError):build(bad)
        old,new=PE32(self.base),PE32(self.new)
        for address,size in ((0xE1108E,5),(0x993495,5),(0xB1496A,5),(0xE115E0,0x164),(0xE21C9A,5)):
            self.assertEqual(old.read(address,size),new.read(address,size))


if __name__=='__main__':unittest.main()
