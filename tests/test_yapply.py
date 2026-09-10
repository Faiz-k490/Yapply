from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "yapply.py"
SPEC = importlib.util.spec_from_file_location("yapply_cli", SCRIPT)
assert SPEC and SPEC.loader
yapply = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(yapply)


class YapplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        yapply.initialize(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @property
    def base(self) -> Path:
        return self.root / ".yapply"

    def write_valid_profile(self) -> None:
        yapply.write_json(
            self.base / "profile.json",
            {
                "schema_version": 1,
                "identity": {
                    "name": "Test Person",
                    "email": "test@example.com",
                    "phone": "",
                    "location": "Test City",
                    "links": [],
                },
                "preferences": {
                    "target_roles": ["Engineer"],
                    "target_locations": ["Remote"],
                    "work_authorization": "Authorized",
                    "remote_preference": "any",
                },
                "facts": [
                    {
                        "id": "fact-project-one",
                        "category": "project",
                        "statement": "Built a test project.",
                        "evidence": "Test fixture",
                        "keywords": ["testing"],
                    }
                ],
            },
        )

    def write_valid_application(self, slug: str = "example-role") -> None:
        app_dir = yapply.create_application(self.root, slug)
        yapply.write_json(
            app_dir / "job.json",
            {
                "schema_version": 1,
                "company": "Example Company",
                "role": "Engineer",
                "url": "https://example.com/job",
                "location": "Remote",
                "description": "Build reliable systems.",
                "captured_at": "2026-01-01T00:00:00Z",
            },
        )
        yapply.write_json(
            app_dir / "resume.json",
            {
                "schema_version": 1,
                "summary": {
                    "text": "Engineer who builds tested systems.",
                    "source_fact_ids": ["fact-project-one"],
                },
                "skills": [
                    {"name": "Testing", "source_fact_ids": ["fact-project-one"]}
                ],
                "sections": [
                    {
                        "heading": "Projects",
                        "items": [
                            {
                                "title": "Test project",
                                "organization": "",
                                "date_range": "",
                                "source_fact_ids": ["fact-project-one"],
                                "bullets": [
                                    {
                                        "text": "Built a test project.",
                                        "source_fact_ids": ["fact-project-one"],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        )

    def test_init_is_private_and_idempotent(self) -> None:
        config_before = yapply.read_json(self.base / "config.json")
        created = yapply.initialize(self.root)
        config_after = yapply.read_json(self.base / "config.json")
        self.assertEqual(created, [])
        self.assertEqual(config_before, config_after)
        self.assertEqual((self.base / ".gitignore").read_text(), "*\n!.gitignore\n")
        self.assertEqual(yapply.read_queue(self.base), [])

    def test_valid_application_requires_known_source_facts(self) -> None:
        self.write_valid_profile()
        self.write_valid_application()
        errors, statements = yapply.validate_application(self.root, "example-role")
        self.assertEqual(errors, [])
        self.assertEqual(statements, 3)

        resume_path = self.base / "applications" / "example-role" / "resume.json"
        resume = yapply.read_json(resume_path)
        resume["summary"]["source_fact_ids"] = ["fact-invented"]
        yapply.write_json(resume_path, resume)
        errors, _ = yapply.validate_application(self.root, "example-role")
        self.assertTrue(any("unknown fact ID fact-invented" in error for error in errors))

    def test_invalid_slug_cannot_escape_workspace(self) -> None:
        with self.assertRaises(yapply.YapplyError):
            yapply.create_application(self.root, "../escape")

    def test_telemetry_is_opt_in_allow_listed_and_overridable(self) -> None:
        self.write_valid_profile()
        yapply.validate_profile_data(yapply.read_json(self.base / "profile.json"))
        self.assertEqual(yapply.read_queue(self.base), [])

        yapply.telemetry_enable(self.root, "https://telemetry.example.test/events")
        result = yapply.main(["--root", str(self.root), "validate-profile"])
        self.assertEqual(result, 0)
        events = yapply.read_queue(self.base)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_name"], "profile_validated")
        self.assertNotIn("installation_id", events[0])
        self.assertIn("occurred_on", events[0])
        serialized = json.dumps(events)
        self.assertNotIn("Test Person", serialized)
        self.assertNotIn("test@example.com", serialized)
        self.assertEqual(
            set(events[0]["properties"]),
            {"outcome", "fact_count_bucket", "error_count_bucket"},
        )

        with mock.patch.dict(os.environ, {"DISABLE_TELEMETRY": "1"}, clear=False):
            result = yapply.main(["--root", str(self.root), "validate-profile"])
        self.assertEqual(result, 0)
        self.assertEqual(len(yapply.read_queue(self.base)), 1)

    def test_cli_status_json(self) -> None:
        completed = subprocess.run(
            ["python3", str(SCRIPT), "--root", str(self.root), "status", "--json"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertFalse(payload["profile_valid"])
        self.assertEqual(payload["application_count"], 0)
        self.assertFalse(payload["telemetry"]["enabled"])


if __name__ == "__main__":
    unittest.main()
