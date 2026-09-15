# Tiles and terrain — tasks

## 1 · Terrain

- [x] 1.1 (Unit) Generate a top-down tileset from a lower and an upper description, writing every tile returned — R1.1, R1.3
- [x] 1.2 (Unit) Generate a platformer tileset from a platform material — R1.2, R1.3
  _Depends 1.1_

## 2 · Tiles

- [x] 2.1 (Unit) Generate tile variants from a numbered description, announcing the Pro Tools price — R2.1
  _Depends 1.1_
- [x] 2.2 (Unit) Pass the connectable-set feature when a road, terrain or building set is asked for — R2.2
  _Depends 2.1_
- [x] 2.3 (Unit) Generate one isometric tile within the sizes that route accepts — R2.3
  _Depends 1.1_

## 3 · Map objects

- [x] 3.1 (Unit) Generate a transparent map prop, style-matched to a map image where one is given — R3.1
  _Depends 1.1_

## 4 · Reporting

- [x] 4.1 (Unit) Report the route, the cost and where the tiles landed, and send nothing under a dry run — R4.1, R4.2
  _Depends 1.1_
