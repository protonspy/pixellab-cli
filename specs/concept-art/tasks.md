# Concept art — tasks

## 1 · Generating

- [x] 1.1 (Unit) Generate a concept image on a named variant, writing every image returned with its manifest — R1.1, R1.3, R1.4
- [x] 1.2 (Unit) Accept the quality, size, background and count options, and let the model's own validation reject a value it does not allow — R1.2
  _Depends 1.1_
- [x] 1.3 (Unit) Add the box art form, with cover defaults that can still be overridden — R3.1
  _Depends 1.1_

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
