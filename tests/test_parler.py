import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/parler-use/scripts/parler.py"
spec = importlib.util.spec_from_file_location("parler", SCRIPT)
parler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parler)


class Queries(unittest.TestCase):
    def setUp(self):
        self.payload = {"ok": True, "apiBaseUrl": parler.API_URL,
                        "user": {"email": "member@example.test", "membership": {"status": "active", "expiresAt": "2026-11-30T00:00:00Z"}},
                        "payments": [{"amount": 20, "currency": "usd"}],
                        "apiKeys": {"keys": [{"id": 41, "name": "member", "key": "sk-test-secret"}]},
                        "rateLimit": {"usage7d": 10, "rateLimit7d": 130, "remaining7d": 120},
                        "accountStatus": {"status": "unavailable", "healthy": None, "truncated": True,
                                          "errorCount": 1, "errors": [{"statusCode": 502, "errorBody": "upstream failed", "upstreamErrorDetail": "details"}]},
                        "tokenUsage": {"configured": True, "matched": True, "stats": {"total_tokens": 50}, "logs": []}}

    def test_every_remote_section_and_membership_expiry_is_preserved(self):
        mapping = {"all": None, "account": "user", "membership": "membership", "payments": "payments", "keys": "apiKeys",
                   "7d": "rateLimit", "status": "accountStatus", "accountStatus": "accountStatus", "tokens": "tokenUsage", "logs": "tokenUsage"}
        for query, field in mapping.items():
            with self.subTest(query=query):
                result = parler.query_usage(query, {}, lambda options: self.payload)
                expected = self.payload if field is None else {field: self.payload["user"]["membership"] if field == "membership" else self.payload[field]}
                self.assertEqual(result, expected)

    def test_partial_status_never_turns_healthy_and_error_details_survive(self):
        status = parler.query_usage("accountStatus", {"error_page": 2}, lambda options: self.payload)["accountStatus"]
        self.assertIsNone(status["healthy"])
        self.assertTrue(status["truncated"])
        self.assertEqual(status["errors"][0]["upstreamErrorDetail"], "details")

    def test_redacts_nested_credentials_without_losing_key_ids_or_errors(self):
        self.payload["accountStatus"]["errors"][0]["message"] = "Bearer private-token or sk-abc123 and saved-password"
        result = parler.redact(self.payload, ("saved-password",))
        text = json.dumps(result)
        for forbidden in ("private-token", "sk-abc123", "sk-test-secret", "saved-password"):
            self.assertNotIn(forbidden, text)
        self.assertEqual(result["apiKeys"]["keys"][0]["id"], 41)
        self.assertIn("upstream failed", text)

    def test_validation_rejects_bad_dates_bounds_and_credential_arguments(self):
        for options in ({"page": 0}, {"page_size": 51}, {"error_page_size": 21}, {"page": True},
                        {"start_date": "2026-10-01"}, {"start_date": "2026-02-30", "end_date": "2026-03-01"},
                        {"start_date": "2026-11-01", "end_date": "2026-10-01"}, {"email": "other"}, {"timezone": "invalid/zone"}):
            with self.subTest(options=options), self.assertRaises(parler.ParlerError):
                parler.validate_options(options)

    def test_credentials_are_only_in_json_body_to_fixed_destination(self):
        with patch.object(parler, "load_config", return_value={"email": "self@example.test", "password": "hidden"}), \
                patch.object(parler, "request_json", return_value=self.payload) as request:
            parler.fetch_usage({"page": 2})
            request.assert_called_once_with(parler.USAGE_URL, {"email": "self@example.test", "password": "hidden", "page": 2})

    def test_redirect_is_stopped_before_credential_forwarding(self):
        with self.assertRaises(parler.ParlerError):
            parler.NoRedirect().redirect_request(None, None, 307, "Redirect", {}, "https://other.example")


class RollingUsage(unittest.TestCase):
    now = datetime(2026, 11, 1, 2, 0, tzinfo=timezone.utc)

    @staticmethod
    def row(identifier, timestamp, tokens=10, cost=0.1):
        return {"id": identifier, "apiKeyId": 41, "createdAt": timestamp, "totalTokens": tokens, "actualCost": cost}

    def test_cross_midnight_boundaries_deduplication_and_independent_paging(self):
        calls = []
        pages = {1: [self.row(1, "2026-11-01T02:00:00Z"), self.row(2, "2026-10-31T22:00:00Z")],
                 2: [self.row(2, "2026-10-31T22:00:00Z"), self.row(3, "2026-10-31T21:00:00Z"), self.row(4, "2026-10-31T20:59:59Z")]}
        def fetch(options):
            calls.append(options)
            return {"tokenUsage": {"configured": True, "matched": True, "logs": pages[options["page"]], "pagination": {"totalPages": 2, "total": 4}}}
        result = parler.rolling_five_hours(fetch, self.now)
        self.assertEqual(result["requests"], 3)
        self.assertEqual(result["totalTokens"], 30)
        self.assertEqual(result["actualCostUSD"], 0.3)
        self.assertTrue(result["complete"])
        self.assertFalse(result["snapshot"])
        self.assertIsNone(result["quotaUsedPercent"])
        self.assertEqual(calls[0]["start_date"], "2026-10-31")
        self.assertEqual(calls[0]["end_date"], "2026-11-01")
        self.assertEqual(calls[0]["timezone"], "UTC")
        self.assertEqual([c["page"] for c in calls], [1, 2])

    def test_page_limit_is_explicitly_incomplete(self):
        fetch = lambda options: {"tokenUsage": {"configured": True, "matched": True,
            "logs": [self.row(1, "2026-11-01T01:00:00Z")], "pagination": {"totalPages": 30, "total": 1500}}}
        result = parler.rolling_five_hours(fetch, self.now, max_pages=1)
        self.assertFalse(result["complete"])
        self.assertEqual(result["requests"], 1)

    def test_missing_service_or_timestamp_is_not_complete_zero(self):
        for usage in ({"configured": False, "matched": False, "message": "Unavailable"},
                      {"configured": True, "matched": True, "logs": [self.row(1, "not-a-date")], "pagination": {"totalPages": 1, "total": 1}}):
            result = parler.rolling_five_hours(lambda options: {"tokenUsage": usage}, self.now)
            self.assertFalse(result["complete"])
            self.assertTrue(result["message"])

    def test_no_logs_can_be_complete_when_upstream_confirms_empty(self):
        result = parler.rolling_five_hours(lambda options: {"tokenUsage": {"configured": True, "matched": True,
            "logs": [], "pagination": {"totalPages": 1, "total": 0}}}, self.now)
        self.assertTrue(result["complete"])
        self.assertEqual(result["requests"], 0)


class MCP(unittest.TestCase):
    def test_real_stdio_lifecycle_protocol_only_output_and_missing_config_error(self):
        messages = ["not-json", json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}),
                    json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                    json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
                    json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "parler_usage", "arguments": {"query": "membership"}}})]
        with tempfile.TemporaryDirectory() as directory:
            env = {k: v for k, v in os.environ.items() if not k.startswith("PARLER_")}
            env["PARLER_CONFIG"] = str(Path(directory) / "missing.json")
            process = subprocess.run([sys.executable, str(SCRIPT), "mcp"], input="\n".join(messages) + "\n", text=True, capture_output=True, env=env)
        self.assertEqual(process.returncode, 0, process.stderr)
        replies = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(len(replies), 4)
        self.assertEqual(replies[0]["error"]["code"], -32700)
        self.assertEqual(replies[1]["result"]["protocolVersion"], "2025-06-18")
        self.assertIn("accountStatus", replies[2]["result"]["tools"][0]["inputSchema"]["properties"]["query"]["enum"])
        self.assertTrue(replies[3]["result"]["isError"])
        self.assertIn("configure", replies[3]["result"]["content"][0]["text"])

    def test_tool_call_returns_masked_actual_data(self):
        with patch.object(parler, "safe_query", return_value={"accountStatus": {"healthy": False, "errorCount": 2}}) as query:
            reply = parler.handle_rpc({"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "parler_usage", "arguments": {"query": "accountStatus", "error_page": 2}}})
        query.assert_called_once_with("accountStatus", {"error_page": 2})
        self.assertFalse(reply["result"]["isError"])
        self.assertEqual(json.loads(reply["result"]["content"][0]["text"])["accountStatus"]["errorCount"], 2)

    def test_invalid_params_dont_crash_server(self):
        reply = parler.handle_rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": [1]})
        self.assertEqual(reply["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
