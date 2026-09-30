from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "yapply.py"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_plugin.py"
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

    @unittest.skipUnless(importlib.util.find_spec("reportlab"), "ReportLab is not installed")
    def test_render_valid_application_to_pdf(self) -> None:
        self.write_valid_profile()
        self.write_valid_application()
        output = yapply.render_resume(self.root, "example-role")
        self.assertTrue(output.is_file())
        self.assertTrue(output.read_bytes().startswith(b"%PDF"))
        self.assertGreater(output.stat().st_size, 1_000)

    @unittest.skipUnless(importlib.util.find_spec("reportlab"), "ReportLab is not installed")
    def test_demo_builds_ready_application_and_pdf(self) -> None:
        demo_root = self.root / "demo-workspace"
        output = yapply.create_demo(demo_root)
        self.assertTrue(output.is_file())
        errors, _ = yapply.validate_application(demo_root, "northstar-platform-engineer")
        self.assertEqual(errors, [])
        tracker = yapply.read_json(demo_root / ".yapply" / "tracker.json")
        self.assertEqual(tracker["applications"][0]["status"], "ready")

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
            [sys.executable, str(SCRIPT), "--root", str(self.root), "status", "--json"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertFalse(payload["profile_valid"])
        self.assertEqual(payload["application_count"], 0)
        self.assertFalse(payload["telemetry"]["enabled"])

    def test_clean_plugin_bundle_excludes_development_and_user_data(self) -> None:
        destination = self.root / "bundle" / "yapply"
        completed = subprocess.run(
            [sys.executable, str(BUILD_SCRIPT), "--output", str(destination)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue((destination / ".codex-plugin" / "plugin.json").is_file())
        self.assertTrue((destination / ".claude-plugin" / "plugin.json").is_file())
        self.assertTrue((destination / ".yapply-plugin-bundle").is_file())
        self.assertTrue((destination / "scripts" / "yapply.py").is_file())
        for excluded in (".git", ".yapply", "tests", "tmp", "output", "__pycache__"):
            self.assertFalse((destination / excluded).exists(), excluded)

    def test_plugin_builder_refuses_to_replace_unmarked_directory(self) -> None:
        destination = self.root / "unmarked" / "yapply"
        destination.mkdir(parents=True)
        sentinel = destination / "keep-me.txt"
        sentinel.write_text("safe", encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(BUILD_SCRIPT), "--output", str(destination), "--force"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertTrue(sentinel.is_file())

    def test_demo_without_reportlab_creates_nothing(self) -> None:
        demo_root = self.root / "no-reportlab"
        with mock.patch.dict(sys.modules, {"reportlab": None}):
            with self.assertRaisesRegex(yapply.YapplyError, "ReportLab"):
                yapply.create_demo(demo_root)
        self.assertFalse((demo_root / ".yapply").exists())


class RepositoryTests(unittest.TestCase):
    """Keep the public manifests and README figures in step with the code."""

    def read_manifest(self, relative: str) -> dict:
        return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))

    def readme_numbers(self) -> dict[str, str]:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        section = readme.split("## By the numbers", 1)[1].split("\n## ", 1)[0]
        rows = re.findall(r"^\| \*\*(.+?)\*\* \| (.+?) \|$", section, re.MULTILINE)
        return {label: number for number, label in rows}

    def test_manifests_agree_on_name_and_version(self) -> None:
        claude = self.read_manifest(".claude-plugin/plugin.json")
        codex = self.read_manifest(".codex-plugin/plugin.json")
        marketplace = self.read_manifest(".claude-plugin/marketplace.json")
        self.assertEqual(claude["version"], yapply.PLUGIN_VERSION)
        self.assertEqual(codex["version"].split("+")[0], yapply.PLUGIN_VERSION)
        self.assertEqual(claude["name"], codex["name"])
        self.assertIn(claude["name"], [plugin["name"] for plugin in marketplace["plugins"]])

    def test_readme_numbers_match_the_code(self) -> None:
        numbers = self.readme_numbers()
        skills = [path for path in (REPO_ROOT / "skills").iterdir() if (path / "SKILL.md").is_file()]
        requirements = [
            line
            for line in (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        hosts = [path for path in (".claude-plugin", ".codex-plugin") if (REPO_ROOT / path).is_dir()]
        self.assertEqual(numbers["agent skills"], str(len(skills)))
        self.assertEqual(numbers["hosts: Claude Code and Codex"], str(len(hosts)))
        self.assertEqual(numbers["application stages tracked"], str(len(yapply.STATUSES)))
        self.assertEqual(numbers["allow-listed telemetry events"], str(len(yapply.EVENT_PROPERTIES)))
        self.assertEqual(numbers["dependency outside the Python standard library"], str(len(requirements)))
        self.assertEqual(numbers["provider API keys needed"], "0")
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotRegex(source, r"API_KEY|api_key")
        self.assertEqual(numbers["network requests the CLI makes on its own"], "0")
        # The only request the CLI can make is the opt-in telemetry flush.
        self.assertEqual(source.count("urlopen("), 1)
        flush = source.split("def telemetry_flush", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("urlopen(", flush)
        self.assertEqual(numbers["telemetry, until you opt in"], "Off")
        self.assertFalse(yapply.config_template()["telemetry"]["enabled"])

    @unittest.skipUnless(importlib.util.find_spec("reportlab"), "ReportLab is not installed")
    def test_readme_demo_numbers_match_the_demo(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            yapply.create_demo(root)
            errors, statements = yapply.validate_application(root, "northstar-platform-engineer")
            facts = yapply.read_json(root / ".yapply" / "profile.json")["facts"]
        self.assertEqual(errors, [])
        label = f"demo résumé lines traced to one of {len(facts)} verified facts"
        self.assertEqual(self.readme_numbers()[label], f"{statements}/{statements}")


if __name__ == "__main__":
    unittest.main()
