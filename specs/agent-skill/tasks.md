# Agent skill — tasks

## 1 · The skill

- [x] 1.1 (Unit) Write SKILL.md: the description that says when to use it, the asset-to-command routing table, and the credential rule — R1.1, R1.2, R3.1, R3.2, R4.1
- [x] 1.2 (Unit) Write the spending rule: dry run first, show the estimate, wait for agreement, and what a failed or unresolved call means — R2.1, R2.2, R2.3
  _Depends 1.1_
- [x] 1.3 (Unit) Write references/commands.md and references/choosing.md, keeping the detail out of the body — R1.3, R4.2
  _Depends 1.1_
- [ ] 1.4 (Unit) Teach the new commands and their tiers — R1.1, R1.3
  _Reason five commands added after delivery_

## 2 · Holding it true

- [x] 2.1 (TDD) Assert that every command the skill names exists in the CLI, and that every command the CLI exposes is named somewhere in the skill — R1.1
  _Depends 1.3_
