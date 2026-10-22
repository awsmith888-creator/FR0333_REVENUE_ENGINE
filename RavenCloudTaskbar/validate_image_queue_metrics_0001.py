#!/usr/bin/env python3
"""Offline consistency gates. Never invokes providers or workflows."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
METRICS = 'fr0333_image_queue_metrics_0001.json'

def require(condition, message):
    if not condition:
        raise ValueError(message)

def read(root, name):
    return json.loads((root / name).read_text())

def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def validate(root=ROOT):
    m = read(root, METRICS)
    old = read(root, 'fr0333_image_queue_failure_closure_0001.json')
    index = read(root, 'fr0333_golden_chain_index_0001.json')
    before = read(root, 'evidence/image_queue_index_at_417f409.json')
    require(m['identifier'] == 'FR.0333.GOLDEN.CHAIN.IMAGE.QUEUE.METRICS.0001', 'metrics identity')
    require(m['certificate_type'] == 'SELF_ISSUED_NOT_EXTERNAL_ATTESTATION', 'certificate boundary')
    require(m['lanes']['active']['scope'] == 'AUTHORIZED_OFFLINE_CHECKS_ONLY', 'active scope')
    require(m['lanes']['passive']['scope'] == 'PRESERVED_CLAIMS_AND_REMAINS_NO_EXECUTION', 'passive scope')
    require(m['lanes']['passive']['automatic_execution'] is False, 'passive execution')
    require(m['provider_calls'] == 0 and m['workflow_dispatches'] == 0, 'execution boundary')
    require(m['quality_promotion'] == 'HOLD', 'quality boundary')
    require(old['closure']['live_provider_delivery'] == 'HOLD_NOT_REEXECUTED', 'original live HOLD')
    require(old['verification']['current_tests']['evidence_class'] == 'SIMULATED_FIXTURE', 'fixture boundary')
    require(old['certificate_type'] == 'SELF_ISSUED_VERIFICATION_RECORD_NOT_EXTERNAL_ATTESTATION', 'original certificate')
    require({i['path'] for i in old['source_files']} == {
        'RavenCloudTaskbar/fr0333_image_queue_runtime.py',
        'RavenCloudTaskbar/test_fr0333_image_queue_runtime.py',
        'historical/RavenCloudTaskbar/fr0333_image_queue_runtime.py',
        'historical/RavenCloudTaskbar/test_fr0333_image_queue_runtime.py'}, 'source coverage')
    active = m['lanes']['active']['metrics']
    require([v['id'] for v in active] == ['A.1', 'A.2', 'A.3', 'A.4', 'A.5', 'A.6'], 'active metric coverage')
    require((active[0]['matched'], active[0]['expected']) == (4, 4), 'hash metric')
    require((active[1]['passed'], active[1]['total'], active[1]['class']) == (10, 10, 'SIMULATED_FIXTURE'), 'current metric')
    require((active[2]['errors'], active[2]['tests'], active[2]['exit_code']) == (8, 8, 1), 'historical metric')
    require(all((v['matched'], v['expected']) == (1, 1) for v in active[3:5]), 'document metrics')
    require(active[5]['count'] == len(before['entries']) == 8, 'index metric')
    passive = m['lanes']['passive']['metrics']
    require([v['id'] for v in passive] == ['P.1', 'P.2', 'P.3'], 'passive coverage')
    require(all(v['class'] == 'HOLD' for v in passive), 'passive HOLD')
    require((passive[0]['claimed'], passive[0]['bytes_reverified_this_task']) == (10, 0), 'output metric')
    require(passive[1]['state'] == 'NOT_OBSERVED' and passive[2]['state'] == 'NOT_ESTABLISHED', 'acceptance/attestation boundary')
    for item in old['source_files']:
        data = (root.parent / item['path']).read_bytes()
        require(hashlib.sha256(data).hexdigest() == item['sha256'], 'source SHA256: ' + item['path'])
        require(blob(data) == item['git_blob_sha'], 'source blob: ' + item['path'])
    for item in m['bound_files']:
        data = (root.parent / item['path']).read_bytes()
        require(hashlib.sha256(data).hexdigest() == item['sha256'], 'bound file: ' + item['path'])
    require(len(m['bound_files']) == 12 and len({i['path'] for i in m['bound_files']}) == 12, 'bound evidence coverage')
    log = (root / 'evidence/image_queue_original_job.log').read_bytes()
    require(hashlib.sha256(log).hexdigest() == old['original_job_log_sha256'], 'original log hash')
    text = log.decode('utf-8-sig')
    require(old['observed']['error'] in text, 'original exception absent')
    require(old['reference_point']['checkout_sha'] in text, 'checkout absent from retained log')
    receipt = (root.parent / old['later_receipt']['path']).read_bytes()
    require(blob(receipt) == old['later_receipt']['git_blob_sha'], 'later receipt blob')
    require(index['entries'][:len(before['entries'])] == before['entries'], 'prior entries changed')
    require(index['public_index'][:len(before['public_index'])] == before['public_index'], 'prior public index changed')
    require(index['rules'] == before['rules'], 'index rules changed')
    entries = index['entries']
    require(len({e['index'] for e in entries}) == len(entries), 'duplicate index')
    require(len({e['identifier'] for e in entries}) == len(entries), 'duplicate identifier')
    require(index['public_index'] == [e['index'] + '.' + e['identifier'] for e in entries], 'public index mismatch')
    expected = {'index': '0.9', 'identifier': m['identifier'], 'artifact': 'RavenCloudTaskbar/' + METRICS, 'state': 'OFFLINE_METRICS_VERIFIED_PASSIVE_REMAINS_HOLD'}
    require(entries[len(before['entries']):] == [expected], 'metrics index binding')
    require(m['parent_entry'] == before['entries'][-1], 'parent 0.8 binding')
    remains = read(root, m['remains_certificate'])
    require(remains['certificate_type'] == 'SELF_ISSUED_NOT_EXTERNAL_ATTESTATION', 'remains certificate')
    require(remains['parent_identifier'] == m['identifier'], 'remains parent')
    require(len({r['id'] for r in remains['items']}) == len(remains['items']), 'duplicate remains')
    require({r['id'] for r in remains['items']} == {'R.' + str(i) for i in range(1, 8)}, 'remains coverage')
    require(all(r['lane'] == 'PASSIVE' and r['state'] == 'HOLD' and r['evidence_needed'] for r in remains['items']), 'remains gate')
    runs = read(root, m['execution_receipt'])
    require(runs['certificate_type'] == 'SELF_ISSUED_NOT_EXTERNAL_ATTESTATION', 'execution certificate')
    for key, tests, errors, code in [('current', 10, 0, 0), ('historical', 8, 8, 1)]:
        r = runs[key]
        raw = (root / r['log']).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == r['sha256'], key + ' execution log hash')
        s = raw.decode()
        require(r['tests'] == tests and r['errors'] == errors and r['exit_code'] == code, key + ' counters')
        require(('Ran ' + str(tests) + ' tests') in s, key + ' test summary')
        require(('FAILED (errors=8)' if errors else '\nOK\n') in s, key + ' result summary')
        if errors:
            require(s.count('takes 1 positional argument but 2 were given') == 8 and old['observed']['error'] in s, 'historical callback exception count')
    regression = runs['metrics_regression']
    data = (root / regression['log']).read_bytes()
    require(hashlib.sha256(data).hexdigest() == regression['sha256'], 'regression log hash')
    require((regression['tests'], regression['errors'], regression['exit_code']) == (9, 0, 0), 'regression counters')
    require('Ran 9 tests' in data.decode() and '\nOK\n' in data.decode(), 'regression summary')
    print('PASS: source/log/receipt hashes · index links · active/passive metrics · self-issued boundaries')
    return m

if __name__ == '__main__':
    validate()
