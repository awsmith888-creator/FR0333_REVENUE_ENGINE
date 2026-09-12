import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).with_name("fr0333_reference_point_gate.py")
spec = importlib.util.spec_from_file_location("reference_gate", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ReferencePointGateTests(unittest.TestCase):
    def test_canonical_delta_forms_pass(self):
        d = mod.INCREMENT
        for token in [f"1.{d}.1.1", f"1.{d}.1.26", f"1.{d}.1.0026", f"1.{d}.1.80"]:
            self.assertEqual(mod.validate_delta_text(token, "fixture"), [])

    def test_missing_reference_points_fail(self):
        d = mod.INCREMENT
        bad = [f"1.{d}26", f"1.{d}.26", f"1{d}.1.26", f"{d}.1.26", f"1.{d}1.26"]
        for token in bad:
            self.assertTrue(mod.validate_delta_text(token, "fixture"), token)

    def test_wrong_delta_glyph_fails(self):
        self.assertTrue(mod.validate_delta_text(f"1.{mod.GREEK_DELTA}.1.26", "fixture"))

    def test_reference_tokens_stay_exact_strings(self):
        errors = mod.validate_reference_file()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
