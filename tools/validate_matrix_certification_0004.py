import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'specs/fr0333_333_matrix_system_0004.json'
MANIFEST = ROOT / 'certification/FR0333_CERTIFICATION_MANIFEST_0004.json'

REQUIRED_GATES = ["SPEC","SCHEMA","CHAIN","MATRIX","HUMANLOCK","AUTHORITY","PROVENANCE","EVIDENCE","EXECUTION","TRACE","REPLAY","LOOP_GUARD","ADVERSARIAL","REGRESSION","SECURITY","HASH","PACKAGE"]


def validate():
    spec = json.loads(SPEC.read_text())
    cert = json.loads(MANIFEST.read_text())
    checks = {
        'canonical_root': spec['canonical_root'] == 'FR-0333 ZERO LION LOGIC GATE FOREVER AND A DAY 1',
        'golden_chain_unchanged': spec['golden_chain'] == 'CANONICAL_UNCHANGED',
        'humanlock': spec['humanlock'] == 'ACTIVE_IMMUTABLE',
        'external_authority_zero': spec['external_authority'] == 'ZERO',
        'promotion_default_deny': spec['promotion_default'] == 'DENY',
        'boolean_belt': spec['belt_semantics']['mode'] == 'BOOLEAN_COMPLETION',
        'partial_pass_forbidden': spec['belt_semantics']['partial_pass'] == 'FORBIDDEN',
        'probability_substitution_forbidden': spec['belt_semantics']['probability_substitution'] == 'FORBIDDEN',
        'four_planes': set(spec['planes']) == {'TRUTH','EXECUTION','AUTHORITY','CERTIFICATION'},
        'unknown_first_class': 'UNKNOWN_FIRST_CLASS' in spec['planes']['TRUTH'],
        'loop_guard': 'LOOP_GUARD' in spec['planes']['EXECUTION'],
        'fist_fail_closed': spec['fist']['rule'] == 'ANY_FAIL_HOLD',
        'gate_count': len(cert['required_gates']) == 17,
        'gate_identity': cert['required_gates'] == REQUIRED_GATES,
        'pass_rule': cert['pass_rule'] == '17_OF_17_PASS',
        'failure_hold': cert['otherwise'] == 'HOLD',
        'operator_gate': cert['operator_gate'] == 'HUMANLOCK_REQUIRED_FOR_L4',
        'no_false_accreditation': cert['claims_control']['accredited_certification'] is False,
    }
    failed = [k for k,v in checks.items() if not v]
    receipt = {'validator':'FR0333.MATRIX.CERTIFICATION.VALIDATOR.0004','checks':checks,'passed':len(checks)-len(failed),'required':len(checks),'state':'PASS' if not failed else 'HOLD','failed':failed}
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if failed:
        raise SystemExit(1)

if __name__ == '__main__':
    validate()
