from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HarnessContractTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
