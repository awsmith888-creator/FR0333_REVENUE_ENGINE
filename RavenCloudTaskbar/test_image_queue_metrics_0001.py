#!/usr/bin/env python3
"""Fail-closed regression checks, including optimized Python."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from validate_image_queue_metrics_0001 import validate, ROOT, METRICS

class MetricsTests(unittest.TestCase):
    def check_mutation(self, filename, change):
        with tempfile.TemporaryDirectory() as temp:
            dst = Path(temp) / 'repo'
            shutil.copytree(ROOT.parent, dst, ignore=shutil.ignore_patterns('__pycache__'))
            target = dst / 'RavenCloudTaskbar' / filename
            data = json.loads(target.read_text())
            change(data)
            target.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                validate(dst / 'RavenCloudTaskbar')
            result = subprocess.run([sys.executable, '-O', str(dst / 'RavenCloudTaskbar/validate_image_queue_metrics_0001.py')], capture_output=True)
            self.assertNotEqual(result.returncode, 0)

    def test_valid_normal_and_optimized(self):
        validate()
        subprocess.run([sys.executable, '-O', str(ROOT / 'validate_image_queue_metrics_0001.py')], check=True, capture_output=True)

    def test_passive_cannot_execute(self):
        self.check_mutation(METRICS, lambda d: d['lanes']['passive'].update(automatic_execution=True))

    def test_active_metric_cannot_inflate(self):
        self.check_mutation(METRICS, lambda d: d['lanes']['active']['metrics'][1].update(passed=11))

    def test_live_claim_cannot_be_promoted(self):
        self.check_mutation('fr0333_image_queue_failure_closure_0001.json', lambda d: d['closure'].update(live_provider_delivery='PASS'))

    def test_prior_index_cannot_change(self):
        self.check_mutation('fr0333_golden_chain_index_0001.json', lambda d: d['entries'][0].update(state='PROMOTED'))

    def test_public_index_cannot_drift(self):
        self.check_mutation('fr0333_golden_chain_index_0001.json', lambda d: d['public_index'].pop())

    def test_artifact_binding_cannot_drift(self):
        self.check_mutation('fr0333_golden_chain_index_0001.json', lambda d: d['entries'][-1].update(artifact='missing.json'))

    def test_recorded_counts_cannot_drift(self):
        self.check_mutation('fr0333_image_queue_metrics_execution_0001.json', lambda d: d['current'].update(tests=11))

    def test_output_claim_cannot_change(self):
        self.check_mutation('fr0333_adobe_image_queue_runtime_receipt_0003.json', lambda d: d['queue'].update(final_delivered_count=11))

if __name__ == '__main__':
    unittest.main(verbosity=2)
