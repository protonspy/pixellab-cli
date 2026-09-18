# Agent skill — tasks

## 1 · The skill

- [x] 1.1 (Unit) Write SKILL.md: the description that says when to use it, the asset-to-command routing table, and the credential rule — R1.1, R1.2, R3.1, R3.2, R4.1
- [x] 1.2 (Unit) Write the spending rule: dry run first, show the estimate, wait for agreement, and what a failed or unresolved call means — R2.1, R2.2, R2.3
  _Depends 1.1_
- [x] 1.3 (Unit) Write references/commands.md and references/choosing.md, keeping the detail out of the body — R1.3, R4.2
  _Depends 1.1_
- [x] 1.4 (Unit) Teach the new commands and their tiers — R1.1, R1.3
  _Reason five commands added after delivery_
- [ ] 1.5 (Unit) Split the packaged skill into an entry and five category skills — R5.1
      R5.3
  _Status removed_
  _Reason citation wrapped past the line limit, so R5.3 was unreachable; replaced by 1.8_
- [x] 1.6 (Unit) Keep money, credentials and workspace in the entry skill — R5.2
  _Reason the skill grew past 800 lines and a tileset request paid for the character workflow_
- [x] 1.7 (Unit) Give each category skill the workflow its category needs — R5.4
  _Reason the skill grew past 800 lines and a tileset request paid for the character workflow_
- [x] 1.8 (Unit) Split the packaged skill by category — R5.1, R5.3
  _Reason replaces 1.5_
- [x] 1.9 (Unit) Say when fal earns its cost against PixelLab direct — R1.4
  _Reason two providers make images and the choice is a cost decision_

## 2 · Holding it true

- [x] 2.1 (TDD) Assert that every command the skill names exists in the CLI, and that every command the CLI exposes is named somewhere in the skill — R1.1
  _Depends 1.3_
- [x] 2.2 (Unit) Install every packaged skill, replacing each one it owns — R5.5
  _Depends 1.8_
  _Reason installing six skills is not installing one six times_
- [x] 2.3 (TDD) Report an installed skill this tool no longer ships — R5.6
  _Depends 2.2_
  _Reason installing six skills is not installing one six times_
