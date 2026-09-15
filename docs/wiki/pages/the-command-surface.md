# The command surface

Thirty-four commands over two providers, and they are all the same shape underneath.
Written after the tool existed, so that the next person changing it knows which
decisions live where rather than inferring it from thirteen modules.

## The shape every generation command has

```
parse the arguments        typer, in the command function
pick the route             routing.py, or the command names one directly
build the request          validate.py against the route in catalog.py
stop here if --dry-run     nothing sent, nothing recorded
hand it to the runner      run.py — ledger in, call, ledger out, files, manifest
print                      output.py, human or --json
```

Everything between "build the request" and "print" is shared. A new command is the
first two lines and a dictionary of arguments; if it needs more than that, the thing
it needs probably belongs in one of the shared modules.

## Where each kind of decision lives

| The decision | Where |
|---|---|
| What a route accepts, and its ceilings | `catalog.py`, checked against the vendored schema by the suite |
| Whether an argument is allowed | `validate.py` |
| Which of several routes to use | `routing.py` for images; the command itself elsewhere |
| How a request is sent, retried and polled | `pixellab.py` |
| How fal is called | `fal.py` |
| Where a file lands and what it is called | `workspace.py` |
| What is recorded, and when | `ledger.py` and `run.py` |
| What the person sees | `output.py` |

The one rule that holds it together: **a command never calls a provider client
directly.** It hands a function to `Runner.run`, which writes the intent line, makes
the call, and writes the outcome whether it succeeded or failed. There is therefore
no path to a paid call that skips the ledger — see [[generation-record]].

## Where the shape bends, and why

**A character is three calls.** `create-character-v3` returns an id and a job; the
rotations are URLs on `GET /characters/{id}`. So the function handed to the runner
does all three, and fills a `roles` list the runner reads afterwards to name the
files by direction.

**A font is two files with different extensions.** The atlas and the TTF come from
separate URLs on the finished job, and a `.ttf` written as `.png` is a file nobody
can use and nothing would warn about — so that command renames after the fact.

**A recipe is several runs sharing one directory.** Each step gets its own run id so
the ledger's intent and outcome lines still pair up, and its own manifest. The recipe
adds only the order, the carrying of one step's output into the next, and
`recipe.json` recording how far it got.

## What the commands deliberately do not do

They do not spell out enum values, size ceilings or provider quirks. Those live in
the route table, the validator rejects a wrong one for free, and the error names what
would have worked. A command that repeated them would be a second copy to drift —
which is the same reason the agent skill does not repeat them either.
