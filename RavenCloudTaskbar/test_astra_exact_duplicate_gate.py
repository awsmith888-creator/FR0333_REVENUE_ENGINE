import tempfile
import unittest
from pathlib import Path
from astra_exact_duplicate_gate import audit, digest_file


class ExactDuplicateGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def make(self, name, data):
        path = self.folder / name
        path.write_bytes(data)
        return path

    def test_two_matching_files_form_one_group(self):
        a = self.make('a.jpg', b'abc' * 100)
        b = self.make('b.jpeg', b'abc' * 100)
        report = audit([str(a), str(b)])
        self.assertEqual(report['exact_duplicate_excess_copies'], 1)
        self.assertEqual(report['exact_duplicate_groups'][0]['sha256'], digest_file(a))
        self.assertEqual(report['library_mutations'], 0)
        self.assertEqual(report['deleted_files'], [])

    def test_same_byte_size_is_not_proof(self):
        a = self.make('a.png', b'abc')
        b = self.make('b.png', b'xyz')
        self.assertEqual(a.stat().st_size, b.stat().st_size)
        self.assertEqual(audit([str(a), str(b)])['exact_duplicate_groups'], [])

    def test_three_copies_produce_two_excess(self):
        p = [self.make(f'{n}.png', b'fixed') for n in 'abc']
        report = audit(map(str, p))
        self.assertEqual(report['exact_duplicate_excess_copies'], 2)
        self.assertTrue(all(x.exists() for x in p))

    def test_repeated_path_is_not_duplicate(self):
        p = self.make('single.png', b'image')
        report = audit([str(p), str(p)])
        self.assertEqual(report['input_unique_paths'], 1)
        self.assertEqual(report['exact_duplicate_groups'], [])

    def test_nonimage_and_missing_files_rejected(self):
        other = self.make('notes.txt', b'image')
        r = audit([str(other), str(self.folder / 'missing.png')])
        self.assertEqual(len(r['rejected_inputs']), 2)
        self.assertEqual(r['input_unique_paths'], 0)

    def test_keeps_distinct_images_and_never_selects_delete_target(self):
        a = self.make('a.png', b'alpha')
        b = self.make('b.png', b'alpha')
        c = self.make('c.png', b'omega')
        before = {p: p.read_bytes() for p in [a, b, c]}
        report = audit([str(a), str(b), str(c)])
        self.assertIsNone(report['selected_canonical_file'])
        self.assertEqual(report['library_mutations'], 0)
        self.assertEqual(report['deleted_files'], [])
        self.assertEqual(before, {p: p.read_bytes() for p in before})


if __name__ == '__main__':
    unittest.main(verbosity=2)
