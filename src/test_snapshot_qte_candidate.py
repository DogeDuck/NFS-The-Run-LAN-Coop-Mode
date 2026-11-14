import struct
import unittest
import snapshot_qte_roles as s
import qte_host_milestones as a

class Reader:
    def __init__(self,raw,unstable=False):self.raw=raw;self.reads=0;self.unstable=unstable
    def read(self,address,size):
        assert address==s.CANDIDATE_STATS
        self.reads+=1
        return self.raw[:size] if not self.unstable or self.reads==1 else b'x'*size

class Tests(unittest.TestCase):
    def test_unknown_image_is_never_read(self):
        r=Reader(b'');self.assertIsNone(s.candidate_snapshot(r,'unknown'));self.assertEqual(r.reads,0)
    def test_exact_client_counter_pair(self):
        self.assertEqual(s.candidate_snapshot(Reader(struct.pack('<2I',3,5)),s.LOCAL_ACTOR_CLIENT),
                         dict(kind='local_actor',native_getters=3,local_selections=5))
    def test_server_entries_are_bounded_and_not_dereferenced(self):
        raw=bytearray(a.STATS_SIZE);struct.pack_into('<I',raw,0x28,4)
        struct.pack_into('<5I',raw,a.CACHE,0xDEAD0000,1,2,0x8000000F,2)
        r=Reader(raw);result=s.candidate_snapshot(r,s.MILESTONE_SERVER)
        self.assertEqual(r.reads,2);self.assertEqual(result['human_count'],4)
        self.assertEqual(result['entries'][0]['arrived_mask'],15);self.assertTrue(result['entries'][0]['closed'])
    def test_changing_or_malformed_snapshots_do_not_claim_readiness(self):
        r=Reader(bytes(a.STATS_SIZE),True)
        self.assertEqual(s.candidate_snapshot(r,s.MILESTONE_SERVER),dict(kind='host_milestones',stable=False))
        raw=bytearray(a.STATS_SIZE);struct.pack_into('<I',raw,0x28,5)
        with self.assertRaisesRegex(ValueError,'roster'):s.candidate_snapshot(Reader(raw),s.MILESTONE_SERVER)

if __name__=='__main__':unittest.main()
