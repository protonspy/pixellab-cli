---
autonomy: auto
ci: wait
branch: feat/engine-export
delivery: in-progress
---

# Engine export — requirements

Two documents a game engine loads without a conversion step: a texture atlas for
frames, and a Tiled tileset for tiles. Both are written locally, from files that
already exist, for nothing.

The shapes are fixed by `adr:0009-export-to-the-texturepacker-atlas-and-the-tiled-tileset`,
which also records why no map is written.

## 1 · The group

- **R1.1** The engine export commands shall complete without calling a provider, and shall write no ledger entry, because nothing is charged.
- **R1.2** When asked for an export, the engine export commands shall write the image and its JSON beside each other under the name given, and shall never overwrite a file already there.
- **R1.3** The JSON shall name its image by filename alone, so that the two can be moved together without the reference breaking.
- **R1.4** If a file given is not an image this tool can read, then the engine export commands shall name the file and say so, before writing anything.

## 2 · The texture atlas

- **R2.1** When asked for a texture atlas, the engine export commands shall compose the images given into one image and write the frame index beside it in the TexturePacker Hash shape.
- **R2.2** The engine export commands shall name each frame after the file it came from, without its extension.
- **R2.3** The engine export commands shall record, for each frame, its rectangle in the composed image, whether it is rotated, whether it is trimmed, the rectangle it occupies within its source, and its source size.
- **R2.4** Where a spritesheet layout is given, the engine export commands shall take the frame names from that layout rather than from the filenames.
- **R2.5** If two frames would carry the same name, then the engine export commands shall refuse and name both sources, because one key holding two frames loses one of them silently.
- **R2.6** The index shall record the composed image's filename and its size, so that a loader can check the pair matches.

## 3 · The tileset

- **R3.1** When asked for a tileset, the engine export commands shall compose the tiles given into one image and write the standalone Tiled tileset document beside it.
- **R3.2** If the tiles given are not all one size, then the engine export commands shall refuse and name the sizes found, because a tileset's grid is uniform by definition.
- **R3.3** The tileset document shall carry the tile size, the tile count, the column count, the image filename and the image size, and shall declare itself a tileset.
- **R3.4** The engine export commands shall write no map, because nothing here knows which tile belongs in which cell.
- **R3.5** Where a tileset is written, the engine export commands shall say that the map is made in Tiled or in code, so that its absence reads as a decision rather than as a missing file.
