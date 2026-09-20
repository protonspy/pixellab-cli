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
- [x] 1.8 (TDD) Generate on PixelLab when fal has no credential — R6.1, R6.4
  _Reason adr:0010 makes fal optional_
- [x] 1.9 (Unit) Say when the fallback changes the kind of image — R6.2
  _Reason adr:0010 makes fal optional_

## 2 · Editing

- [x] 2.1 (Unit) Upload the local images, pass their URLs with the instruction, and write the result — R2.1
  _Depends 1.1_
- [x] 2.2 (Unit) Upload a mask where one is given, and check every file exists before the first upload — R2.2, R2.3
  _Depends 2.1_
- [x] 2.3 (Unit) Refuse the background form without fal rather than fall back — R6.1,
      R6.3
  _Reason the fallback is the defect this closes; see adr:0011_
- [x] 2.4 (Unit) Add the background form, transparent, on the edit model — R7.1, R7.2
  _Reason the pixel-art route redrew a composed image somebody paid for_

## 3 · Recording

- [x] 3.1 (Unit) Record every fal call in the ledger with the money it cost left empty — R4.1
  _Depends 1.1_
- [x] 3.2 (Unit) Report the model and arguments under a dry run, uploading nothing and calling nothing — R4.2
  _Depends 2.1_
- [x] 3.3 (Unit) Read the finished job's timing and record it as measured, leaving the cost unknown where the provider will not say — R4.3, R4.4
  _Depends 3.1_
  _Reason a fal call recorded nothing at all, so the one thing about it that can be known was not being asked for_
- [x] 3.4 (TDD) Fall back from a failure, recording both calls — R6.3
  _Reason adr:0010 makes fal optional_
