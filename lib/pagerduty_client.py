"""Explicit PagerDuty operations adapted from stackstorm-pagerduty 2.0.0."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple


class PagerDutyPackError(RuntimeError):
    """Safe operator-facing PagerDuty pack error."""


@dataclass(frozen=True)
class Operation:
    method: str
    path: str
    result_key: Optional[str] = None
    body_key: Optional[str] = None
    paginated: bool = False
    needs_from: bool = False


def _op(method: str, path: str, result_key: Optional[str] = None, body_key: Optional[str] = None, *, paginated: bool = False, needs_from: bool = False) -> Operation:
    return Operation(method, path, result_key, body_key, paginated, needs_from)


OPERATIONS = {
    "escalation_policy_create": _op("POST", "/escalation_policies", "escalation_policy", "escalation_policy", needs_from=True),
    "escalation_policy_delete": _op("DELETE", "/escalation_policies/{entity_id}"),
    "escalation_policy_find": _op("GET", "/escalation_policies", "escalation_policies", paginated=True),
    "escalation_policy_find_services": _op("GET", "/escalation_policies/{entity_id}/services", "services", paginated=True),
    "escalation_policy_get": _op("GET", "/escalation_policies/{entity_id}", "escalation_policy"),
    "incident_acknowledge": _op("PUT", "/incidents/{entity_id}", "incident", "incident", needs_from=True),
    "incident_create_rest_v2": _op("POST", "/incidents", "incident", "incident", needs_from=True),
    "incident_create_rest_v2_simple": _op("POST", "/incidents", "incident", "incident", needs_from=True),
    "incident_create_note": _op("POST", "/incidents/{entity_id}/notes", "note", "note", needs_from=True),
    "incident_find": _op("GET", "/incidents", "incidents", paginated=True),
    "incident_find_alerts": _op("GET", "/incidents/{entity_id}/alerts", "alerts", paginated=True),
    "incident_find_log_entries": _op("GET", "/incidents/{entity_id}/log_entries", "log_entries", paginated=True),
    "incident_find_notes": _op("GET", "/incidents/{entity_id}/notes", "notes", paginated=True),
    "incident_get": _op("GET", "/incidents/{entity_id}", "incident"),
    "incident_merge": _op("PUT", "/incidents/{entity_id}/merge", "incident", None, needs_from=True),
    "incident_reassign": _op("PUT", "/incidents/{entity_id}", "incident", "incident", needs_from=True),
    "incident_resolve": _op("PUT", "/incidents/{entity_id}", "incident", "incident", needs_from=True),
    "incident_snooze": _op("POST", "/incidents/{entity_id}/snooze", "incident", None, needs_from=True),
    "integration_get": _op("GET", "/services/{entity_id}/integrations/{resource_id}", "integration"),
    "log_entry_find": _op("GET", "/log_entries", "log_entries", paginated=True),
    "log_entry_get": _op("GET", "/log_entries/{entity_id}", "log_entry"),
    "maintenance_window_create": _op("POST", "/maintenance_windows", "maintenance_window", "maintenance_window", needs_from=True),
    "maintenance_window_create_simple": _op("POST", "/maintenance_windows", "maintenance_window", "maintenance_window", needs_from=True),
    "maintenance_window_delete": _op("DELETE", "/maintenance_windows/{entity_id}"),
    "maintenance_window_find": _op("GET", "/maintenance_windows", "maintenance_windows", paginated=True),
    "maintenance_window_get": _op("GET", "/maintenance_windows/{entity_id}", "maintenance_window"),
    "notification_find": _op("GET", "/notifications", "notifications", paginated=True),
    "on_call_find": _op("GET", "/oncalls", "oncalls", paginated=True),
    "schedule_create": _op("POST", "/schedules", "schedule", "schedule", needs_from=True),
    "schedule_delete": _op("DELETE", "/schedules/{entity_id}"),
    "schedule_find": _op("GET", "/schedules", "schedules", paginated=True),
    "schedule_get": _op("GET", "/schedules/{entity_id}", "schedule"),
    "schedule_get_on_call": _op("GET", "/schedules/{entity_id}/users", "users"),
    "service_create": _op("POST", "/services", "service", "service", needs_from=True),
    "service_create_simple": _op("POST", "/services", "service", "service", needs_from=True),
    "service_delete": _op("DELETE", "/services/{entity_id}"),
    "service_find": _op("GET", "/services", "services", paginated=True),
    "service_find_integrations": _op("GET", "/services/{entity_id}/integrations", "integrations", paginated=True),
    "service_get": _op("GET", "/services/{entity_id}", "service"),
    "service_get_integrations": _op("GET", "/services/{entity_id}/integrations/{resource_id}", "integration"),
    "team_add_escalation_policy": _op("PUT", "/teams/{entity_id}/escalation_policies/{escalation_policy}"),
    "team_add_user": _op("PUT", "/teams/{entity_id}/users/{user}"),
    "team_create": _op("POST", "/teams", "team", "team"),
    "team_create_simple": _op("POST", "/teams", "team", "team"),
    "team_delete": _op("DELETE", "/teams/{entity_id}"),
    "team_find": _op("GET", "/teams", "teams", paginated=True),
    "team_get": _op("GET", "/teams/{entity_id}", "team"),
    "team_remove_escalation_policy": _op("DELETE", "/teams/{entity_id}/escalation_policies/{escalation_policy}"),
    "team_remove_user": _op("DELETE", "/teams/{entity_id}/users/{user}"),
    "user_create": _op("POST", "/users", "user", "user", needs_from=True),
    "user_create_simple": _op("POST", "/users", "user", "user", needs_from=True),
    "user_create_contact_method": _op("POST", "/users/{entity_id}/contact_methods", "contact_method", "contact_method"),
    "user_create_contact_method_simple": _op("POST", "/users/{entity_id}/contact_methods", "contact_method", "contact_method"),
    "user_create_notification_rule": _op("POST", "/users/{entity_id}/notification_rules", "notification_rule", "notification_rule"),
    "user_create_notification_rule_simple": _op("POST", "/users/{entity_id}/notification_rules", "notification_rule", "notification_rule"),
    "user_delete": _op("DELETE", "/users/{entity_id}"),
    "user_delete_contact_method": _op("DELETE", "/users/{entity_id}/contact_methods/{resource_id}"),
    "user_delete_notification_rule": _op("DELETE", "/users/{entity_id}/notification_rules/{resource_id}"),
    "user_find": _op("GET", "/users", "users", paginated=True),
    "user_find_contact_methods": _op("GET", "/users/{entity_id}/contact_methods", "contact_methods"),
    "user_find_notification_rules": _op("GET", "/users/{entity_id}/notification_rules", "notification_rules"),
    "user_get": _op("GET", "/users/{entity_id}", "user"),
    "user_get_contact_method": _op("GET", "/users/{entity_id}/contact_methods/{resource_id}", "contact_method"),
    "user_get_notification_rule": _op("GET", "/users/{entity_id}/notification_rules/{resource_id}", "notification_rule"),
}


def _fetch_key(ref: str) -> Dict[str, Any]:
    if not isinstance(ref, str) or not ref:
        raise PagerDutyPackError("credential_key must be a non-empty string")
    try:
        import attune
        from attune.api_client.api.secrets import get_key
    except ImportError as exc:
        raise PagerDutyPackError("attune-sdk is required to resolve credential_key") from exc
    try:
        response = get_key.sync_detailed(ref, client=attune.context.client, decrypt=True)
    except Exception as exc:
        raise PagerDutyPackError(f"unable to read credential Key {ref!r}") from exc
    status = int(response.status_code)
    if status == 404:
        raise PagerDutyPackError(f"credential Key {ref!r} was not found")
    if status >= 400 or not response.parsed:
        raise PagerDutyPackError(f"credential Key lookup failed with status {status}")
    value = response.parsed.data.value
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise PagerDutyPackError("credential Key must contain a JSON object") from exc
    if not isinstance(value, dict):
        raise PagerDutyPackError("credential Key must contain an object")
    return value


def _required_string(params: Mapping[str, Any], name: str) -> str:
    value = params.get(name)
    if not isinstance(value, str) or not value:
        raise PagerDutyPackError(f"{name} must be a non-empty string")
    return value


def _settings(config: Mapping[str, Any]) -> Tuple[str, str, float]:
    token = config.get("api_token") or config.get("api_key")
    if not isinstance(token, str) or not token:
        raise PagerDutyPackError("credential Key requires api_token")
    base_url = config.get("api_base_url", "https://api.pagerduty.com")
    if not isinstance(base_url, str) or not base_url.startswith("https://"):
        raise PagerDutyPackError("api_base_url must be an HTTPS URL")
    timeout = config.get("timeout_seconds", 30)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise PagerDutyPackError("timeout_seconds must be a number")
    timeout = float(timeout)
    if not math.isfinite(timeout) or timeout < 1 or timeout > 300:
        raise PagerDutyPackError("timeout_seconds must be between 1 and 300")
    return token, base_url.rstrip("/"), timeout


def _json_response(response: Any) -> Dict[str, Any]:
    if response.status_code < 200 or response.status_code >= 300:
        raise PagerDutyPackError(f"PagerDuty request failed with HTTP status {response.status_code}")
    if response.status_code == 204 or not response.content:
        return {}
    try:
        value = response.json()
    except (ValueError, TypeError) as exc:
        raise PagerDutyPackError("PagerDuty returned an invalid JSON response") from exc
    if not isinstance(value, dict):
        raise PagerDutyPackError("PagerDuty returned a non-object JSON response")
    return value


def _query(params: Mapping[str, Any]) -> Dict[str, Any]:
    excluded = {"credential_key", "data", "entity_id", "resource_id", "from_email", "service_key", "description", "details", "client", "client_url", "incident_key", "title", "service_id", "content", "source_incidents", "user_ids", "duration", "name", "type", "email", "address", "label", "contact_method_id", "contact_method_type", "start_delay_in_minutes", "escalation_policy", "user", "start_time", "end_time", "auto_resolve_timeout", "acknowledgement_timeout", "status", "alert_creation", "color", "role", "job_title", "overflow"}
    query: Dict[str, Any] = {}
    for key, value in params.items():
        if key in excluded or value is None:
            continue
        query[f"{key}[]" if isinstance(value, list) else key] = value
    return query


def _simple_data(operation: str, params: Mapping[str, Any]) -> Dict[str, Any]:
    if operation == "incident_create_rest_v2_simple":
        body: Dict[str, Any] = {"type": "incident", "title": _required_string(params, "title"), "service": {"id": _required_string(params, "service_id"), "type": "service_reference"}}
        if params.get("details") is not None:
            body["body"] = {"type": "incident_body", "details": params["details"]}
        return body
    if operation == "maintenance_window_create_simple":
        body = {"type": "maintenance_window", "start_time": _required_string(params, "start_time"), "end_time": _required_string(params, "end_time"), "services": [{"id": _required_string(params, "service_id"), "type": "service_reference"}]}
        if params.get("description") is not None:
            body["description"] = params["description"]
        return body
    if operation == "service_create_simple":
        return {"type": params.get("type", "service"), "name": _required_string(params, "name"), "description": params.get("description"), "auto_resolve_timeout": params.get("auto_resolve_timeout", 14400), "acknowledgement_timeout": params.get("acknowledgement_timeout", 1800), "status": params.get("status", "active"), "escalation_policy": {"id": _required_string(params, "escalation_policy_id"), "type": "escalation_policy_reference"}, "alert_creation": params.get("alert_creation", "create_alerts_and_incidents")}
    if operation == "team_create_simple":
        return {key: value for key, value in {"type": params.get("type", "team"), "name": _required_string(params, "name"), "description": params.get("description")}.items() if value is not None}
    if operation == "user_create_simple":
        return {key: value for key, value in {"type": params.get("type", "user"), "name": _required_string(params, "name"), "email": _required_string(params, "email"), "time_zone": params.get("time_zone", "America/Los_Angeles"), "color": params.get("color", "grey20"), "role": params.get("role", "user"), "description": params.get("description"), "job_title": params.get("job_title")}.items() if value is not None}
    if operation == "user_create_contact_method_simple":
        return {"type": _required_string(params, "type"), "label": _required_string(params, "label"), "address": _required_string(params, "address")}
    if operation == "user_create_notification_rule_simple":
        return {"type": "assignment_notification_rule", "start_delay_in_minutes": params.get("start_delay_in_minutes", 0), "contact_method": {"id": _required_string(params, "contact_method_id"), "type": _required_string(params, "contact_method_type")}}
    data = params.get("data")
    if not isinstance(data, dict):
        raise PagerDutyPackError("data must be an object")
    return dict(data)


def _body(operation: str, spec: Operation, params: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    if spec.method in {"GET", "DELETE"}:
        return None
    if operation in {"team_add_escalation_policy", "team_add_user"}:
        return None
    if operation == "incident_acknowledge":
        data = {"type": "incident_reference", "status": "acknowledged"}
    elif operation == "incident_resolve":
        data = {"type": "incident_reference", "status": "resolved"}
    elif operation == "incident_reassign":
        users = params.get("user_ids")
        if not isinstance(users, list) or not users:
            raise PagerDutyPackError("user_ids must be a non-empty array")
        data = {"type": "incident_reference", "assignments": [{"assignee": {"id": item, "type": "user_reference"}} for item in users]}
    elif operation == "incident_create_note":
        data = {"content": _required_string(params, "content")}
    elif operation == "incident_merge":
        incidents = params.get("source_incidents")
        if not isinstance(incidents, list) or not incidents:
            raise PagerDutyPackError("source_incidents must be a non-empty array")
        if not all(isinstance(item, str) and item for item in incidents):
            raise PagerDutyPackError("source_incidents must contain non-empty strings")
        return {"source_incidents": [{"id": item, "type": "incident_reference"} for item in incidents]}
    elif operation == "incident_snooze":
        duration = params.get("duration", 900)
        if isinstance(duration, bool) or not isinstance(duration, int) or duration < 1:
            raise PagerDutyPackError("duration must be a positive integer")
        return {"duration": duration}
    else:
        data = _simple_data(operation, params)
    return {spec.body_key: data} if spec.body_key else data


def _rest_request(operation: str, params: Mapping[str, Any], config: Mapping[str, Any]) -> Any:
    import requests

    spec = OPERATIONS[operation]
    token, base_url, timeout = _settings(config)
    values = {name: _required_string(params, name) for name in ("entity_id", "resource_id", "escalation_policy", "user") if "{" + name + "}" in spec.path}
    url = base_url + spec.path.format(**values)
    headers = {"Authorization": f"Token token={token}", "Accept": "application/vnd.pagerduty+json;version=2", "Content-Type": "application/json"}
    if spec.needs_from:
        from_email = params.get("from_email") or config.get("from_email")
        if not isinstance(from_email, str) or not from_email:
            raise PagerDutyPackError("from_email is required")
        headers["From"] = from_email
    query = _query(params) if spec.method == "GET" else {}
    if operation == "schedule_create":
        query["overflow"] = params.get("overflow", False)
    maximum = query.pop("maximum", 25) if spec.paginated else None
    if maximum is not None and (isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1):
        raise PagerDutyPackError("maximum must be a positive integer")
    collected = []
    offset = 0
    while True:
        page_query = dict(query)
        if spec.paginated:
            page_query.update({"limit": min(100, maximum - len(collected)), "offset": offset})
        try:
            response = requests.request(spec.method, url, headers=headers, params=page_query or None, json=_body(operation, spec, params), timeout=timeout)
        except requests.Timeout as exc:
            raise PagerDutyPackError("PagerDuty request timed out") from exc
        except requests.RequestException as exc:
            raise PagerDutyPackError("PagerDuty request failed") from exc
        value = _json_response(response)
        if not spec.paginated:
            if spec.method == "DELETE":
                return {"deleted": True}
            return value.get(spec.result_key, value) if spec.result_key else value or {"success": True}
        page = value.get(spec.result_key, [])
        if not isinstance(page, list):
            raise PagerDutyPackError("PagerDuty pagination response has an invalid result list")
        collected.extend(page[: maximum - len(collected)])
        if len(collected) >= maximum or not value.get("more") or not page:
            return collected
        offset += len(page)


def _create_event(params: Mapping[str, Any], config: Mapping[str, Any]) -> Dict[str, Any]:
    import requests

    service_key = params.get("service_key") or config.get("service_key")
    if not isinstance(service_key, str) or not service_key:
        raise PagerDutyPackError("credential Key requires service_key for Events API v1")
    timeout_value = config.get("timeout_seconds", 30)
    if isinstance(timeout_value, bool) or not isinstance(timeout_value, (int, float)) or not math.isfinite(float(timeout_value)) or not 1 <= float(timeout_value) <= 300:
        raise PagerDutyPackError("timeout_seconds must be between 1 and 300")
    url = config.get("events_v1_url", "https://events.pagerduty.com/generic/2010-04-15/create_event.json")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise PagerDutyPackError("events_v1_url must be an HTTPS URL")
    payload = {"service_key": service_key, "event_type": "trigger", "description": _required_string(params, "description")}
    for name in ("details", "client", "client_url", "incident_key"):
        if params.get(name) is not None:
            payload[name] = params[name]
    try:
        response = requests.post(url, json=payload, timeout=float(timeout_value))
    except requests.Timeout as exc:
        raise PagerDutyPackError("PagerDuty Events request timed out") from exc
    except requests.RequestException as exc:
        raise PagerDutyPackError("PagerDuty Events request failed") from exc
    return _json_response(response)


def execute_action(operation: str, params: Mapping[str, Any]) -> Any:
    config = _fetch_key(str(params.get("credential_key", "pagerduty.credentials")))
    if operation == "incident_create_events_v1":
        return _create_event(params, config)
    if operation not in OPERATIONS:
        raise PagerDutyPackError(f"unsupported PagerDuty operation {operation!r}")
    return _rest_request(operation, params, config)
