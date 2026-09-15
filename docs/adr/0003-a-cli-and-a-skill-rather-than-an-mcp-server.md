---
status: accepted
date: 2026-09-14
---

# 0003 — A CLI and a skill, rather than an MCP server

## Context

The tool has two callers: a person at a terminal, and an agent working on a game. An MCP
server would serve the second natively — tools appear in the agent's tool list with typed
arguments. A CLI serves the first natively and the second through whatever shell the
agent already has.

MCP costs a running process, a transport, a client configuration per agent, and a tool
schema that has to be kept in step with the commands. It also puts every tool description
into the agent's context whether or not the session is about art.

A skill costs one directory of Markdown. It loads when the work is about generating
assets and is absent otherwise, and what it teaches is the CLI — which means the person
and the agent are driving exactly the same code path, with the same validation and the
same ledger entries.

## Decision

Ship a CLI, `pixellab`, and a skill that teaches an agent to use it. No MCP server.

## Consequences

An agent without shell access cannot use this tool. That is the real cost, and it is
accepted: the agents this is built for have Bash.

Because the skill's only interface is the CLI, the CLI's own help output and error
messages are part of the product rather than an afterthought — a wrong invocation has to
explain itself well enough that the agent recovers without the skill being reloaded.

Nothing here forecloses an MCP server later. It would be a thin front over the same
commands, and the route table, ledger and workspace layout are all indifferent to which
one calls them.
