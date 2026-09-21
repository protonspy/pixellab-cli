"""Hold the skills to the CLI.

The skills are the only interface an agent has to this tool. A command they name that
does not exist sends an agent down a dead end; a command the tool has that no skill
mentions is a capability nobody will find. Both are caught here, because neither is
visible by reading any one file alone.

Since the split there is a third failure worth catching: a command owned by two skills.
Two owners is two places to keep true, and the copy is the one that goes stale.
"""

import re
from pathlib import Path

import pytest
import typer

from pixellab_cli.cli import app
from pixellab_cli.harness import ENTRY_SKILL

SKILLS_DIR = Path(__file__).resolve().parents[1] / ".claude" / "skills"
ENTRY_DIR = SKILLS_DIR / ENTRY_SKILL
ENTRY = ENTRY_DIR / "SKILL.md"
REFERENCES = ENTRY_DIR / "references"

PACKAGED = Path(__file__).resolve().parents[1] / "src" / "pixellab_cli" / "skill"

# Every category skill `harness.packaged_skills` ships, and the list is checked against
# it below: one missing from here is a skill nothing in this file tests, which is how
# the animation skill went five releases without being checked at all.
CATEGORY_SKILLS = (
    "pixellab-cli-images",
    "pixellab-cli-characters",
    "pixellab-cli-animation",
    "pixellab-cli-editing",
    "pixellab-cli-scenes",
    "pixellab-cli-interface",
)

ALL_SKILLS = (ENTRY_SKILL, *CATEGORY_SKILLS)


def cli_commands() -> set[str]:
    """Every leaf command, as `pixellab-cli …` would be typed."""
    root = typer.main.get_command(app)
    found: set[str] = set()

    def walk(command, prefix=""):
        name = f"{prefix}{command.name}".strip()
        subcommands = getattr(command, "commands", None)
        if subcommands:
            for sub in subcommands.values():
                walk(sub, f"{name} " if name else "")
            return
        found.add(name.replace("pixellab-cli ", "", 1))

    walk(root)
    return found


def entry_text() -> str:
    return ENTRY.read_text(encoding="utf-8")


def skill_body(name: str) -> str:
    return (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")


def all_skill_text() -> str:
    parts = [entry_text(), *(skill_body(name) for name in CATEGORY_SKILLS)]
    parts += [path.read_text(encoding="utf-8") for path in sorted(REFERENCES.glob("*.md"))]
    return "\n".join(parts)


def documents(text: str, command: str) -> bool:
    """Whether `text` carries this command's usage line, not merely its name."""
    return bool(re.search(rf"^pixellab-cli {re.escape(command)} <", text, re.MULTILINE))


def named_commands(text: str) -> set[str]:
    """Every `pixellab …` invocation the text mentions, as a command path."""
    found = set()
    for match in re.finditer(r"pixellab-cli ((?:[a-z][a-z-]*)(?: [a-z][a-z-]*)?)", text):
        found.add(match.group(1).strip())
    return found


class TestTheSkillsAreWellFormed:
    def test_the_entry_exists_where_the_agent_looks_for_it(self):
        assert ENTRY.is_file()

    @pytest.mark.parametrize("name", (ENTRY_SKILL, *CATEGORY_SKILLS))
    def test_each_skill_has_a_name_matching_its_directory(self, name):
        text = skill_body(name)

        assert text.startswith("---")
        assert re.search(rf"^name: {re.escape(name)}$", text, re.MULTILINE)

    @pytest.mark.parametrize("name", (ENTRY_SKILL, *CATEGORY_SKILLS))
    def test_each_description_says_when_to_use_it(self, name):
        description = re.search(r"^description: (.+)$", skill_body(name), re.MULTILINE).group(1)

        assert len(description) > 40
        assert "Use it" in description

    def test_the_cost_reference_is_there(self):
        assert (REFERENCES / "costs.md").is_file()

    def test_the_entry_stays_shorter_than_what_it_routes_to(self):
        # R4.2, carried across the split: the entry loads whenever art is mentioned, so
        # the detail that is only needed once a category is chosen lives in the category.
        routed = sum(len(skill_body(name)) for name in CATEGORY_SKILLS)

        assert len(entry_text()) < routed


class TestTheEntryRoutes:
    """R5.1: an agent that loaded only the entry has to be able to find the rest."""

    @pytest.mark.parametrize("name", CATEGORY_SKILLS)
    def test_the_entry_names_every_category_skill(self, name):
        assert name in entry_text()


class TestEveryCommandHasExactlyOneOwner:
    def test_no_command_in_any_skill_is_invented(self):
        known = cli_commands()
        groups = {name.split(" ")[0] for name in known if " " in name}
        mentioned = named_commands(all_skill_text())

        unknown = {
            name
            for name in mentioned
            if name not in known and name not in groups and name.split(" ")[0] not in known | groups
        }

        assert not unknown, f"the skills name commands that do not exist: {sorted(unknown)}"

    @pytest.mark.parametrize("command", sorted(cli_commands()))
    def test_every_command_the_tool_has_is_named_somewhere(self, command):
        assert command in all_skill_text(), f"{command} is not mentioned in any skill"

    @pytest.mark.parametrize("command", sorted(cli_commands()))
    def test_no_command_is_documented_by_two_skills(self, command):
        # Owning a command means documenting its signature — a usage line naming it and
        # its placeholders. Mentioning one in prose is a cross-reference and is what
        # holds the set together, so it deliberately does not count as ownership.
        owners = [name for name in ALL_SKILLS if documents(skill_body(name), command)]

        assert len(owners) <= 1, f"{command} has its signature in {owners}"


class TestTheEntryIsSafeAlone:
    """R5.2: a harness may load the entry and nothing else."""

    def test_it_requires_a_dry_run_before_the_first_paid_call(self):
        text = entry_text()

        assert "--dry-run" in text
        assert "wait" in text.lower()

    def test_it_says_a_failed_generation_is_charged(self):
        assert "failed generation is charged" in entry_text()

    def test_it_points_at_the_ledger_for_what_has_been_spent(self):
        assert "pixellab-cli ledger" in entry_text()

    def test_it_names_the_pro_tools_commands(self):
        text = entry_text()

        assert "Pro Tools" in text
        assert "object new" in text

    def test_it_says_animation_costs_per_direction(self):
        assert "per direction" in entry_text()

    def test_it_offers_the_budget_flag(self):
        assert "--max-generations" in entry_text()

    def test_it_names_both_variables(self):
        text = entry_text()

        assert "PIXELLAB_SECRET" in text
        assert "FAL_KEY" in text

    def test_it_says_where_the_values_come_from(self):
        text = entry_text()

        assert "pixellab.ai/account" in text
        assert "fal.ai/dashboard/keys" in text

    def test_it_forbids_printing_a_credential(self):
        assert "never read, print, echo" in entry_text().lower()

    def test_it_tells_the_agent_not_to_name_a_route(self):
        assert "Pass `--route` only when the person named one" in entry_text()

    def test_it_tells_the_agent_not_to_guess_a_limit(self):
        assert "do not guess a limit" in entry_text().lower()

    def test_it_explains_how_to_resume_a_stopped_recipe(self):
        text = entry_text()

        assert "recipe resume" in text
        assert "recipe.json" in text

    def test_it_says_where_the_output_lands(self):
        assert "pixellab-out/" in entry_text()


class TestNoCredentialLeaks:
    def test_nothing_looks_like_a_credential(self):
        assert not re.search(r"\b(sk|fal|pl)-[A-Za-z0-9]{16,}", all_skill_text())


class TestTheInstalledCopyMatchesThePackagedOne:
    """This repository's own skills are the output of `pixellab-cli setup --claude` here.

    Two copies of anything drift. The packaged ones are what ship and what every other
    project gets; if they ever disagree, this repository is testing skills nobody else
    has.
    """

    def test_the_same_skills_are_present(self):
        packaged = {path.name for path in PACKAGED.iterdir() if path.is_dir()}
        installed = {path.name for path in SKILLS_DIR.iterdir() if path.name.startswith("pixellab")}

        assert installed == packaged

    @pytest.mark.parametrize("name", (ENTRY_SKILL, *CATEGORY_SKILLS))
    def test_every_packaged_file_is_installed_unchanged(self, name):
        source = PACKAGED / name
        packaged = {
            found.relative_to(source): found.read_text(encoding="utf-8")
            for found in source.rglob("*")
            if found.is_file()
        }
        destination = SKILLS_DIR / name
        installed = {
            found.relative_to(destination): found.read_text(encoding="utf-8")
            for found in destination.rglob("*")
            if found.is_file()
        }

        assert installed == packaged


class TestTheHelpIsTheCurrentList:
    """R5.12. A skill is written once and read for as long as it is installed, so the
    options it names are a version behind from the first release after it. The help is
    free, local and current — `art concept --transparent` was in the tool long before
    anybody read it off a page."""

    def test_the_entry_sends_the_agent_to_the_help(self):
        body = entry_text()

        assert "--help" in body
        assert "free" in body.lower()

    @pytest.mark.parametrize("name", CATEGORY_SKILLS)
    def test_every_category_skill_names_the_help(self, name):
        """A category skill is where the options are listed, which is where the
        reminder has to be: an agent that loaded only this one still gets it."""
        assert "--help" in skill_body(name)

    def test_the_harness_block_carries_it_too(self):
        """An agent whose harness loads a skill only when it judges it relevant reads
        this block every session and may never load a skill at all."""
        from pixellab_cli.harness import block_body

        assert "--help" in block_body(None)


class TestNothingShipsUntested:
    """The animation skill was packaged and installed for five releases while every
    test in this file walked past it, because the list above is written by hand and
    the shipped set is not. One missing name is a whole skill nobody checks."""

    def test_every_packaged_skill_is_named_here(self):
        from pixellab_cli.harness import packaged_skills

        assert set(packaged_skills()) == set(ALL_SKILLS)


class TestAPriceNamesACommand:
    """`ui` was listed as a Pro Tools route, and then `ui` became a group whose other
    two commands are free. Nothing caught it, because a group's name reads as a command
    everywhere else in this file. A price is quoted against what a person types, so
    every name in a price list has to be a leaf command."""

    PRICED = re.compile(r"Pro Tools[^\n|]*[:|]([^\n]*)")

    def priced_names(self, body: str) -> set[str]:
        """Every backticked command named on a line that quotes the Pro Tools price."""
        named: set[str] = set()
        for line in self.PRICED.findall(body):
            for quoted in re.findall(r"`([^`]+)`", line):
                # `sprite` with several `--style` is one entry in two spans: a flag is
                # not a command and is not what this is checking.
                if not quoted.startswith("-"):
                    named.add(quoted)
        return named

    def sources(self) -> dict[str, str]:
        from pixellab_cli.harness import block_body

        return {
            "the harness block": block_body(None),
            "the entry skill": entry_text(),
            "the cost reference": (REFERENCES / "costs.md").read_text(encoding="utf-8"),
        }

    def test_each_source_quotes_a_price_against_something(self):
        """A regex that matches nothing would pass every assertion below."""
        for where, body in self.sources().items():
            assert self.priced_names(body), f"no priced command found in {where}"

    def test_every_priced_name_is_a_command_somebody_can_type(self):
        commands = cli_commands()
        for where, body in self.sources().items():
            for name in sorted(self.priced_names(body)):
                assert name in commands, f"{where} prices {name!r}, which is not a command"


class TestAPoseIsMadeFromTheIdle:
    """A state is a character with its own id, so which one a pose is made *from* is a
    choice nobody was told how to make: the idle, so every pose has one ancestor and
    one palette carried forward from the same frame."""

    def body(self) -> str:
        return skill_body("pixellab-cli-animation")

    def test_the_skill_says_the_pose_comes_off_the_idle(self):
        assert "idle-state-id" in self.body()

    def test_the_order_makes_the_idle_before_the_poses(self):
        body = self.body()
        idle = body.index("the idle, once, off the base character")
        pose = body.index("the pose that motion needs")
        assert idle < pose
