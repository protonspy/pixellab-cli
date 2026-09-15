"""Hold the skill to the CLI.

The skill is the only interface an agent has to this tool. A command it names that
does not exist sends an agent down a dead end; a command the tool has that the skill
never mentions is a capability nobody will find. Both are caught here, because
neither is visible by reading either file alone.
"""

import re
from pathlib import Path

import pytest
import typer

from pixellab_cli.cli import app

SKILL_DIR = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "pixellab-assets"
SKILL = SKILL_DIR / "SKILL.md"
REFERENCES = SKILL_DIR / "references"

# Commands whose absence from the skill body is deliberate: they are listed in the
# generated reference and are not something an agent reaches for unprompted.
NOT_IN_BODY: set[str] = set()


def cli_commands() -> set[str]:
    """Every leaf command, as `pixellab …` would be typed."""
    root = typer.main.get_command(app)
    found: set[str] = set()

    def walk(command, prefix=""):
        name = f"{prefix}{command.name}".strip()
        subcommands = getattr(command, "commands", None)
        if subcommands:
            for sub in subcommands.values():
                walk(sub, f"{name} " if name else "")
            return
        found.add(name.replace("pixellab ", "", 1))

    walk(root)
    return found


def skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


def all_skill_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in [SKILL, *sorted(REFERENCES.glob("*.md"))]
    )


def named_commands(text: str) -> set[str]:
    """Every `pixellab …` invocation the text mentions, as a command path."""
    found = set()
    for match in re.finditer(r"pixellab ((?:[a-z][a-z-]*)(?: [a-z][a-z-]*)?)", text):
        found.add(match.group(1).strip())
    return found


class TestTheSkillIsWellFormed:
    def test_it_exists_where_the_agent_looks_for_it(self):
        assert SKILL.is_file()

    def test_it_has_a_name_and_a_description(self):
        text = skill_text()

        assert text.startswith("---")
        assert re.search(r"^name: pixellab-assets$", text, re.MULTILINE)
        assert re.search(r"^description: .{40,}$", text, re.MULTILINE)

    def test_the_description_says_when_to_use_it(self):
        description = re.search(r"^description: (.+)$", skill_text(), re.MULTILINE).group(1)

        assert "Use it" in description

    def test_both_reference_files_are_there(self):
        assert (REFERENCES / "commands.md").is_file()
        assert (REFERENCES / "choosing.md").is_file()

    def test_the_body_stays_shorter_than_the_references_it_defers_to(self):
        # R4.2: detail that is only sometimes needed does not belong in the body.
        body = len(skill_text())
        references = sum(len(path.read_text(encoding="utf-8")) for path in REFERENCES.glob("*.md"))

        assert body < references


class TestEveryCommandItNamesExists:
    def test_no_command_in_the_skill_is_invented(self):
        known = cli_commands()
        groups = {name.split(" ")[0] for name in known if " " in name}
        mentioned = named_commands(all_skill_text())

        unknown = {
            name
            for name in mentioned
            if name not in known and name not in groups and name.split(" ")[0] not in known | groups
        }

        assert not unknown, f"the skill names commands that do not exist: {sorted(unknown)}"

    @pytest.mark.parametrize("command", sorted(cli_commands()))
    def test_every_command_the_tool_has_is_named_somewhere_in_the_skill(self, command):
        if command in NOT_IN_BODY:
            pytest.skip("deliberately not in the skill")

        assert command in all_skill_text(), f"{command} is not mentioned anywhere in the skill"


class TestTheRulesThatCostMoney:
    def test_it_requires_a_dry_run_before_the_first_paid_call(self):
        text = skill_text()

        assert "--dry-run" in text
        assert "wait" in text.lower()

    def test_it_says_a_failed_generation_is_charged(self):
        assert "failed generation is charged" in skill_text()

    def test_it_points_at_the_ledger_for_what_has_been_spent(self):
        assert "pixellab ledger" in skill_text()

    def test_it_names_the_pro_tools_commands(self):
        text = skill_text()

        assert "Pro Tools" in text
        assert "pixellab object new" in text

    def test_it_says_animation_costs_per_direction(self):
        assert "per direction" in skill_text()

    def test_it_offers_the_budget_flag(self):
        assert "--max-generations" in skill_text()


class TestCredentials:
    def test_it_names_both_variables(self):
        text = skill_text()

        assert "PIXELLAB_SECRET" in text
        assert "FAL_KEY" in text

    def test_it_says_where_the_values_come_from(self):
        text = skill_text()

        assert "pixellab.ai/account" in text
        assert "fal.ai/dashboard/keys" in text

    def test_it_forbids_printing_a_credential(self):
        text = skill_text().lower()

        assert "never read, print, echo" in text

    def test_it_contains_nothing_that_looks_like_a_credential(self):
        text = all_skill_text()

        assert not re.search(r"\b(sk|fal|pl)-[A-Za-z0-9]{16,}", text)


class TestRoutingAdvice:
    def test_it_tells_the_agent_not_to_name_a_route(self):
        assert "Do not name a provider route" in skill_text()

    def test_it_tells_the_agent_not_to_guess_enum_values(self):
        assert "Do not guess enum spellings" in skill_text()

    def test_it_explains_how_to_resume_a_stopped_recipe(self):
        text = skill_text()

        assert "recipe resume" in text
        assert "recipe.json" in text

    def test_it_says_where_the_output_lands(self):
        assert "pixellab-out/" in skill_text()
