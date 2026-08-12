import importlib.util
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib import pagerduty_client as client  # noqa: E402


class Response:
    def __init__(self, status_code=200, value=None, content=b"json"):
        self.status_code = status_code
        self._value = {} if value is None else value
        self.content = content

    def json(self):
        if isinstance(self._value, Exception):
            raise self._value
        return self._value


class MetadataContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.targets = {}
        for path in sorted((ROOT / "actions").glob("*.yaml")):
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
            cls.targets[value["ref"].removeprefix("pagerduty.")] = value

    def test_exactly_65_one_to_one_action_definitions(self):
        self.assertEqual(65, len(self.targets))

    def test_names_match_supported_client_dispatch(self):
        expected = set(client.OPERATIONS) | {"incident_create_events_v1"}
        self.assertEqual(expected, set(self.targets))

    def test_universal_attune_contract(self):
        for name, action in self.targets.items():
            with self.subTest(action=name):
                self.assertEqual(f"pagerduty.{name}", action["ref"])
                self.assertEqual("python", action["runner_type"])
                self.assertEqual(">=3.10", action["runtime_version"])
                self.assertEqual("pagerduty_action.py", action["entry_point"])
                self.assertEqual("stdin", action["parameter_delivery"])
                self.assertEqual("json", action["parameter_format"])
                self.assertEqual("json", action["output_format"])
                self.assertEqual(["standard"], action["default_execution_permission_set_refs"])
                self.assertEqual({"operation", "result"}, set(action["output"]))
                self.assertEqual("string", action["output"]["operation"]["type"])
                self.assertEqual("any", action["output"]["result"]["type"])
                credential = action["parameters"]["credential_key"]
                self.assertEqual("pagerduty.credentials", credential["default"])
                self.assertTrue(credential["required"])

    def test_schemas_are_flat_and_hide_source_dispatch_fields(self):
        for name, action in self.targets.items():
            with self.subTest(action=name):
                self.assertNotIn("entity", action["parameters"])
                self.assertNotIn("method", action["parameters"])
                for parameter, definition in action["parameters"].items():
                    self.assertIsInstance(parameter, str)
                    self.assertIsInstance(definition, dict)
                    self.assertIsInstance(definition.get("type"), str)

    def test_representative_required_defaults_and_enums(self):
        incident_find = self.targets["incident_find"]["parameters"]
        self.assertEqual(25, incident_find["maximum"]["default"])
        self.assertEqual(["all"], incident_find["date_range"]["enum"])
        snooze = self.targets["incident_snooze"]["parameters"]
        self.assertTrue(snooze["entity_id"]["required"])
        self.assertEqual(900, snooze["duration"]["default"])
        service = self.targets["service_create_simple"]["parameters"]
        self.assertEqual("service", service["type"]["default"])
        self.assertEqual(["create_incidents", "create_alerts_and_incidents"], service["alert_creation"]["enum"])
        contact = self.targets["user_create_contact_method_simple"]["parameters"]
        self.assertTrue(contact["address"]["required"])
        self.assertIn("sms_contact_method", contact["type"]["enum"])

    def test_only_team_remove_user_is_disabled(self):
        disabled = {name for name, value in self.targets.items() if not value["enabled"]}
        self.assertEqual({"team_remove_user"}, disabled)

    def test_service_key_is_secret_and_has_no_template_default(self):
        definition = self.targets["incident_create_events_v1"]["parameters"]["service_key"]
        self.assertTrue(definition["secret"])
        self.assertNotIn("default", definition)

    def test_nested_raw_data_constraints_are_retained(self):
        escalation = self.targets["escalation_policy_create"]["parameters"]["data"]
        self.assertTrue(escalation["required"])
        self.assertEqual("string", escalation["properties"]["name"]["type"])
        self.assertEqual("array", escalation["properties"]["escalation_rules"]["type"])
        targets = escalation["properties"]["escalation_rules"]["items"]["properties"]["targets"]
        self.assertEqual(["id", "type"], targets["items"]["required"])
        service = self.targets["service_create"]["parameters"]["data"]
        scheduled = service["properties"]["scheduled_actions"]["items"]
        self.assertEqual(["type", "to_urgency", "at"], scheduled["required"])

    def test_license_is_upstream_apache_text(self):
        digest = hashlib.sha256((ROOT / "LICENSE").read_bytes()).hexdigest()
        self.assertEqual("b40930bbcf80744c86c46a12bc9da056641d722716c378f5659b9e555ef833e1", digest)

    def test_readme_has_complete_matrix(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for name in self.targets:
            self.assertIn(f"`pagerduty.{name}`", text)
        for fidelity in ("| exact |", "| adapted |", "| partial |", "| manual |"):
            self.assertIn(fidelity, text)
        for heading in ("Assumptions and setup", "Source inventory", "Conversion matrix", "Semantics gaps", "Usage", "Runtime and testing"):
            self.assertIn(f"## {heading}", text)


class ClientUnitTests(unittest.TestCase):
    def test_operation_table_has_expected_methods_and_placeholders(self):
        self.assertEqual(64, len(client.OPERATIONS))
        self.assertEqual("POST", client.OPERATIONS["service_create"].method)
        self.assertEqual("/users/{entity_id}/contact_methods/{resource_id}", client.OPERATIONS["user_get_contact_method"].path)
        self.assertTrue(client.OPERATIONS["incident_find"].paginated)
        self.assertTrue(client.OPERATIONS["incident_resolve"].needs_from)

    def test_settings_validation_and_normalization(self):
        self.assertEqual(
            ("token", "https://api.example.invalid", 12.0),
            client._settings({"api_key": "token", "api_base_url": "https://api.example.invalid/", "timeout_seconds": 12}),
        )
        invalid = [
            {},
            {"api_token": "x", "api_base_url": "http://insecure.invalid"},
            {"api_token": "x", "timeout_seconds": True},
            {"api_token": "x", "timeout_seconds": 301},
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(client.PagerDutyPackError):
                client._settings(value)

    def test_fetch_key_accepts_object_and_json_string(self):
        class Parsed:
            pass

        fake_attune = types.ModuleType("attune")
        fake_attune.context = types.SimpleNamespace(client=object())
        fake_secrets = types.ModuleType("attune.api_client.api.secrets")
        for key_value in ({"api_token": "x"}, '{"api_token":"x"}'):
            parsed = Parsed()
            parsed.data = types.SimpleNamespace(value=key_value)
            fake_secrets.get_key = types.SimpleNamespace(
                sync_detailed=mock.Mock(return_value=types.SimpleNamespace(status_code=200, parsed=parsed))
            )
            modules = {
                "attune": fake_attune,
                "attune.api_client": types.ModuleType("attune.api_client"),
                "attune.api_client.api": types.ModuleType("attune.api_client.api"),
                "attune.api_client.api.secrets": fake_secrets,
            }
            with self.subTest(value=key_value), mock.patch.dict(sys.modules, modules):
                self.assertEqual({"api_token": "x"}, client._fetch_key("pagerduty.credentials"))

    def test_fetch_key_maps_lookup_failures_safely(self):
        fake_attune = types.ModuleType("attune")
        fake_attune.context = types.SimpleNamespace(client=object())
        fake_secrets = types.ModuleType("attune.api_client.api.secrets")
        fake_secrets.get_key = types.SimpleNamespace(
            sync_detailed=mock.Mock(return_value=types.SimpleNamespace(status_code=404, parsed=None))
        )
        modules = {
            "attune": fake_attune,
            "attune.api_client": types.ModuleType("attune.api_client"),
            "attune.api_client.api": types.ModuleType("attune.api_client.api"),
            "attune.api_client.api.secrets": fake_secrets,
        }
        with mock.patch.dict(sys.modules, modules), self.assertRaisesRegex(client.PagerDutyPackError, "not found"):
            client._fetch_key("missing")

    @mock.patch("requests.request")
    def test_rest_get_builds_auth_path_and_array_query(self, request):
        request.return_value = Response(value={"integration": {"id": "PI"}})
        result = client._rest_request(
            "integration_get",
            {"entity_id": "PS", "resource_id": "PI", "include": ["services"]},
            {"api_token": "secret", "api_base_url": "https://api.example.invalid"},
        )
        self.assertEqual({"id": "PI"}, result)
        args, kwargs = request.call_args
        self.assertEqual(("GET", "https://api.example.invalid/services/PS/integrations/PI"), args[:2])
        self.assertEqual({"include[]": ["services"]}, kwargs["params"])
        self.assertEqual("Token token=secret", kwargs["headers"]["Authorization"])
        self.assertIsNone(kwargs["json"])

    @mock.patch("requests.request")
    def test_rest_create_shapes_simple_body_and_from_header(self, request):
        request.return_value = Response(value={"incident": {"id": "P1"}})
        result = client._rest_request(
            "incident_create_rest_v2_simple",
            {"from_email": "actor@example.invalid", "title": "Test", "service_id": "PS", "details": "Details"},
            {"api_token": "secret"},
        )
        self.assertEqual({"id": "P1"}, result)
        kwargs = request.call_args.kwargs
        self.assertEqual("actor@example.invalid", kwargs["headers"]["From"])
        self.assertEqual("incident", kwargs["json"]["incident"]["type"])
        self.assertEqual("Details", kwargs["json"]["incident"]["body"]["details"])

    @mock.patch("requests.request")
    def test_rest_incident_mutation_bodies(self, request):
        request.return_value = Response(value={"incident": {"id": "P1"}})
        cases = {
            "incident_acknowledge": ({}, {"incident": {"type": "incident_reference", "status": "acknowledged"}}),
            "incident_resolve": ({}, {"incident": {"type": "incident_reference", "status": "resolved"}}),
            "incident_reassign": ({"user_ids": ["U1"]}, {"incident": {"type": "incident_reference", "assignments": [{"assignee": {"id": "U1", "type": "user_reference"}}]}}),
            "incident_snooze": ({"duration": 60}, {"duration": 60}),
            "incident_merge": ({"source_incidents": ["I2"]}, {"source_incidents": [{"id": "I2", "type": "incident_reference"}]}),
        }
        for operation, (extra, expected) in cases.items():
            with self.subTest(operation=operation):
                params = {"entity_id": "P1", "from_email": "actor@example.invalid", **extra}
                client._rest_request(operation, params, {"api_token": "secret"})
                self.assertEqual(expected, request.call_args.kwargs["json"])

    @mock.patch("requests.request")
    def test_pagination_honors_maximum_across_pages(self, request):
        request.side_effect = [
            Response(value={"incidents": [{"id": "1"}, {"id": "2"}], "more": True}),
            Response(value={"incidents": [{"id": "3"}, {"id": "4"}], "more": False}),
        ]
        result = client._rest_request("incident_find", {"maximum": 3, "statuses": ["triggered"]}, {"api_token": "secret"})
        self.assertEqual([{"id": "1"}, {"id": "2"}, {"id": "3"}], result)
        self.assertEqual(2, request.call_count)
        self.assertEqual({"statuses[]": ["triggered"], "limit": 1, "offset": 2}, request.call_args.kwargs["params"])

    @mock.patch("requests.request")
    def test_delete_returns_normalized_success_result(self, request):
        request.return_value = Response(status_code=204, content=b"")
        self.assertEqual({"deleted": True}, client._rest_request("user_delete", {"entity_id": "U1"}, {"api_token": "secret"}))

    @mock.patch("requests.request")
    def test_bodyless_team_put_sends_no_payload(self, request):
        request.return_value = Response(status_code=204, content=b"")
        result = client._rest_request("team_add_user", {"entity_id": "T1", "user": "U1"}, {"api_token": "secret"})
        self.assertEqual({"success": True}, result)
        self.assertIsNone(request.call_args.kwargs["json"])

    @mock.patch("requests.request")
    def test_schedule_create_preserves_overflow_query(self, request):
        request.return_value = Response(value={"schedule": {"id": "S1"}})
        client._rest_request("schedule_create", {"data": {"name": "Primary"}, "overflow": True, "from_email": "actor@example.invalid"}, {"api_token": "secret"})
        self.assertEqual({"overflow": True}, request.call_args.kwargs["params"])

    def test_json_response_rejects_http_invalid_json_and_non_object(self):
        values = [
            Response(status_code=500, value={"token": "must not surface"}),
            Response(value=ValueError("bad")),
            Response(value=[1, 2]),
        ]
        for response in values:
            with self.subTest(status=response.status_code), self.assertRaises(client.PagerDutyPackError):
                client._json_response(response)

    @mock.patch("requests.post")
    def test_events_v1_uses_config_key_and_optional_fields(self, post):
        post.return_value = Response(value={"status": "success", "incident_key": "K1"})
        result = client._create_event(
            {"description": "Test", "details": {"safe": True}, "client": "Attune"},
            {"service_key": "secret", "events_v1_url": "https://events.example.invalid/v1", "timeout_seconds": 8},
        )
        self.assertEqual("success", result["status"])
        self.assertEqual("secret", post.call_args.kwargs["json"]["service_key"])
        self.assertEqual({"safe": True}, post.call_args.kwargs["json"]["details"])
        self.assertEqual(8.0, post.call_args.kwargs["timeout"])

    def test_execute_action_uses_default_credential_and_dispatches(self):
        with mock.patch.object(client, "_fetch_key", return_value={"api_token": "secret"}) as fetch, mock.patch.object(client, "_rest_request", return_value={"id": "U1"}) as rest:
            self.assertEqual({"id": "U1"}, client.execute_action("user_get", {"entity_id": "U1"}))
        fetch.assert_called_once_with("pagerduty.credentials")
        rest.assert_called_once_with("user_get", {"entity_id": "U1"}, {"api_token": "secret"})

    def test_validation_rejects_missing_fields_and_bad_collections(self):
        cases = [
            ("integration_get", {"entity_id": "S1"}),
            ("incident_reassign", {"entity_id": "I1", "from_email": "a@example.invalid", "user_ids": []}),
            ("incident_snooze", {"entity_id": "I1", "from_email": "a@example.invalid", "duration": True}),
        ]
        with mock.patch("requests.request"):
            for operation, params in cases:
                with self.subTest(operation=operation), self.assertRaises(client.PagerDutyPackError):
                    client._rest_request(operation, params, {"api_token": "secret"})


class EntryPointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("pagerduty_action_test", ROOT / "actions" / "pagerduty_action.py")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def run_main(self, stdin, action="pagerduty.user_get"):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.dict(os.environ, {"ATTUNE_ACTION": action}, clear=False), mock.patch("sys.stdin", io.StringIO(stdin)), mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
            code = self.module.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_success_emits_only_declared_json(self):
        with mock.patch.object(self.module, "execute_action", return_value={"id": "U1"}) as execute:
            code, stdout, stderr = self.run_main('{"entity_id":"U1"}')
        self.assertEqual(0, code)
        self.assertEqual({"operation": "user_get", "result": {"id": "U1"}}, json.loads(stdout))
        self.assertEqual("", stderr)
        execute.assert_called_once_with("user_get", {"entity_id": "U1"})

    def test_invalid_input_fails_without_stdout(self):
        code, stdout, stderr = self.run_main("[]")
        self.assertEqual(1, code)
        self.assertEqual("", stdout)
        self.assertIn("action parameters must be a JSON object", stderr)

    def test_unexpected_remote_error_redacts_message(self):
        with mock.patch.object(self.module, "execute_action", side_effect=RuntimeError("secret response body")):
            code, stdout, stderr = self.run_main("{}")
        self.assertEqual(1, code)
        self.assertEqual("", stdout)
        self.assertIn("RuntimeError", stderr)
        self.assertNotIn("secret response body", stderr)


if __name__ == "__main__":
    unittest.main()
