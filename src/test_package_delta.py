import unittest
from build_test_package import delta, apply,reverse_apply,research_baseline


class DeltaTests(unittest.TestCase):
    def test_changes_across_block_boundary_and_append(self):
        before = b'a' * 8192
        after = bytearray(before)
        after[4094:4098] = b'bbbb'
        after += b'our adapter'
        self.assertEqual(apply(before, delta('test', before, after)), bytes(after))

    def test_unchanged_and_wrong_baseline(self):
        patch = delta('test', b'abc', b'abc')
        self.assertEqual(apply(b'abc', patch), b'abc')
        with self.assertRaises(ValueError):
            apply(b'abd', patch)
        with self.assertRaises(ValueError):
            delta('test', b'abc', b'ab')

    def test_reverse_reconstructs_installed_candidate_without_mutating_input(self):
        before=b'a'*8192;after=before[:4094]+b'bbbb'+before[4098:]+b'new sections'
        patch=delta('test',before,after)
        self.assertEqual(reverse_apply(after,patch),before)
        self.assertEqual(research_baseline(after,patch),before)
        self.assertEqual(research_baseline(before,patch),before)
        self.assertTrue(after.endswith(b'new sections'))
    def test_reverse_rejects_unknown_build_and_invalid_runs(self):
        patch=delta('test',b'abc',b'bbcADAPTER')
        with self.assertRaises(ValueError):reverse_apply(b'changed',patch)
        patch['Changes'][0]['Offset']=-1
        with self.assertRaises(ValueError):reverse_apply(b'bbcADAPTER',patch)

    def test_new_candidate_recovers_same_baseline_without_accepting_other_sources(self):
        old=delta('test',b'abc',b'bbcOLD')
        new=delta('test',b'abc',b'cbcNEW')
        self.assertEqual(research_baseline(b'cbcNEW',old,[new]),b'abc')
        alien=delta('test',b'xyz',b'cbcNEW')
        with self.assertRaises(ValueError):research_baseline(b'cbcNEW',old,[alien])
        with self.assertRaises(ValueError):research_baseline(b'cbcBAD',old,[new])


if __name__ == '__main__':
    unittest.main()
