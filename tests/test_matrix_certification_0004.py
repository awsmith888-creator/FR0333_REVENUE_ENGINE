import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT/'specs/fr0333_333_matrix_system_0004.json').read_text())
CERT = json.loads((ROOT/'certification/FR0333_CERTIFICATION_MANIFEST_0004.json').read_text())

class MatrixCertification0004(unittest.TestCase):
    def test_authority(self):
        self.assertEqual(SPEC['humanlock'], 'ACTIVE_IMMUTABLE')
        self.assertEqual(SPEC['external_authority'], 'ZERO')
        self.assertEqual(SPEC['promotion_default'], 'DENY')

    def test_belt_is_boolean_not_probability(self):
        belt = SPEC['belt_semantics']
        self.assertEqual(belt['mode'], 'BOOLEAN_COMPLETION')
        self.assertEqual(belt['partial_pass'], 'FORBIDDEN')
        self.assertEqual(belt['probability_substitution'], 'FORBIDDEN')

    def test_matrix_planes(self):
        self.assertEqual(set(SPEC['planes']), {'TRUTH','EXECUTION','AUTHORITY','CERTIFICATION'})
        self.assertIn('UNKNOWN_FIRST_CLASS', SPEC['planes']['TRUTH'])
        self.assertIn('LOOP_GUARD', SPEC['planes']['EXECUTION'])

    def test_fist_fail_closed(self):
        self.assertEqual(SPEC['fist']['rule'], 'ANY_FAIL_HOLD')

    def test_certificate_gate_count(self):
        self.assertEqual(len(CERT['required_gates']), 17)
        self.assertEqual(CERT['pass_rule'], '17_OF_17_PASS')
        self.assertEqual(CERT['otherwise'], 'HOLD')

    def test_no_false_legal_or_accreditation_claim(self):
        c = CERT['claims_control']
        self.assertFalse(c['accredited_certification'])
        self.assertFalse(c['government_certification'])
        self.assertFalse(c['legal_opinion'])
        self.assertFalse(c['production_approval'])

    def test_operator_gate(self):
        self.assertEqual(CERT['operator_gate'], 'HUMANLOCK_REQUIRED_FOR_L4')

if __name__ == '__main__':
    unittest.main()
