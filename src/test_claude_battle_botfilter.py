"""Execute original Claude machine code and the one-instruction follow-up in Unicorn."""
import json
import struct
import unittest
from pathlib import Path
import test_battle_team_lead as fixture
from build_test_package import apply
from pe_image_readonly import PE32
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EFLAGS
import patch_claude_battle_botfilter as a

ROOT=Path(__file__).resolve().parent


class IsolatedClaudeFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.BattleTeamLeadTests.setUpClass()
        cls.helper=fixture.BattleTeamLeadTests('runTest')
        patch=json.loads((ROOT/'outputs/TheRun-Coop-v0.7.2-TEST-CANDIDATE/patches/client.json').read_text())
        cls.original=apply(fixture.IMAGE.read_bytes(),patch)
        cls.patched,_,cls.report=a.build(cls.original)

    def world(self,race,players,bots=(),rival=2,local=0,patched=True):
        u=self.helper.world(race,players,rival_id=rival,local_id=local,bots=bots)
        im=PE32(self.patched if patched else self.original)
        for sec in im.sections:
            if sec['name'] not in ('.btllead','.btlleas','.btlbot','.btlbots'):continue
            address=im.base+sec['rva']
            u.mem_map(address,0x1000)
            u.mem_write(address,im.read(address,sec['size']))
        u.mem_write(0x98C640,im.read(0x98C640,10))
        return u

    def test_original_claude_falsely_leads_when_both_behind_bot_in_vector(self):
        race={0:10.0,1:0.0,2:20.0,3:30.0,4:40.0}
        for local in (0,1):
            for patched,expected in ((False,1),(True,0)):
                u=self.world(race,[0,1,2,3,4],bots=(2,3,4),local=local,patched=patched)
                self.assertEqual(self.helper.call(u)[0],expected)

    def test_faster_other_bot_is_excluded_even_when_rival_not_in_vector(self):
        race={0:10.0,1:0.0,2:20.0,3:99.0}
        self.assertEqual(self.helper.call(self.world(race,[0,1,3],bots=(3,),patched=False))[0],1)
        self.assertEqual(self.helper.call(self.world(race,[0,1,3],bots=(3,)))[0],0)

    def test_real_human_lead_still_shared_in_both_directions(self):
        for front in (0,1):
            for local in (0,1):
                race={0:5.0,1:5.0,2:20.0,3:99.0};race[front]=25.0
                self.assertEqual(self.helper.call(self.world(race,[3,1,2,0],bots=(2,3),local=local)),(1,25.0,20.0))

    def test_three_and_four_humans_any_one_can_lead_bots_never_do(self):
        # Offline only: no extra game windows, noncontiguous player IDs.
        for humans in ((1,5,7),(1,5,7,9)):
            race={rid:5. for rid in humans};race.update({2:20.,3:99.})
            players=[3,*reversed(humans),2]
            for local in humans:
                self.assertEqual(self.helper.call(self.world(race,players,bots=(2,3),local=local))[0],0)
            for front in humans:
                leading={**race,front:25.}
                for local in humans:
                    self.assertEqual(self.helper.call(self.world(leading,players,bots=(2,3),local=local))[0],1)

    def test_human_teammate_and_bot_flags_match_native_bool_semantics(self):
        self.assertEqual(self.helper.call(self.world({0:5.,1:10.},[0,1],rival=1))[0],1)
        u=self.world({0:10.,1:0.,2:20.},[0,1,2],bots=(2,))
        # Unknown nonzero bot byte is never accepted as a human.
        u.mem_write(fixture.HEAP+0x9000+2*0x400+0x260,b'\x02')
        self.assertEqual(self.helper.call(u)[0],0)

    def test_only_six_bytes_change_before_appended_sections(self):
        site=PE32(self.original).offset(self.report['site'])
        differences={i for i,(x,y) in enumerate(zip(self.original,self.patched)) if x!=y and i>=0x1000}
        self.assertTrue(differences)
        self.assertLessEqual(differences,set(range(site,site+6)))
        with self.assertRaises(ValueError):a.build(self.patched)
        self.assertFalse(self.report['gameplay_verified'])

    def test_hook_preserves_flags_and_stack_on_both_paths(self):
        for bot in (0,1):
            u=self.world({0:10.,1:0.,2:20.},[0,1,2],bots=(2,))
            player=fixture.HEAP+0x9000+2*0x400
            u.mem_write(player+0x260,bytes([bot]))
            u.reg_write(UC_X86_REG_EAX,player);u.reg_write(UC_X86_REG_ESP,fixture.STACK+0x8000)
            u.reg_write(UC_X86_REG_EFLAGS,0x246)
            endpoint=self.report['site']+6 if not bot else self.report['loop']
            u.emu_start(self.report['site'],endpoint,count=30)
            self.assertEqual(u.reg_read(UC_X86_REG_ESP),fixture.STACK+0x8000)
            self.assertEqual(u.reg_read(UC_X86_REG_EFLAGS),0x246)
            self.assertEqual(u.reg_read(UC_X86_REG_EAX),player if bot else 2)


if __name__=='__main__':unittest.main()
