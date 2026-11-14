"""Real, exact R2 images: native candidates compose without replacing QTE hooks.

Unicorn behavior remains covered by the adapters' own tests. These checks prove
the image-level composition and preservation of the already installed R2 fixes.
They do not emulate rendering, streaming or network delivery.
"""
import hashlib
import unittest
from functools import lru_cache
from pathlib import Path

from offline_test_images import image
from pe_image_readonly import PE32
from patch_qte_spawn_local_bus import build as actor_build
from patch_qte_host_milestones import build as host_build
from patch_team_finish_four import build as team_build, R2 as CLIENT_R2
from patch_gas_entry_guard import build as gas_build, R2 as SERVER_R2
from patch_cutscene_ai import build as scene_build
from patch_qte_delta_current import build as delta_build
from server_ai_reference_guard import build as ai_build
import qte_host_milestones as host
import qte_spawn_local_bus as actor

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def r2_images():
    client, _ = actor_build(image('client', 'integrated'))
    server, _ = host_build((ROOT / 'outputs/offline-3h-20261113/ghidra/NFSTR_Server_BCDAFBF8.exe').read_bytes())
    assert hashlib.sha256(client).hexdigest() == CLIENT_R2
    assert hashlib.sha256(server).hexdigest() == SERVER_R2
    return client, server


class IntegratedNativeTests(unittest.TestCase):
    def test_garage_relay_and_unlock_are_pinned_to_the_actual_cohort(self):
        import re
        from build_integrated_selected_candidate import pin_garage_scripts
        client,server=r2_images()
        core=(ROOT/'package_tools/Garage-Core.ps1').read_text(encoding='utf-8-sig')
        unlock=(ROOT/'package_tools/Unlock-Coop-Garage.ps1').read_text(encoding='utf-8-sig')
        output,worker=pin_garage_scripts(core,unlock,client,server)
        builds=re.search(r"GarageServerBuilds=@\((.*?)\)",output,re.S)[1]
        self.assertEqual(re.findall(r"'[A-F0-9]{64}'",builds),["'"+SERVER_R2.upper()+"'"])
        self.assertIn(CLIENT_R2.upper(),worker)
        self.assertNotIn('C9D48E500EF82EFC642EDF2DB848A9072E56FBC114E283173D6E7E58BAC634A6',worker)
        changed=bytearray(server);at=PE32(server).offset(0x13EAF90);changed[at]^=1
        with self.assertRaises(ValueError):pin_garage_scripts(core,unlock,client,bytes(changed))
    def test_team_and_scene_compose_on_exact_r2_and_preserve_actor_bus(self):
        client, _ = r2_images()
        guarded,delta_report=delta_build(client)
        team, team_report = team_build(guarded)
        result, scene_report = scene_build(team)
        before, after = PE32(client), PE32(result)
        # All previous R2 adapter code/data sections remain byte-identical.
        for section in before.sections:
            if section['name'].startswith('.qte'):
                at = before.base + section['rva']
                self.assertEqual(after.read(at, section['size']), before.read(at, section['size']))
        self.assertEqual(after.read(actor.SLOT, 4), before.read(actor.SLOT, 4))
        self.assertEqual(team_report['humans_max'], 4)
        self.assertTrue(delta_report['negative_finite_delta_clamped'])
        self.assertTrue(scene_report['lan_only'])
        self.assertFalse(scene_report['gameplay_verified'])
        with self.assertRaises(ValueError):
            scene_build(result)

    def test_r2_negative_delta_guard_executes_real_actor_entry(self):
        import test_qte_delta_current as native
        client,_=r2_images();patched,report=delta_build(client)
        case=native.CurrentDeltaTests('test_same_native_entry_with_current_patch_reaches_forward_update')
        case.base,case.new,case.report=client,patched,report
        old=case.run_native(0xBD220457,False)
        new=case.run_native(0xBD220457,True)
        self.assertEqual(old[0],[('native_assert',3)])
        self.assertEqual(new[:2],(['native_forward'],0))
        for bits in (0,0x3F800000):
            original,guarded=case.run_native(bits,False),case.run_native(bits,True)
            self.assertEqual(original[:2],guarded[:2])
            self.assertEqual(original[3],guarded[3])

    def test_station_on_r2_preserves_host_milestones_and_retry(self):
        _, server = r2_images()
        result, report = gas_build(server, SERVER_R2)
        before, after = PE32(server), PE32(result)
        for at, length in ((host.HANDLER, len(host.HEAD)), (host.RESET, 5), (host.SUB_SLOT, 4)):
            self.assertEqual(after.read(at, length), before.read(at, length))
        self.assertFalse(report['changes_world_collision'])
        self.assertFalse(report['gameplay_verified'])
        with self.assertRaises(ValueError):
            gas_build(result, SERVER_R2)

    def test_optional_ai_guard_accepts_r2_without_touching_milestones(self):
        _, server = r2_images()
        result, report = ai_build(server)
        before, after = PE32(server), PE32(result)
        for at, length in ((host.HANDLER, len(host.HEAD)), (host.RESET, 5), (host.SUB_SLOT, 4)):
            self.assertEqual(after.read(at, length), before.read(at, length))
        self.assertFalse(report['gameplay_verified'])
        with self.assertRaises(ValueError):
            ai_build(result)

    def test_exact_native_ports_reject_one_byte_mutation(self):
        client, server = r2_images()
        for data, builder in ((client, team_build), (server, ai_build),
                              (server, lambda b: gas_build(b, SERVER_R2))):
            changed = bytearray(data)
            changed[-1] ^= 1
            with self.assertRaises(ValueError):
                builder(bytes(changed))


if __name__ == '__main__':
    unittest.main()
