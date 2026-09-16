# Concept art — tasks

## 1 · Generating

- [x] 1.1 (Unit) Generate a concept image on a named variant, writing every image returned with its manifest — R1.1, R1.3, R1.4
- [x] 1.2 (Unit) Accept the quality, size, background and count options, and let the model's own validation reject a value it does not allow — R1.2
  _Depends 1.1_
- [x] 1.3 (Unit) Add the box art form, with cover defaults that can still be overridden — R3.1
  _Depends 1.1_
- [x] 1.4 (Unit) Add pixellab art anchor — R5.1, R5.2
  _Reason anchor asked for after delivery_
- [x] 1.5 (Unit) Take repeatable --reference on the generating forms, routing to the edit model of the same variant when any is given — R1.5, R1.6, R2.3
  _Depends 1.1_
  _Reason a reference image had to be reconstructed as a text description, so the result resembled the reference rather than matching it_
- [x] 1.6 (Unit) Keep the anchor's framing while taking the subject's appearance from the references — R5.3
  _Depends 1.5_
- [x] 1.7 (Unit) Send the middle tier by default and refuse one above the ceiling, naming what would have worked — R1.7, R1.8, R1.9, R3.1
  _Depends 1.1_
  _Reason box art defaulted to the top tier and every other form omitted the tier, so the provider applied its own, which is high_

## 2 · Editing

- [x] 2.1 (Unit) Upload the local images, pass their URLs with the instruction, and write the result — R2.1
  _Depends 1.1_
- [x] 2.2 (Unit) Upload a mask where one is given, and check every file exists before the first upload — R2.2, R2.3
  _Depends 2.1_

## 3 · Recording

- [x] 3.1 (Unit) Record every fal call in the ledger with its cost marked unknown — R4.1
  _Depends 1.1_
- [x] 3.2 (Unit) Report the model and arguments under a dry run, uploading nothing and calling nothing — R4.2
  _Depends 2.1_
