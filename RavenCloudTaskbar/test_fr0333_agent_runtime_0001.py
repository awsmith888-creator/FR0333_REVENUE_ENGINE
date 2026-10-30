import unittest
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fr0333_agent_runtime_0001 import (
    AdobeMCPDiscovery, GateError, MCPResponse, authorize_action, config_status, local_model_completion, probability_from_receipts,
    validate_adobe_mcp_url, validate_local_model_url,
)


class AgentGateTests(unittest.TestCase):
    def test_no_probability_is_claimed_without_minimum_receipts(self):
        result = probability_from_receipts([], task_class="single-image-output")
        self.assertIsNone(result["probability"])
        self.assertEqual(result["state"], "U.21.HOLD.INSUFFICIENT_VERIFIED_TRIALS")

    def test_receipt_probability_has_interval_and_evidence_basis(self):
        receipts = [{"task_class":"single-image-output", "outcome":i < 8,
                     "verification_state":"INDEPENDENTLY_VERIFIED",
                     "receipt_sha256":f"{i + 1:064x}"} for i in range(10)]
        result = probability_from_receipts(receipts, task_class="single-image-output")
        self.assertEqual(result["probability"], 0.8)
        self.assertLessEqual(result["interval_95"][0], 0.8)
        self.assertGreaterEqual(result["interval_95"][1], 0.8)
        self.assertEqual(result["evidence_basis"], "CALLER_DECLARED_INDEPENDENTLY_VERIFIED_RECEIPTS")
        self.assertEqual(result["receipt_authenticity"], "NOT_CRYPTOGRAPHICALLY_AUTHENTICATED")

    def test_probability_rejects_invalid_receipts(self):
        cases = [
            ([{"task_class":"other", "outcome":True, "verification_state":"INDEPENDENTLY_VERIFIED", "receipt_sha256":"1"*64}], "expected"),
            ([{"task_class":"expected", "outcome":1, "verification_state":"INDEPENDENTLY_VERIFIED", "receipt_sha256":"1"*64}], "expected"),
            ([{"task_class":"expected", "outcome":True, "verification_state":"UNVERIFIED", "receipt_sha256":"1"*64}], "expected"),
            ([{"task_class":"expected", "outcome":True, "verification_state":"INDEPENDENTLY_VERIFIED", "receipt_sha256":"1"*64}]*2, "expected"),
        ]
        for receipts, task_class in cases:
            with self.subTest(receipts=receipts), self.assertRaises(GateError):
                probability_from_receipts(receipts, task_class=task_class)

    def test_model_endpoint_is_loopback_only(self):
        self.assertEqual(validate_local_model_url("http://localhost:8000/v1"), "http://localhost:8000/v1")
        for value in ["https://provider.example/v1", "http://169.254.169.254/latest", "file:///etc/passwd"]:
            with self.subTest(value=value), self.assertRaises(GateError):
                validate_local_model_url(value)

    def test_adobe_endpoint_requires_tls_and_adobe_domain(self):
        self.assertEqual(validate_adobe_mcp_url("https://example.adobe.io/mcp"), "https://example.adobe.io/mcp")
        for value in ["http://example.adobe.io/mcp", "https://adobe.io.attacker.test/mcp", "https://example.com/mcp"]:
            with self.subTest(value=value), self.assertRaises(GateError):
                validate_adobe_mcp_url(value)

    def test_sensitive_actions_need_operator_approval(self):
        self.assertEqual(authorize_action("add_board_item")["state"], "U.21.HOLD.OPERATOR_APPROVAL_REQUIRED")
        self.assertEqual(authorize_action("add_board_item", operator_approved=True)["state"], "T.20.PASS.ACTION_AUTHORIZED_FOR_ADAPTER")
        with self.assertRaises(GateError):
            authorize_action("shell_exec", operator_approved=True)

    def test_self_check_is_disconnected_and_makes_no_network_calls(self):
        result = config_status({})
        self.assertEqual(result["model_adapter"], "DEFAULT_LOOPBACK_URL_NOT_PROBED")
        self.assertEqual(result["adobe_adapter"], "HOLD.DISCONNECTED")
        self.assertEqual(result["network_calls"], 0)
        self.assertEqual(result["tool_calls"], 0)
        self.assertEqual(result["writes"], 0)

    def test_probability_requires_task_class(self):
        with self.assertRaises(GateError):
            probability_from_receipts([], task_class="")

    def test_passive_active_spec_pairs_ten_to_ten(self):
        path = Path(__file__).with_name("fr0333_agent_capability_evolution_0001.json")
        spec = json.loads(path.read_text(encoding="utf-8"))
        passive = spec["passive_matrix"]
        active = spec["active_metrics"]
        self.assertEqual(len(passive), 10)
        self.assertEqual(len(active), 10)
        self.assertEqual({item["id"] for item in passive}, {f"M{i:02d}" for i in range(1, 11)})
        self.assertEqual({item["id"] for item in active}, {f"A{i:02d}" for i in range(1, 11)})
        self.assertEqual({item["ref"] for item in active}, {item["id"] for item in passive})

    def test_runtime_spec_does_not_claim_live_connections(self):
        path = Path(__file__).with_name("fr0333_agent_capability_evolution_0001.json")
        spec = json.loads(path.read_text(encoding="utf-8"))
        evidence = spec["implementation_evidence"]
        self.assertEqual(evidence["adobe_runtime_connection"], "U.21.HOLD.DISCONNECTED_UNTIL_ENDPOINT_AND_OPERATOR_TOKEN_ARE_CONFIGURED")
        self.assertEqual(evidence["external_network_calls"], 0)
        self.assertEqual(evidence["canonical_promotion"], "HUMANLOCK_HOLD")

    def test_model_response_is_text_only_and_has_no_tools(self):
        from unittest.mock import patch
        expected = {"choices": [{"message": {"content": "proposed plan"}}]}
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, limit):
                return json.dumps(expected).encode("utf-8")
        with patch("fr0333_agent_runtime_0001.urllib.request.build_opener") as build_opener:
            build_opener.return_value.open.return_value = Response()
            result = local_model_completion("summarize this", endpoint="http://127.0.0.1:8000/v1")
        self.assertEqual(result["response"], "proposed plan")
        self.assertEqual(result["tool_calls"], 0)
        self.assertEqual(result["writes"], 0)

    def test_adobe_discovery_never_invokes_tools(self):
        from unittest.mock import patch
        client = AdobeMCPDiscovery("https://example.adobe.io/mcp", "test-token")
        calls = []
        def fake_post(method, params=None):
            calls.append(method)
            if method == "initialize":
                return MCPResponse({"result": {"protocolVersion": "2025-03-26"}}, None)
            return MCPResponse({"result": {"tools": [{"name": "boards_read"}]}}, "session")
        with patch.object(client, "_post", side_effect=fake_post), patch.object(client, "_notification"):
            result = client.discover()
        self.assertEqual(calls, ["initialize", "tools/list"])
        self.assertEqual(result["tools_invoked"], 0)
        self.assertEqual(result["writes"], 0)


if __name__ == "__main__":
    unittest.main()
