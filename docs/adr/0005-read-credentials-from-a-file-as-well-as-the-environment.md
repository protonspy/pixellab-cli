---
status: accepted
date: 2026-09-15
---

# 0005 — Read credentials from a file as well as the environment

## Context

Until now the tool read both credentials from environment variables and from nowhere
else. The reason is in `config.py`'s own first paragraph: a token in a file is a token
that gets committed.

That reason has not stopped being true. What it did not account for is the cost of the
alternative on the machines this runs on. On Windows an environment variable set with
`setx` does not reach a process that is already running, so adopting a key means
setting it and restarting the terminal, the editor, or an agent session. An agent
cannot set it at all without the value passing through its transcript, which is the one
place a credential must never be.

The work is also per project. Someone generating art for two games wants two fal
accounts, and an environment variable is per shell rather than per directory.

Three things make a file safe enough to be worth it, and all three are load-bearing:

- The default lives in the user's home directory, outside every repository.
- A project file is honoured, and carries values only. **A `*_command` field is read
  from the home file and ignored in a project file**, because a project file arrives
  with a clone: honouring a command there would make `git clone && pixellab sprite`
  arbitrary code execution.
- The environment still wins. CI exports a variable and no file on a runner can
  quietly take precedence over it.

## Decision

Read credentials from, in order: the environment, then the nearest `.pixellab.json`
found from the working directory upward, then `~/.pixellab.json`. First hit wins per
credential rather than per file, so a project may override one key and inherit the
other.

The file holds `pixellab_secret` and `fal_key` as values, or `pixellab_secret_command`
and `fal_key_command` naming a command whose standard output is the credential — the
latter only in the home file.

`pixellab config set <name>` writes it, prompting without echo. `pixellab config show`
reports which credentials are present and which source each came from, never a value.

Project files are searched from the working directory because that is where the game
is; this tool's own repository has nothing to do with it.

## Consequences

A credential can now sit on disk, which is what the previous decision refused. The
mitigations above are what makes it acceptable, and they are testable rather than
advisory: the command-in-a-project-file rule is a refusal with a test behind it, not a
line in a document.

`config show` naming the source matters more than it looks. With four places a value
can come from, "it is not picking up my key" becomes the common failure, and the answer
has to be readable without printing the secret.

A file is a second place to leak from. Anything that renders a credential still goes
through `redact()`, and `pixellab config show` prints presence and provenance only.

Superseding this would mean removing the file, which breaks every machine that adopted
it — so the format is a contract from the first release that carries it.
