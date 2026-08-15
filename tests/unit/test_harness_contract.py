from collections.abc import Iterator
import os
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]


EXCLUDED_MARKDOWN_ROOTS = {".git", "IsaacSim"}
LAST_UPDATED_PATTERN = re.compile(
    r"^> Last updated: \d{4}-\d{2}-\d{2} \d{2}:\d{2} KST$"
)


def iter_project_markdown_files() -> Iterator[Path]:
    for directory, dirnames, filenames in os.walk(ROOT):
        relative_directory = Path(directory).relative_to(ROOT)
        kept_directories = []
        for name in dirnames:
            relative_child = relative_directory / name
            if name == "__pycache__":
                continue
            if relative_child.parts[0] in EXCLUDED_MARKDOWN_ROOTS:
                continue
            if relative_child.parts[:2] == (".superpowers", "sdd"):
                continue
            kept_directories.append(name)
        dirnames[:] = kept_directories

        for filename in filenames:
            if filename.endswith(".md"):
                yield Path(directory) / filename


class HarnessContractTest(unittest.TestCase):
    def test_markdown_files_start_with_last_updated_timestamp(self) -> None:
        invalid = []
        for path in sorted(iter_project_markdown_files()):
            lines = path.read_text(encoding="utf-8").splitlines()
            first_line = lines[0] if lines else ""
            if LAST_UPDATED_PATTERN.fullmatch(first_line) is None:
                invalid.append(str(path.relative_to(ROOT)))

        self.assertEqual(
            [],
            invalid,
            f"Markdown files missing valid last-updated metadata: {invalid}",
        )

    def test_required_files_exist(self) -> None:
        required = [
            "AGENTS.md",
            "ARCHITECTURE.md",
            ".codex/config.toml",
            ".codex/rules/default.rules",
            "docs/index.md",
            "docs/safety/robot-safety.md",
            "docs/experiments/protocol.md",
            "scripts/check.sh",
            "scripts/test_offline.sh",
        ]

        missing = [path for path in required if not (ROOT / path).is_file()]
        self.assertEqual([], missing, f"Missing harness files: {missing}")

    def test_safe_codex_defaults(self) -> None:
        config = (ROOT / ".codex/config.toml").read_text(encoding="utf-8")

        self.assertIn('approval_policy = "on-request"', config)
        self.assertIn('sandbox_mode = "workspace-write"', config)
        self.assertIn('approvals_reviewer = "user"', config)
        self.assertNotIn('sandbox_mode = "danger-full-access"', config)
        self.assertNotIn('approval_policy = "never"', config)

    def test_agents_contains_robot_safety_rules(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        required_phrases = [
            "/sim/cmd_vel",
            "/selected_route",
            "/navigation_stop",
            "Only one process may publish",
            "offline test",
            "real LIMO",
        ]

        missing = [text for text in required_phrases if text not in agents]
        self.assertEqual([], missing, f"Missing AGENTS.md rules: {missing}")

    def test_dangerous_commands_are_restricted(self) -> None:
        rules = (ROOT / ".codex/rules/default.rules").read_text(
            encoding="utf-8"
        )

        required_patterns = [
            '"ros2", "topic", "pub"',
            '"rm", "-rf"',
            '"git", "reset", "--hard"',
            'decision = "forbidden"',
        ]

        missing = [text for text in required_patterns if text not in rules]
        self.assertEqual([], missing, f"Missing command restrictions: {missing}")

    def test_docs_index_links_core_documents(self) -> None:
        index = (ROOT / "docs/index.md").read_text(encoding="utf-8")

        required_links = [
            "../ARCHITECTURE.md",
            "safety/robot-safety.md",
            "experiments/protocol.md",
            "exec-plans/active/",
        ]

        missing = [text for text in required_links if text not in index]
        self.assertEqual([], missing, f"Missing documentation links: {missing}")

    def test_architecture_records_static_source_audit(self) -> None:
        architecture = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")

        required_sections = [
            "## Verification method",
            "## Runtime processes and entry points",
            "## ROS2 interface inventory",
            "## HTTP interface inventory",
            "## `/sim/cmd_vel` publisher inventory",
            "## VLM failure and timeout handling",
            "## Inter-module JSON contracts",
            "## Hard-coded paths and locations",
            "## Documentation and code mismatches",
        ]
        required_statuses = ["Verified", "Partially verified", "Assumption"]

        missing = [
            text
            for text in required_sections + required_statuses
            if text not in architecture
        ]
        self.assertEqual([], missing, f"Missing architecture audit content: {missing}")

    def test_markdown_document_locations_are_indexed(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        index = (ROOT / "docs/index.md").read_text(encoding="utf-8")

        required_agent_locations = [
            "## Markdown documentation locations",
            "docs/meetings/",
            "docs/experiments/",
            "docs/exec-plans/active/",
            "docs/superpowers/specs/",
            "docs/superpowers/plans/",
            "docs/automation/",
        ]
        required_index_entries = [
            "## Markdown location map",
            "superpowers/specs/",
            "superpowers/plans/",
            "automation/index.md",
            "WEEKLY_REPORT_AUTOMATION.md",
        ]

        missing_agents = [
            text for text in required_agent_locations if text not in agents
        ]
        missing_index = [
            text for text in required_index_entries if text not in index
        ]

        self.assertEqual(
            [], missing_agents, f"Missing AGENTS.md locations: {missing_agents}"
        )
        self.assertEqual(
            [], missing_index, f"Missing docs index entries: {missing_index}"
        )
        self.assertTrue((ROOT / "docs/automation/index.md").is_file())


if __name__ == "__main__":
    unittest.main()
