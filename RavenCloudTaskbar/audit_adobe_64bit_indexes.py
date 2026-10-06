import hashlib
import json
from pathlib import Path

SPEC_PATH = Path('specs/FR-0333-ADOBE-64BIT-REG.v1.0.5-RC.json')
INDEX_A_PATH = Path('specs/FR-0333-ADOBE-64BIT-INDEX.A.v1.0.5-RC.json')
INDEX_B_PATH = Path('specs/FR-0333-ADOBE-64BIT-INDEX.B.v1.0.5-RC.json')


def load(path):
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def digest(value):
    payload = json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def expand_a(index_a):
    mapping = {}
    for cluster, block in index_a['clusters'].items():
        start = int(block['start'])
        end = int(block['end'])
        declared_count = int(block['count'])
        assert end >= start, f'INDEX_A invalid range for {cluster}'
        assert end - start + 1 == declared_count, f'INDEX_A count mismatch for {cluster}'
        for number in range(start, end + 1):
            bit_id = f'BIT_{number:02d}'
            assert bit_id not in mapping, f'INDEX_A duplicate {bit_id}'
            mapping[bit_id] = cluster
    return mapping


def expand_b(index_b):
    mapping = {}
    for block in index_b['ranges']:
        start = int(block['start'])
        end = int(block['end'])
        cluster = block['cluster']
        assert end >= start, f'INDEX_B invalid range for {cluster}'
        for number in range(start, end + 1):
            bit_id = f'BIT_{number:02d}'
            assert bit_id not in mapping, f'INDEX_B duplicate {bit_id}'
            mapping[bit_id] = cluster
    return mapping


def spec_maps(spec):
    bit_to_cluster = {}
    forward = {}
    reverse = {}

    for cluster, cluster_bits in spec['register_schema'].items():
        for bit_id, bit in cluster_bits.items():
            assert bit_id not in bit_to_cluster, f'spec duplicate {bit_id}'
            field_name = bit['field_name']
            assert field_name not in reverse, f'spec duplicate field_name {field_name}'

            bit_to_cluster[bit_id] = cluster
            forward[bit_id] = {
                'cluster': cluster,
                'field_name': field_name,
                'evidence_class': bit['evidence_class'],
                'zero_lion_gate': bit['zero_lion_gate'],
            }
            reverse[field_name] = {
                'bit_id': bit_id,
                'cluster': cluster,
                'evidence_class': bit['evidence_class'],
                'zero_lion_gate': bit['zero_lion_gate'],
            }

    return bit_to_cluster, forward, reverse


def main():
    spec = load(SPEC_PATH)
    index_a = load(INDEX_A_PATH)
    index_b = load(INDEX_B_PATH)

    version = spec['specification_metadata']['architecture_version']
    assert index_a['version'] == version == index_b['version'], 'index/spec version drift'
    assert index_a['source_spec'] == spec['specification_metadata']['identifier']
    assert index_b['source_spec'] == spec['specification_metadata']['identifier']

    a_map = expand_a(index_a)
    b_map = expand_b(index_b)
    spec_map, forward, reverse = spec_maps(spec)

    expected_ids = {f'BIT_{i:02d}' for i in range(1, 65)}
    assert set(a_map) == expected_ids, 'INDEX_A does not cover exactly BIT_01..BIT_64'
    assert set(b_map) == expected_ids, 'INDEX_B does not cover exactly BIT_01..BIT_64'
    assert index_a['expected_total_bits'] == len(a_map) == 64
    assert index_b['expected_total_bits'] == len(b_map) == 64

    assert a_map == b_map, 'INDEX_A and INDEX_B disagree'
    assert a_map == spec_map, 'indexes disagree with register schema'

    for bit_id, row in forward.items():
        inverse = reverse[row['field_name']]
        assert inverse['bit_id'] == bit_id, f'forward/reverse mismatch at {bit_id}'
        assert inverse['cluster'] == row['cluster'], f'cluster inverse mismatch at {bit_id}'
        assert inverse['evidence_class'] == row['evidence_class'], f'evidence inverse mismatch at {bit_id}'
        assert inverse['zero_lion_gate'] == row['zero_lion_gate'], f'gate inverse mismatch at {bit_id}'

    defined_gates = set(spec['schema_definitions']['zero_lion_gate'])
    used_gates = {row['zero_lion_gate'] for row in forward.values()}
    assert used_gates <= defined_gates, f'index auditor found undefined used gates: {used_gates-defined_gates}'

    print('INDEX_A PASS: forward cluster index covers 64/64 bits')
    print('INDEX_B PASS: reverse range index covers 64/64 bits')
    print('INDEX_A <-> INDEX_B PASS: exact structural agreement')
    print('INDEXES <-> REGISTER PASS: exact bit-to-cluster agreement')
    print('FORWARD <-> REVERSE FIELD INDEX PASS: bijection preserved')
    print('GATE VOCABULARY PASS: every indexed gate is defined in the spec')
    print(f'INDEX_A_SHA256={digest(index_a)}')
    print(f'INDEX_B_SHA256={digest(index_b)}')
    print(f'FORWARD_INDEX_SHA256={digest(forward)}')
    print(f'REVERSE_INDEX_SHA256={digest(reverse)}')


if __name__ == '__main__':
    main()
