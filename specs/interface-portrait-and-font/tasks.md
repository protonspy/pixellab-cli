# Interface, portrait and font — tasks

## 1 · Interface

- [x] 1.1 (Unit) Generate a UI panel from a style description with optional named elements, announcing the Pro Tools price — R1.1, R1.2
- [x] 1.2 (TDD) Choose between a panel and one element — R1.3
  _Reason generate-ui-v2 was absent from the catalog; see n-0034_
- [x] 1.3 (Unit) Take a concept image for one element — R1.4
  _Reason generate-ui-v2 was absent from the catalog; see n-0034_

## 2 · Fonts

- [x] 2.1 (Unit) Generate a pixel font with an explicit weight, announcing the fixed price — R2.2, R2.3
  _Depends 1.1_
- [x] 2.2 (TDD) Download the atlas and the font file from the finished job and write each with the right extension — R2.1
  _Depends 2.1_

## 3 · Portraits

- [x] 3.1 (Unit) Convert between a portrait and a character in the direction asked for, rejecting a size the route does not offer — R3.1, R3.2
  _Depends 1.1_

## 4 · Consent

- [x] 4.1 (Unit) Report the route and the arguments under a dry run, sending nothing — R4.1
  _Depends 1.1_

## 7 · The panel you already paid for

- [x] 7.1 (Unit) Add the UI asset list and detail routes to the catalogue — R1.5, R1.6
  _Reason the UI library routes were never reached and a lost panel meant paying again_
- [x] 7.2 (Unit) Make ui a group with ui new, and list the account's panels — R1.5
  _Depends 7.1_
  _Reason the UI library routes were never reached and a lost panel meant paying again_
- [x] 7.3 (Unit) Show one panel, write it, and say when it is not ready — R1.6, R1.7
  _Depends 7.1_
  _Reason the UI library routes were never reached and a lost panel meant paying again_
- [x] 7.4 (Unit) Teach the skill and the README the ui group — R1.5, R1.6
  _Depends 7.3_
  _Reason the UI library routes were never reached and a lost panel meant paying again_
