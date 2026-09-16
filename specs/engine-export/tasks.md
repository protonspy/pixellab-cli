---
autonomy: auto
ci: wait
---

# Engine export — tasks

## 1 · The group

- [x] 1.1 (Unit) Add the `export` command group, writing the image and its JSON as a pair that never overwrites — R1.1, R1.2, R1.3
- [x] 1.2 (Unit) Refuse a file that is not a readable image, naming it, before anything is written — R1.4
  _Depends 1.1_

## 2 · The texture atlas

- [x] 2.1 (TDD) Place each frame on the composed image and record the rectangle it landed on — R2.1, R2.3
  _Depends 1.2_
- [x] 2.2 (Unit) Write the Hash index: frames by name, plus the image's own name and size — R2.1, R2.2, R2.6
  _Depends 2.1_
- [x] 2.3 (Unit) Take the frame names from a spritesheet layout where one is given — R2.4
  _Depends 2.2_
- [x] 2.4 (Unit) Refuse two frames that would share one name, naming both sources — R2.5
  _Depends 2.2_

## 3 · The tileset

- [x] 3.1 (Unit) Compose the tiles and write the standalone Tiled tileset beside them — R3.1, R3.3
  _Depends 1.2_
- [x] 3.2 (Unit) Refuse tiles that are not all one size, naming the sizes found — R3.2
  _Depends 3.1_
- [x] 3.3 (Unit) Say that the map is made in Tiled or in code, and write none — R3.4, R3.5
  _Depends 3.1_
