---
autonomy: auto
ci: wait
branch: feat/foundation
delivery: in-review
pr: 1
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

## Out of scope

- Teaching PixelLab's or fal's APIs. The skill teaches the CLI; the CLI owns the APIs.
- An MCP server. See `adr:0003-a-cli-and-a-skill-rather-than-an-mcp-server`.
