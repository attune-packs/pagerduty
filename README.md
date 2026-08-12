# PagerDuty

Attune actions for PagerDuty REST API v2 and the legacy Events API v1, adapted from
`StackStorm-Exchange/stackstorm-pagerduty` 2.0.0 at commit
`4555dfc3f5fdbc1486503149c86392a1d5bf24b8`.

## Assumptions and setup

- Python 3.10 or newer and the dependencies in `requirements.txt` are available to the worker.
- PagerDuty endpoints are reachable from the selected worker.
- Create an Attune Key named `pagerduty.credentials`, or pass another ref as `credential_key`.
- The Key value is a JSON object containing `api_token`; it may also contain `from_email`, `service_key`,
  `api_base_url`, `events_v1_url`, and `timeout_seconds`.
- `api_base_url` and `events_v1_url` must use HTTPS. `timeout_seconds` must be from 1 through 300.
- Actions receive a flat JSON object on stdin and use the reserved `standard` permission to read the scoped Key.
- No credential values belong in action parameters, examples, logs, or source control. The optional direct
  `service_key` parameter is marked secret.

Example Key value (replace placeholders in Attune, not in this repository):

```json
{
  "api_token": "REDACTED_API_TOKEN",
  "from_email": "automation@example.invalid",
  "service_key": "REDACTED_EVENTS_V1_KEY",
  "timeout_seconds": 30
}
```

## Source inventory

The source contains a manifest and config schema, 65 Python action definitions, four ChatOps aliases, one shared
dispatcher/client implementation, documentation, and Apache-2.0 licensing. It contains no sensors, triggers,
rules, workflows, queues, schedules, or tests.
Each source action maps one-to-one to an Attune action. Dots are translated to underscores because the shared
client dispatches on the final Attune action-ref segment. Source `entity` and `method` fields and immutable
simple-action `data` templates were runner internals and are not exposed as user parameters.

## Conversion matrix

Fidelity is `adapted` for REST actions: API intent and user inputs are retained, while StackStorm runner/config
delivery is replaced by Attune stdin JSON and Key lookup. The legacy Events v1 action is `partial` because the
obsolete endpoint is retained rather than silently changing to Events API v2. `team.remove_user` remains disabled.

| Source | Attune target | Fidelity | Important differences | Follow-up |
|---|---|---|---|---|
| Manifest, config schema, and example config | `pack.yaml` and `pagerduty.credentials` Key | adapted | Canonical Attune metadata; secrets moved from config to a scoped encrypted Key; unsafe sample values omitted | Create the Key after installation |
| `actions/action.py` and `actions/lib/base.py` | `actions/pagerduty_action.py` and `lib/pagerduty_client.py` | adapted | Explicit stateless HTTP operations replace obsolete `pypd` globals; bounded timeout; no retries; safe errors | Integration-test against the target PagerDuty account |
| 64 REST action definitions | 64 action YAML files listed below | adapted | Dotted refs become underscore refs; output uses a stable envelope; schemas correct malformed source object definitions | Validate account-specific API permissions and current PagerDuty fields |
| `incident.create.events_v1` | `pagerduty.incident_create_events_v1` | partial | Legacy Events v1 is retained; it is not equivalent to Events API v2 and remains trigger-only | Migrate callers to a separately designed Events v2 action |
| Four StackStorm ChatOps aliases | README invocation examples only | manual | Attune has no direct StackStorm alias resource; natural-language parsing and response templates are not reproduced | Implement aliases in the selected chat integration if required |
| Disabled `team.remove_user` | Disabled `pagerduty.team_remove_user` | adapted | Disabled state is preserved even though the direct REST implementation avoids the historical `pypd` typo | Enable only after an integration test and operator decision |
| Source tests | `tests/test_pack.py` | adapted | Upstream had no tests; deterministic contract and mocked HTTP tests were added | Add opt-in live tests outside the pack gate |
| Sensors, triggers, rules, workflows, queues, and schedules | None | exact | No source resources existed | Add only for new operator requirements |
| Documentation and Apache-2.0 license | `README.md` and `LICENSE` | adapted | Source attribution retained; screenshots and logo are not redistributed | Review PagerDuty trademark assets separately if added |
| Source CI/release metadata | None | manual | Publication automation is repository-specific | Add target CI when publishing |

### Escalation Policy

| Source | Attune target | State | Fidelity | Important difference |
|---|---|---|---|---|
| `escalation_policy.create` | `pagerduty.escalation_policy_create` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `escalation_policy.delete` | `pagerduty.escalation_policy_delete` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `escalation_policy.find` | `pagerduty.escalation_policy_find` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `escalation_policy.find_services` | `pagerduty.escalation_policy_find_services` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `escalation_policy.get` | `pagerduty.escalation_policy_get` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |

### Incident

| Source | Attune target | State | Fidelity | Important difference |
|---|---|---|---|---|
| `incident.acknowledge` | `pagerduty.incident_acknowledge` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `incident.create.events_v1` | `pagerduty.incident_create_events_v1` | enabled | partial | Legacy Events API v1 retained; not equivalent to Events API v2 |
| `incident.create.rest_v2.simple` | `pagerduty.incident_create_rest_v2_simple` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `incident.create.rest_v2` | `pagerduty.incident_create_rest_v2` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `incident.create_note` | `pagerduty.incident_create_note` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `incident.find` | `pagerduty.incident_find` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `incident.find_alerts` | `pagerduty.incident_find_alerts` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `incident.find_log_entries` | `pagerduty.incident_find_log_entries` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `incident.find_notes` | `pagerduty.incident_find_notes` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `incident.get` | `pagerduty.incident_get` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `incident.merge` | `pagerduty.incident_merge` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `incident.reassign` | `pagerduty.incident_reassign` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `incident.resolve` | `pagerduty.incident_resolve` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `incident.snooze` | `pagerduty.incident_snooze` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |

### Integration

| Source | Attune target | State | Fidelity | Important difference |
|---|---|---|---|---|
| `integration.get` | `pagerduty.integration_get` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |

### Log Entry

| Source | Attune target | State | Fidelity | Important difference |
|---|---|---|---|---|
| `log_entry.find` | `pagerduty.log_entry_find` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `log_entry.get` | `pagerduty.log_entry_get` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |

### Maintenance Window

| Source | Attune target | State | Fidelity | Important difference |
|---|---|---|---|---|
| `maintenance_window.create.simple` | `pagerduty.maintenance_window_create_simple` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `maintenance_window.create` | `pagerduty.maintenance_window_create` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `maintenance_window.delete` | `pagerduty.maintenance_window_delete` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `maintenance_window.find` | `pagerduty.maintenance_window_find` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `maintenance_window.get` | `pagerduty.maintenance_window_get` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |

### Notification

| Source | Attune target | State | Fidelity | Important difference |
|---|---|---|---|---|
| `notification.find` | `pagerduty.notification_find` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |

### On Call

| Source | Attune target | State | Fidelity | Important difference |
|---|---|---|---|---|
| `on_call.find` | `pagerduty.on_call_find` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |

### Schedule

| Source | Attune target | State | Fidelity | Important difference |
|---|---|---|---|---|
| `schedule.create` | `pagerduty.schedule_create` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `schedule.delete` | `pagerduty.schedule_delete` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `schedule.find` | `pagerduty.schedule_find` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `schedule.get` | `pagerduty.schedule_get` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `schedule.get_on_call` | `pagerduty.schedule_get_on_call` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |

### Service

| Source | Attune target | State | Fidelity | Important difference |
|---|---|---|---|---|
| `service.create.simple` | `pagerduty.service_create_simple` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `service.create` | `pagerduty.service_create` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `service.delete` | `pagerduty.service_delete` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `service.find` | `pagerduty.service_find` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `service.find_integrations` | `pagerduty.service_find_integrations` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `service.get` | `pagerduty.service_get` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `service.get_integrations` | `pagerduty.service_get_integrations` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |

### Team

| Source | Attune target | State | Fidelity | Important difference |
|---|---|---|---|---|
| `team.add_escalation_policy` | `pagerduty.team_add_escalation_policy` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `team.add_user` | `pagerduty.team_add_user` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `team.create.simple` | `pagerduty.team_create_simple` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `team.create` | `pagerduty.team_create` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `team.delete` | `pagerduty.team_delete` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `team.find` | `pagerduty.team_find` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `team.get` | `pagerduty.team_get` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `team.remove_escalation_policy` | `pagerduty.team_remove_escalation_policy` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `team.remove_user` | `pagerduty.team_remove_user` | disabled | adapted | Shared explicit HTTP client and Attune Key auth |

### User

| Source | Attune target | State | Fidelity | Important difference |
|---|---|---|---|---|
| `user.create.simple` | `pagerduty.user_create_simple` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `user.create` | `pagerduty.user_create` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `user.create_contact_method.simple` | `pagerduty.user_create_contact_method_simple` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `user.create_contact_method` | `pagerduty.user_create_contact_method` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `user.create_notification_rule.simple` | `pagerduty.user_create_notification_rule_simple` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `user.create_notification_rule` | `pagerduty.user_create_notification_rule` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `user.delete` | `pagerduty.user_delete` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `user.delete_contact_method` | `pagerduty.user_delete_contact_method` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `user.delete_notification_rule` | `pagerduty.user_delete_notification_rule` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `user.find` | `pagerduty.user_find` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `user.find_contact_methods` | `pagerduty.user_find_contact_methods` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `user.find_notification_rules` | `pagerduty.user_find_notification_rules` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `user.get` | `pagerduty.user_get` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `user.get_contact_method` | `pagerduty.user_get_contact_method` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |
| `user.get_notification_rule` | `pagerduty.user_get_notification_rule` | enabled | adapted | Shared explicit HTTP client and Attune Key auth |

## Semantics gaps

- The conversion uses explicit HTTP operations rather than `pypd`; returned values are plain decoded JSON,
  lists, or status objects rather than Python entity objects.
- Raw create actions accept and forward a `data` object. Metadata preserves useful nested source constraints,
  but PagerDuty remains authoritative for full request validation.
- Pagination is normalized to one list capped by `maximum` (default 25). The client requests pages of at most
  100 and does not expose PagerDuty pagination metadata.
- Delete operations return `{"deleted": true}` and empty successful non-delete responses return
  `{"success": true}`.
- HTTP error response bodies are deliberately not surfaced, reducing diagnostic detail to avoid leaking remote
  content. No retries are performed.
- Events API v1 is retained for source parity even though it is legacy. The action only triggers incidents.
- `team_remove_user` remains disabled for source-state parity, although the explicit client does not use the
  upstream `pypd` method that caused the original disablement.
- Source ChatOps aliases are manual mappings: the three incident mutation/query commands are represented by
  direct action usage examples, but their natural-language matching and rendered responses are not reproduced.
- Cancellation can terminate an Attune action process but cannot recall an HTTP mutation already accepted by
  PagerDuty. Mutations have no compensation, concurrency control, or automatic retry and retain PagerDuty's
  endpoint-specific idempotency behavior. Events v1 deduplicates only when `incident_key` is supplied.

## Usage

Execute with flat parameters. For example:

```bash
attune action execute pagerduty.incident_find --params-json '{"statuses":["triggered"],"maximum":10}'
attune action execute pagerduty.incident_acknowledge --params-json '{"entity_id":"PINCIDENT","from_email":"automation@example.invalid"}'
attune action execute pagerduty.incident_create_events_v1 --params-json '{"description":"Synthetic test alert"}'
```

Structured stdout has two fields: `operation` is the underscore action operation and `result` is the decoded
PagerDuty result. In workflows, consume these as `result().data.operation` and `result().data.result`.

## Runtime and testing

All actions use `runner_type: python`, `runtime_version: ">=3.10"`, the shared
`actions/pagerduty_action.py` entry point, stdin/JSON parameter delivery, and JSON output. Dependencies are
installed from the pack-root `requirements.txt` into the worker runtime environment.

Tests are deterministic `unittest` tests. They validate all 65 metadata contracts and mock Key resolution and
HTTP calls; they never contact PagerDuty or Attune:

```bash
python3 -m unittest tests/test_pack.py
attune --output json pack check .
attune pack test . --detailed
```

## Upstream And License

This is a modified adaptation of the original
[StackStorm Exchange PagerDuty pack](https://github.com/StackStorm-Exchange/stackstorm-pagerduty).
The upstream Apache License 2.0 is included in [LICENSE](LICENSE), with
attribution and source revision details in [NOTICE](NOTICE).
