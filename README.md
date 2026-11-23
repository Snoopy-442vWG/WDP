# WDP — Weapons Delivery Planner (A-10C, DCS World)

A replacement for the DAPS spreadsheet. WDP builds Z-sled delivery profiles for the DCS A-10C II for every
munition, including the GAU-8, and exports them for JAFDTC to load into the jet's DSMS.

## What WDP will do
- **Z-sleds for every A-10C munition**, including the GAU-8, rockets, unguided bombs and guided weapons.
- **Target elevation and temperature inputs.** Sleds are planned above the target; altitudes are shown in MSL (what the
  altimeter reads) with AGL alongside. True airspeed, time of flight, mils, AOD, IHP/IPP and wind corrections are
  recalculated for the air at that elevation and temperature.
- **Default SEM by dive angle.** 30° or steeper → CLB (the jet's name for the 3-3 climbing SEM). TRN/TLT are flagged
  if planned above 20° of dive (3-3 5.6). 20° or shallower: CLB for low-drag weapons, TLT for high-drag. The planner
  can override.
- **Pop-up attack diagram** for each profile.
- **PNG download of each Z-sled** (and pop diagram), for attaching to the mission data card.
- **Export to JAFDTC.** Profile data (name, munition, SEM, min alt, DTOF, ripple qty/feet) plus the sled PNG, for
  JAFDTC to load into the jet's DSMS.

## Status
- `prototype/` — Python version of the calculation engine (Mk-82 LD), checked against the 23FG Battle Book
  (CWDS) sleds. See `prototype/validation_mk82ld.md`. This will be ported to C# for the Windows app.
- `prototype/sled_png.py` — first version of the Z-sled PNG export (76 vFS battle book layout).
- `tools/dcs/` — DCS mission script that logs weapon releases and impacts for calibration test drops.
- Pop-up diagram — not started yet.
- Windows app (C#/WinUI, based on JAFDTC) — not started yet.

## Prototype
```
cd prototype
python run.py          # compare against the 23FG CWDS Mk-82 LD sleds
python demo_elev.py    # target elevation / temperature / SEM examples
python sled_png.py     # render a sample Z-sled PNG (see samples/)
```

## Data sources
- 476TTP 3-3.A10C (sled definitions, SEM rules)
- 23FG A-10 Battle Book (CWDS reference sleds) and 76 vFS A-10C Battle Book
- DCS weapon data via dcs-lua-datamine (Quaggles)
