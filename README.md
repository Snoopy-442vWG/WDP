# WDP — Weapons Delivery Planner (A-10C, DCS World)

A replacement for the DAPS spreadsheet. WDP builds Z-sled delivery profiles for the DCS A-10C II for every
munition, including the GAU-8, and exports them for JAFDTC to load into the jet's DSMS.

## Status
- `prototype/` — Python version of the calculation engine (Mk-82 LD), checked against the 23FG Battle Book
  (CWDS) sleds. See `prototype/validation_mk82ld.md`. This will be ported to C# for the Windows app.
- Windows app (C#/WinUI, based on JAFDTC) — not started yet.

## Prototype
```
cd prototype
python run.py          # compare against the 23FG CWDS Mk-82 LD sleds
python demo_elev.py    # target elevation / temperature / SEM examples
```

## Data sources
- 476TTP 3-3.A10C (sled definitions, SEM rules)
- 23FG A-10 Battle Book (CWDS reference sleds) and 76 vFS A-10C Battle Book
- DCS weapon data via dcs-lua-datamine (Quaggles)
