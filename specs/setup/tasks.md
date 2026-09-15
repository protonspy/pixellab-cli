# Setup — tasks

## 1 · The packaged skill

- [x] 1.1 (Unit) Move the skill into the package as data, and keep this repository's copy in step with a test — R1.1

## 2 · Writing a harness

- [x] 2.1 (TDD) Replace a managed block in a file, append it when absent, and leave the rest alone — R1.4, R1.5
  _Depends 1.1_
- [x] 2.2 (Unit) Install the skill directory for Claude Code, project and global — R1.1, R1.3
  _Depends 1.1_
- [x] 2.3 (Unit) Install the block and the references for Codex and opencode — R1.1, R1.3
  _Depends 2.1_
- [x] 2.4 (Unit) Add the opencode instructions entry where a config file exists — R1.1
  _Depends 2.3_
- [x] 2.5 (Unit) Report an unwritable path and carry on with the rest — R1.6
  _Depends 2.2_
- [x] 2.6 (TDD) Refuse a link, empty before filling, keep endings — R1.7, R1.8, R1.9
  _Reason security review found link following and a stale reinstall_

## 3 · The command

- [x] 3.1 (Unit) Add pixellab setup with a flag per harness and a global switch — R1.1, R1.3
  _Depends 2.2, 2.3_
- [x] 3.2 (Unit) Offer the harnesses there is evidence of when none is named — R1.2
  _Depends 3.1_
- [x] 3.3 (Unit) Resolve the credentials first, ask only for what is missing, take no for an answer — R2.1, R2.2, R2.3, R2.4
  _Depends 3.1_
- [x] 3.4 (Unit) Install what was named and ask nothing under a non-interactive run, refusing one that names no harness — R3.1, R3.2
  _Depends 3.1_
- [x] 3.5 (Unit) Report what was written, what was skipped, and what is still missing — R4.1
  _Depends 3.3, 3.4_
- [x] 3.6 (Unit) Report what reached the disk, before any failure — R1.10, R2.5
  _Reason code review found the report hidden by a later failure_
