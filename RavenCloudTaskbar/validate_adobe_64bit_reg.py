import json
from pathlib import Path

SPEC = Path('specs/FR-0333-ADOBE-64BIT-REG.v1.0.5-RC.json')

ALLOWED_EVIDENCE = {'E_OBS','E_MES','E_DER','E_INF','E_CLM'}
ALLOWED_GATES = {
    'PASS','ROUTE_UNVERIFIED','HALT_STREAM','HARD_PURGE',
    'HALT_STREAM_IF_APPLICABLE','HALT_STREAM_ON_INVALID_APPLICABLE_STATUS'
}


def load_spec():
    with SPEC.open('r', encoding='utf-8') as f:
        return json.load(f)


def iter_bits(spec):
    for cluster_name, cluster in spec['register_schema'].items():
        for bit_name, bit in cluster.items():
            yield cluster_name, bit_name, bit


def main():
    spec = load_spec()
    bits = list(iter_bits(spec))

    assert spec['specification_metadata']['identifier'] == 'FR-0333-ADOBE-64BIT-REG'
    assert spec['specification_metadata']['architecture_version'] == '1.0.5-RC'
    assert len(bits) == 64, f'expected 64 bits, found {len(bits)}'

    expected = {f'BIT_{i:02d}' for i in range(1, 65)}
    actual = {name for _, name, _ in bits}
    assert actual == expected, f'bit register mismatch: missing={expected-actual}, extra={actual-expected}'

    field_names = [bit['field_name'] for _, _, bit in bits]
    assert len(field_names) == len(set(field_names)), 'field_name values must be unique'

    for cluster, name, bit in bits:
        assert bit['evidence_class'] in ALLOWED_EVIDENCE, f'{cluster}/{name}: bad evidence_class'
        assert bit['zero_lion_gate'] in ALLOWED_GATES, f'{cluster}/{name}: bad gate'
        assert 'calculation' in bit and bit['calculation'], f'{cluster}/{name}: missing calculation'
        assert 'failure_state' in bit, f'{cluster}/{name}: missing failure_state'

    # Hardening invariants from the 1.0.5-RC review.
    bit = {name: data for _, name, data in bits}

    assert bit['BIT_04']['failure_state'] == 'NULL', 'BIT_04 must not use year-zero sentinel'
    assert bit['BIT_29']['failure_state'] == 'NULL', 'BIT_29 must not use epoch-zero as missing sentinel'

    assert bit['BIT_11']['zero_lion_gate'] == 'ROUTE_UNVERIFIED'
    assert bit['BIT_13']['zero_lion_gate'] == 'ROUTE_UNVERIFIED'
    assert bit['BIT_25']['zero_lion_gate'] == 'ROUTE_UNVERIFIED'

    for n in ('BIT_12','BIT_14','BIT_28','BIT_36','BIT_37','BIT_39'):
        assert bit[n].get('applicability'), f'{n} requires applicability semantics'
        assert bit[n].get('value_when_not_applicable') == 'NULL', f'{n} must represent N/A as NULL'

    assert bit['BIT_10'].get('interpretation') == 'DESCRIPTIVE_ONLY_NOT_TAMPER_PROOF'
    assert bit['BIT_16']['field_name'] == 'tamper_suspected'
    assert 'signed_claim_binding_contradiction' in bit['BIT_16']['calculation']

    assert bit['BIT_26']['field_name'] == 'signer_credential_verification_state'
    assert bit['BIT_30']['field_name'] == 'credential_key_usage'
    assert bit['BIT_31'].get('authorization_use') == 'PROHIBITED'
    assert bit['BIT_32'].get('human_identity_claim') == 'PROHIBITED'
    assert bit['BIT_36']['field_name'] == 'signer_credential_control_edge'

    assert bit['BIT_46']['failure_state'] == 'NULL', 'detector failure must not become synthetic=1.0'
    assert bit['BIT_48']['value_when_not_applicable'] == 'NULL'

    assert 'count_applicable' in bit['BIT_40']['calculation']
    assert 'applicable' in bit['BIT_56']['calculation']
    assert 'applicable' in bit['BIT_60']['calculation']

    assert bit['BIT_62']['zero_lion_gate'] == 'HARD_PURGE'
    assert bit['BIT_63']['zero_lion_gate'] == 'HARD_PURGE'

    print('FR-0333-ADOBE-64BIT-REG validation PASS')
    print('64/64 bits present')
    print('evidence classes valid')
    print('applicability semantics enforced')
    print('identity/authorization separation enforced')
    print('detector failure semantics enforced')
    print('consent/privacy hard purge gates enforced')


if __name__ == '__main__':
    main()
