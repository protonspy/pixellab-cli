---
autonomy: auto
ci: wait
branch: feat/guard-the-character-flow
delivery: in-review
pr: 59
---

# Agent skill — requirements

## Purpose

The skill is the only interface an agent has to this tool, because there is no MCP
server. It has to teach enough that an agent asked for "a knight sprite" reaches the
right command with the right arguments, and — more importantly — does not spend money
the person did not agree to.

## R1 · Routing the request

- **R1.1** The agent skill shall map the kinds of asset a game needs to the command that makes each one.
- **R1.2** The agent skill shall state that the tool chooses the provider route, so that an agent does not name one unless the person did.
- **R1.3** The agent skill shall state which commands are cheap and which are Pro Tools priced.
- **R1.4** (ADDED) The agent skill shall say when a concept image on fal earns its cost against generating on PixelLab directly, and shall state that the fal path adds a paid conversion.

## R2 · Spending

- **R2.1** The agent skill shall require a dry run before the first paid call of a session, and shall require the person's agreement to the estimate.
- **R2.2** The agent skill shall state that a failed generation is charged, and that an unresolved call may have been charged.
- **R2.3** The agent skill shall direct an agent to the ledger command for what has been spent.

## R3 · Credentials

- **R3.1** The agent skill shall state which environment variables hold the credentials and where their values come from.
- **R3.2** The agent skill shall forbid reading, printing or echoing a credential value.

## R4 · Shape

- **R4.1** The agent skill shall carry a description that says when to use it.
- **R4.2** The agent skill shall keep the detail that is only needed sometimes in reference files rather than in the body.

## R5 · One skill per category

- **R5.1** (ADDED) The agent skill shall be a set of skills, each owning the commands of one asset category, plus one entry skill that routes to them.
- **R5.2** (ADDED) The entry skill shall carry the spending rule, the credential rule and the workspace conventions, so that an agent that loaded only the entry skill is still safe to run.
- **R5.3** (ADDED) The category skills shall between them name every command the tool exposes, and the agent skill shall give no command more than one owner.
- **R5.4** (ADDED) The category skill shall carry the workflow its category needs, in the order the steps are taken.
- **R5.5** (ADDED) When installing, the tool shall write every packaged skill, and shall replace the contents of each one it owns.
- **R5.6** (ADDED) If a skill directory from a previous installation is no longer packaged, then the tool shall say so rather than leaving it to be read as current instructions.

- **R5.7** (ADDED) The character skill shall carry the reference flow in the order its steps are taken — a concept or a box art, then a local inspect and trim, then the paid character call with that reference — and shall state that the paid call is not entered from anywhere else.
- **R5.8** (ADDED) When the flow reaches the paid character call, the character skill shall require the agent to ask first whether the full-size image is to be sent for a larger character, and whether it is to be converted to pixel art first.

- **R5.9** (ADDED) When installing for a harness that loads a skill only where it judges the skill relevant, the tool shall also write the rules that cost money if missed into the file that harness reads every session, and shall point that file at the skills.
- **R5.10** (ADDED) The entry skill shall state that a paid call needs the person's agreement on that call, and shall forbid treating an earlier agreement as covering a later call.

## Out of scope

- Teaching PixelLab's or fal's APIs. The skill teaches the CLI; the CLI owns the APIs.
- An MCP server. See `adr:0003-a-cli-and-a-skill-rather-than-an-mcp-server`.
