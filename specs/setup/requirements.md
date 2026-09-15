---
autonomy: auto
ci: wait
---

# Setup — requirements

## Purpose

One command that takes someone from an installed CLI to a working agent: the skill
where their harness looks for it, and the two credentials stored. Three harnesses,
and none of them looks in the same place or reads the same format — which is the
whole reason this is a command rather than a paragraph in the README.

## R1 · Installing

- **R1.1** When asked to set up a harness, the setup command shall write the agent instructions where that harness reads them, and shall report every path it wrote.
- **R1.2** Where no harness is named, the setup command shall offer the harnesses it finds evidence of in the target directory and in the user's home.
- **R1.3** The setup command shall install into the working directory by default, and into the user's home where a global install is asked for.
- **R1.4** The setup command shall leave the parts of a file it did not write untouched, replacing only the region it owns.
- **R1.5** When run a second time with the same arguments, the setup command shall produce the same result as the first without duplicating anything it wrote.
- **R1.6** If a path it would write is not writable, then the setup command shall say which path and continue with the harnesses that remain.

## R2 · Credentials

- **R2.1** The setup command shall report, for each credential, whether it is already resolved and from which source, before asking for anything.
- **R2.2** Where a credential is already resolved, the setup command shall not ask for it.
- **R2.3** When asking for a credential, the setup command shall read it without echoing it and shall write it to the credentials file in the user's home.
- **R2.4** The setup command shall accept a credential being declined and shall finish the rest of the work.

## R3 · Running without a person

- **R3.1** While a non-interactive run is asked for, the setup command shall install what was named and ask nothing.
- **R3.2** If a non-interactive run names no harness, then the setup command shall say that a harness must be named and shall write nothing.

## R4 · Saying what happened

- **R4.1** The setup command shall report what it wrote, what it skipped and why, and what is still missing before the tool can generate anything.

## Out of scope

- Installing the CLI itself. That is `uv tool install`, and a tool that installs itself is a tool that was already installed.
- Any harness beyond Claude Code, Codex and opencode.
- Editing a harness's own settings — model choice, permissions, MCP servers. This writes instructions and credentials, nothing else.
