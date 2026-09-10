#!/usr/bin/env python3
"""Local-first workspace tools for the Yapply agent plugin."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PLUGIN_VERSION = "0.1.0"
SCHEMA_VERSION = 1
WORKSPACE_DIR = ".yapply"
STATUSES = (
    "saved",
    "preparing",
    "ready",
    "applied",
    "interviewing",
    "offer",
    "rejected",
    "withdrawn",
)
FACT_CATEGORIES = ("experience", "project", "education", "skill", "award", "other")
REMOTE_PREFERENCES = ("any", "remote", "hybrid", "onsite")
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
FACT_ID_PATTERN = re.compile(r"^fact-[a-z0-9][a-z0-9-]*$")
COUNT_BUCKETS = ("0", "1", "2-5", "6-20", "21+")
EVENT_PROPERTIES = {
    "workspace_initialized": {"outcome"},
    "profile_validated": {"outcome", "fact_count_bucket", "error_count_bucket"},
    "application_created": {"outcome"},
    "application_validated": {"outcome", "statement_count_bucket", "error_count_bucket"},
    "application_status_changed": {"outcome", "from_status", "to_status"},
}


class YapplyError(RuntimeError):
    """Expected user-facing error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def workspace(root: Path) -> Path:
    return root.resolve() / WORKSPACE_DIR


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise YapplyError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise YapplyError(f"Invalid JSON in {path}: line {exc.lineno}, column {exc.colno}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(payload)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def require_workspace(root: Path) -> Path:
    base = workspace(root)
    if not base.is_dir():
        raise YapplyError(f"No Yapply workspace at {base}. Run 'yapply init' first.")
    return base


def profile_template() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "identity": {
            "name": "",
            "email": "",
            "phone": "",
            "location": "",
            "links": [],
        },
        "preferences": {
            "target_roles": [],
            "target_locations": [],
            "work_authorization": "",
            "remote_preference": "any",
        },
        "facts": [],
    }


def config_template() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "telemetry": {"enabled": False, "endpoint": None},
    }


def tracker_template() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "applications": []}


def candidates_template() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "candidates": []}


def initialize(root: Path) -> list[Path]:
    base = workspace(root)
    base.mkdir(parents=True, exist_ok=True)
    (base / "applications").mkdir(exist_ok=True)
    (base / "telemetry").mkdir(exist_ok=True)

    files: list[tuple[Path, Any]] = [
        (base / "config.json", config_template()),
        (base / "profile.json", profile_template()),
        (base / "tracker.json", tracker_template()),
        (base / "candidates.json", candidates_template()),
    ]
    created: list[Path] = []
    for path, value in files:
        if not path.exists():
            write_json(path, value)
            created.append(path)

    gitignore = base / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n!.gitignore\n", encoding="utf-8")
        created.append(gitignore)

    queue = base / "telemetry" / "events.jsonl"
    if not queue.exists():
        queue.touch()
        created.append(queue)

    record_event(root, "workspace_initialized", {"outcome": "success"})
    return created


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_string_list(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        errors.append(f"{label} must be an array of strings")


def validate_profile_data(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["profile must be a JSON object"]
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    identity = data.get("identity")
    if not isinstance(identity, dict):
        errors.append("identity must be an object")
    else:
        for key in ("name", "email"):
            if not is_nonempty_string(identity.get(key)):
                errors.append(f"identity.{key} must be a non-empty string")
        for key in ("phone", "location"):
            if not isinstance(identity.get(key), str):
                errors.append(f"identity.{key} must be a string")
        validate_string_list(identity.get("links"), "identity.links", errors)

    preferences = data.get("preferences")
    if not isinstance(preferences, dict):
        errors.append("preferences must be an object")
    else:
        validate_string_list(preferences.get("target_roles"), "preferences.target_roles", errors)
        validate_string_list(
            preferences.get("target_locations"), "preferences.target_locations", errors
        )
        if not isinstance(preferences.get("work_authorization"), str):
            errors.append("preferences.work_authorization must be a string")
        if preferences.get("remote_preference") not in REMOTE_PREFERENCES:
            errors.append(
                "preferences.remote_preference must be one of "
                + ", ".join(REMOTE_PREFERENCES)
            )

    facts = data.get("facts")
    if not isinstance(facts, list):
        errors.append("facts must be an array")
        return errors
    if not facts:
        errors.append("facts must contain at least one verified fact")

    seen: set[str] = set()
    for index, fact in enumerate(facts):
        label = f"facts[{index}]"
        if not isinstance(fact, dict):
            errors.append(f"{label} must be an object")
            continue
        fact_id = fact.get("id")
        if not isinstance(fact_id, str) or not FACT_ID_PATTERN.fullmatch(fact_id):
            errors.append(f"{label}.id must match fact-<lowercase-slug>")
        elif fact_id in seen:
            errors.append(f"{label}.id duplicates {fact_id}")
        else:
            seen.add(fact_id)
        if fact.get("category") not in FACT_CATEGORIES:
            errors.append(f"{label}.category must be one of {', '.join(FACT_CATEGORIES)}")
        for key in ("statement", "evidence"):
            if not is_nonempty_string(fact.get(key)):
                errors.append(f"{label}.{key} must be a non-empty string")
        validate_string_list(fact.get("keywords"), f"{label}.keywords", errors)
    return errors


def validate_job_data(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["job must be a JSON object"]
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"job.schema_version must be {SCHEMA_VERSION}")
    for key in ("company", "role", "description", "captured_at"):
        if not is_nonempty_string(data.get(key)):
            errors.append(f"job.{key} must be a non-empty string")
    for key in ("url", "location"):
        if not isinstance(data.get(key), str):
            errors.append(f"job.{key} must be a string")
    return errors


def validate_source_ids(
    value: Any, label: str, known_facts: set[str], errors: list[str]
) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"{label} must contain at least one fact ID")
        return
    if any(not isinstance(item, str) for item in value):
        errors.append(f"{label} must contain only strings")
        return
    if len(value) != len(set(value)):
        errors.append(f"{label} must not contain duplicate fact IDs")
    for fact_id in value:
        if fact_id not in known_facts:
            errors.append(f"{label} references unknown fact ID {fact_id}")


def validate_statement(
    value: Any, label: str, known_facts: set[str], errors: list[str]
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return
    if not is_nonempty_string(value.get("text")):
        errors.append(f"{label}.text must be a non-empty string")
    validate_source_ids(value.get("source_fact_ids"), f"{label}.source_fact_ids", known_facts, errors)


def validate_resume_data(data: Any, known_facts: set[str]) -> tuple[list[str], int]:
    errors: list[str] = []
    statement_count = 0
    if not isinstance(data, dict):
        return ["resume must be a JSON object"], statement_count
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"resume.schema_version must be {SCHEMA_VERSION}")

    validate_statement(data.get("summary"), "resume.summary", known_facts, errors)
    statement_count += 1

    skills = data.get("skills")
    if not isinstance(skills, list):
        errors.append("resume.skills must be an array")
    else:
        for index, skill in enumerate(skills):
            label = f"resume.skills[{index}]"
            if not isinstance(skill, dict):
                errors.append(f"{label} must be an object")
                continue
            if not is_nonempty_string(skill.get("name")):
                errors.append(f"{label}.name must be a non-empty string")
            validate_source_ids(
                skill.get("source_fact_ids"), f"{label}.source_fact_ids", known_facts, errors
            )
            statement_count += 1

    sections = data.get("sections")
    if not isinstance(sections, list):
        errors.append("resume.sections must be an array")
        return errors, statement_count
    for section_index, section in enumerate(sections):
        section_label = f"resume.sections[{section_index}]"
        if not isinstance(section, dict):
            errors.append(f"{section_label} must be an object")
            continue
        if not is_nonempty_string(section.get("heading")):
            errors.append(f"{section_label}.heading must be a non-empty string")
        items = section.get("items")
        if not isinstance(items, list):
            errors.append(f"{section_label}.items must be an array")
            continue
        for item_index, item in enumerate(items):
            item_label = f"{section_label}.items[{item_index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_label} must be an object")
                continue
            if not is_nonempty_string(item.get("title")):
                errors.append(f"{item_label}.title must be a non-empty string")
            for key in ("organization", "date_range"):
                if not isinstance(item.get(key), str):
                    errors.append(f"{item_label}.{key} must be a string")
            validate_source_ids(
                item.get("source_fact_ids"),
                f"{item_label}.source_fact_ids",
                known_facts,
                errors,
            )
            bullets = item.get("bullets")
            if not isinstance(bullets, list):
                errors.append(f"{item_label}.bullets must be an array")
                continue
            for bullet_index, bullet in enumerate(bullets):
                validate_statement(
                    bullet,
                    f"{item_label}.bullets[{bullet_index}]",
                    known_facts,
                    errors,
                )
                statement_count += 1
    return errors, statement_count


def count_bucket(count: int) -> str:
    if count <= 0:
        return "0"
    if count == 1:
        return "1"
    if count <= 5:
        return "2-5"
    if count <= 20:
        return "6-20"
    return "21+"


def telemetry_env_disabled() -> bool:
    truthy = {"1", "true", "yes", "on"}
    return (
        os.getenv("DISABLE_TELEMETRY", "").lower() in truthy
        or os.getenv("DO_NOT_TRACK", "").lower() in truthy
    )


def read_config(root: Path) -> dict[str, Any]:
    data = read_json(require_workspace(root) / "config.json")
    if not isinstance(data, dict):
        raise YapplyError("config.json must be an object")
    telemetry = data.get("telemetry")
    if not isinstance(telemetry, dict):
        raise YapplyError("config.json telemetry must be an object")
    return data


def validate_event(name: str, properties: dict[str, str]) -> None:
    allowed = EVENT_PROPERTIES.get(name)
    if allowed is None:
        raise YapplyError(f"Unsupported telemetry event: {name}")
    unexpected = set(properties) - allowed
    if unexpected:
        raise YapplyError(f"Unexpected telemetry properties: {', '.join(sorted(unexpected))}")
    if properties.get("outcome") not in (None, "success", "failure"):
        raise YapplyError("Telemetry outcome must be success or failure")
    for key in ("fact_count_bucket", "error_count_bucket", "statement_count_bucket"):
        if key in properties and properties[key] not in COUNT_BUCKETS:
            raise YapplyError(f"Invalid count bucket for {key}")
    for key in ("from_status", "to_status"):
        if key in properties and properties[key] not in (*STATUSES, "none"):
            raise YapplyError(f"Invalid application status for {key}")


def record_event(root: Path, name: str, properties: dict[str, str]) -> bool:
    base = workspace(root)
    config_path = base / "config.json"
    if not config_path.exists() or telemetry_env_disabled():
        return False
    config = read_json(config_path)
    telemetry = config.get("telemetry", {}) if isinstance(config, dict) else {}
    if not isinstance(telemetry, dict) or telemetry.get("enabled") is not True:
        return False
    validate_event(name, properties)
    event = {
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "plugin_version": PLUGIN_VERSION,
        "event_name": name,
        "occurred_on": utc_date(),
        "properties": properties,
    }
    queue = base / "telemetry" / "events.jsonl"
    queue.parent.mkdir(parents=True, exist_ok=True)
    with queue.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")
    return True


def read_queue(base: Path) -> list[dict[str, Any]]:
    queue = base / "telemetry" / "events.jsonl"
    if not queue.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(queue.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise YapplyError(f"Invalid telemetry queue JSON on line {line_number}") from exc
        if not isinstance(event, dict):
            raise YapplyError(f"Telemetry queue line {line_number} is not an object")
        events.append(event)
    return events


def validate_slug(slug: str) -> str:
    if not SLUG_PATTERN.fullmatch(slug):
        raise YapplyError("Slug must be lowercase letters, numbers, and hyphens (max 80 characters)")
    return slug


def create_application(root: Path, slug: str) -> Path:
    slug = validate_slug(slug)
    base = require_workspace(root)
    app_dir = base / "applications" / slug
    if app_dir.exists():
        raise YapplyError(f"Application already exists: {slug}")
    app_dir.mkdir(parents=True)
    write_json(
        app_dir / "job.json",
        {
            "schema_version": SCHEMA_VERSION,
            "company": "",
            "role": "",
            "url": "",
            "location": "",
            "description": "",
            "captured_at": utc_now(),
        },
    )
    write_json(
        app_dir / "resume.json",
        {
            "schema_version": SCHEMA_VERSION,
            "summary": {"text": "", "source_fact_ids": []},
            "skills": [],
            "sections": [],
        },
    )
    tracker_path = base / "tracker.json"
    tracker = read_json(tracker_path)
    if not isinstance(tracker, dict) or not isinstance(tracker.get("applications"), list):
        raise YapplyError("tracker.json must contain an applications array")
    now = utc_now()
    tracker["applications"].append(
        {"slug": slug, "status": "preparing", "created_at": now, "updated_at": now}
    )
    write_json(tracker_path, tracker)
    record_event(root, "application_created", {"outcome": "success"})
    return app_dir


def validate_application(root: Path, slug: str) -> tuple[list[str], int]:
    slug = validate_slug(slug)
    base = require_workspace(root)
    profile = read_json(base / "profile.json")
    profile_errors = validate_profile_data(profile)
    known_facts = {
        fact.get("id")
        for fact in profile.get("facts", [])
        if isinstance(fact, dict) and isinstance(fact.get("id"), str)
    } if isinstance(profile, dict) else set()
    app_dir = base / "applications" / slug
    if not app_dir.is_dir():
        raise YapplyError(f"Unknown application: {slug}")
    job_errors = validate_job_data(read_json(app_dir / "job.json"))
    resume_errors, statement_count = validate_resume_data(
        read_json(app_dir / "resume.json"), known_facts
    )
    errors = [f"profile: {error}" for error in profile_errors]
    errors.extend(job_errors)
    errors.extend(resume_errors)
    record_event(
        root,
        "application_validated",
        {
            "outcome": "success" if not errors else "failure",
            "statement_count_bucket": count_bucket(statement_count),
            "error_count_bucket": count_bucket(len(errors)),
        },
    )
    return errors, statement_count


def update_status(root: Path, slug: str, new_status: str) -> tuple[str, str]:
    slug = validate_slug(slug)
    if new_status not in STATUSES:
        raise YapplyError(f"Status must be one of: {', '.join(STATUSES)}")
    base = require_workspace(root)
    if not (base / "applications" / slug).is_dir():
        raise YapplyError(f"Unknown application: {slug}")
    tracker_path = base / "tracker.json"
    tracker = read_json(tracker_path)
    applications = tracker.get("applications") if isinstance(tracker, dict) else None
    if not isinstance(applications, list):
        raise YapplyError("tracker.json must contain an applications array")
    previous = "none"
    for entry in applications:
        if isinstance(entry, dict) and entry.get("slug") == slug:
            previous = entry.get("status") if entry.get("status") in STATUSES else "none"
            entry["status"] = new_status
            entry["updated_at"] = utc_now()
            break
    else:
        now = utc_now()
        applications.append(
            {"slug": slug, "status": new_status, "created_at": now, "updated_at": now}
        )
    write_json(tracker_path, tracker)
    record_event(
        root,
        "application_status_changed",
        {"outcome": "success", "from_status": previous, "to_status": new_status},
    )
    return previous, new_status


def workspace_status(root: Path) -> dict[str, Any]:
    base = require_workspace(root)
    profile = read_json(base / "profile.json")
    profile_errors = validate_profile_data(profile)
    tracker = read_json(base / "tracker.json")
    applications = tracker.get("applications", []) if isinstance(tracker, dict) else []
    if not isinstance(applications, list):
        raise YapplyError("tracker.json must contain an applications array")
    status_counts = Counter(
        entry.get("status")
        for entry in applications
        if isinstance(entry, dict) and entry.get("status") in STATUSES
    )
    config = read_config(root)
    telemetry = config["telemetry"]
    return {
        "workspace": str(base),
        "profile_valid": not profile_errors,
        "profile_error_count": len(profile_errors),
        "application_count": len(applications),
        "applications_by_status": dict(sorted(status_counts.items())),
        "telemetry": {
            "enabled": telemetry.get("enabled") is True and not telemetry_env_disabled(),
            "environment_override": telemetry_env_disabled(),
            "endpoint_configured": bool(telemetry.get("endpoint")),
            "queued_events": len(read_queue(base)),
        },
    }


def telemetry_enable(root: Path, endpoint: str) -> None:
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.netloc:
        raise YapplyError("Telemetry endpoint must be an absolute HTTPS URL")
    base = require_workspace(root)
    config = read_config(root)
    config["telemetry"] = {"enabled": True, "endpoint": endpoint}
    write_json(base / "config.json", config)


def telemetry_disable(root: Path) -> None:
    base = require_workspace(root)
    config = read_config(root)
    endpoint = config["telemetry"].get("endpoint")
    config["telemetry"] = {"enabled": False, "endpoint": endpoint}
    write_json(base / "config.json", config)


def telemetry_clear(root: Path) -> int:
    base = require_workspace(root)
    events = read_queue(base)
    (base / "telemetry" / "events.jsonl").write_text("", encoding="utf-8")
    return len(events)


def telemetry_flush(root: Path) -> int:
    if telemetry_env_disabled():
        raise YapplyError("Telemetry is disabled by the environment")
    base = require_workspace(root)
    config = read_config(root)
    telemetry = config["telemetry"]
    if telemetry.get("enabled") is not True:
        raise YapplyError("Telemetry is disabled")
    endpoint = telemetry.get("endpoint")
    if not isinstance(endpoint, str):
        raise YapplyError("No telemetry endpoint is configured")
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.netloc:
        raise YapplyError("Telemetry endpoint must be an absolute HTTPS URL")
    events = read_queue(base)
    if not events:
        return 0
    payload = json.dumps({"events": events}, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": f"yapply/{PLUGIN_VERSION}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise YapplyError(f"Telemetry collector returned HTTP {response.status}")
    except urllib.error.URLError as exc:
        raise YapplyError(f"Could not reach telemetry collector: {exc.reason}") from exc
    (base / "telemetry" / "events.jsonl").write_text("", encoding="utf-8")
    return len(events)


def print_validation(errors: list[str], label: str) -> int:
    if not errors:
        print(f"{label} is valid.")
        return 0
    print(f"{label} has {len(errors)} error(s):", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yapply",
        description="Local-first career workspace tools for the Yapply agent plugin.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Career workspace root (default: current directory)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create a private .yapply workspace without overwriting files")
    status_parser = subparsers.add_parser("status", help="Show workspace readiness and tracker totals")
    status_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    subparsers.add_parser("validate-profile", help="Validate profile.json and verified fact IDs")

    create_parser = subparsers.add_parser(
        "create-application", help="Create an empty application record"
    )
    create_parser.add_argument("slug")

    validate_parser = subparsers.add_parser(
        "validate-application", help="Validate a job and provenance-backed resume"
    )
    validate_parser.add_argument("slug")

    track_parser = subparsers.add_parser("track", help="Update an application's status")
    track_parser.add_argument("slug")
    track_parser.add_argument("status", choices=STATUSES)

    telemetry_parser = subparsers.add_parser("telemetry", help="Manage anonymous telemetry")
    telemetry_subparsers = telemetry_parser.add_subparsers(dest="telemetry_command", required=True)
    telemetry_subparsers.add_parser("status", help="Show telemetry configuration and queue size")
    enable_parser = telemetry_subparsers.add_parser("enable", help="Enable telemetry for an HTTPS collector")
    enable_parser.add_argument("--endpoint", required=True)
    telemetry_subparsers.add_parser("disable", help="Disable telemetry without deleting the queue")
    telemetry_subparsers.add_parser("preview", help="Print the exact queued events")
    telemetry_subparsers.add_parser("clear", help="Delete queued telemetry events")
    telemetry_subparsers.add_parser("flush", help="Send queued events to the configured collector")
    return parser


def run(args: argparse.Namespace) -> int:
    root: Path = args.root
    if args.command == "init":
        created = initialize(root)
        if created:
            print(f"Initialized {workspace(root)} ({len(created)} files created).")
        else:
            print(f"Yapply workspace already initialized at {workspace(root)}; nothing overwritten.")
        return 0

    if args.command == "status":
        status = workspace_status(root)
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print(f"Workspace: {status['workspace']}")
            print(f"Profile valid: {'yes' if status['profile_valid'] else 'no'}")
            print(f"Applications: {status['application_count']}")
            for key, value in status["applications_by_status"].items():
                print(f"  {key}: {value}")
            telemetry = status["telemetry"]
            print(f"Telemetry enabled: {'yes' if telemetry['enabled'] else 'no'}")
            print(f"Queued telemetry events: {telemetry['queued_events']}")
        return 0

    if args.command == "validate-profile":
        base = require_workspace(root)
        profile = read_json(base / "profile.json")
        errors = validate_profile_data(profile)
        fact_count = len(profile.get("facts", [])) if isinstance(profile, dict) and isinstance(profile.get("facts"), list) else 0
        record_event(
            root,
            "profile_validated",
            {
                "outcome": "success" if not errors else "failure",
                "fact_count_bucket": count_bucket(fact_count),
                "error_count_bucket": count_bucket(len(errors)),
            },
        )
        return print_validation(errors, "Profile")

    if args.command == "create-application":
        app_dir = create_application(root, args.slug)
        print(f"Created application at {app_dir}.")
        return 0

    if args.command == "validate-application":
        errors, _ = validate_application(root, args.slug)
        return print_validation(errors, f"Application {args.slug}")

    if args.command == "track":
        previous, current = update_status(root, args.slug, args.status)
        print(f"Updated {args.slug}: {previous} -> {current}.")
        return 0

    if args.command == "telemetry":
        if args.telemetry_command == "status":
            print(json.dumps(workspace_status(root)["telemetry"], indent=2))
        elif args.telemetry_command == "enable":
            telemetry_enable(root, args.endpoint)
            print("Anonymous telemetry enabled. Use 'yapply telemetry preview' before flushing.")
        elif args.telemetry_command == "disable":
            telemetry_disable(root)
            print("Telemetry disabled. Existing queued events were preserved.")
        elif args.telemetry_command == "preview":
            print(json.dumps(read_queue(require_workspace(root)), indent=2))
        elif args.telemetry_command == "clear":
            print(f"Cleared {telemetry_clear(root)} queued event(s).")
        elif args.telemetry_command == "flush":
            print(f"Sent {telemetry_flush(root)} event(s).")
        return 0
    raise YapplyError(f"Unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except YapplyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
