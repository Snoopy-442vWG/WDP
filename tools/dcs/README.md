# WDP drop logger — calibration test drops

`wdp_droplog.lua` records every weapon release and impact into DCS's own log file. No Tacview or DKS needed.
For each weapon it records:

- **At release:** position, altitude, terrain height, true velocity vector (so the real flight-path angle, not pitch),
  true airspeed, groundspeed, pitch, roll, heading, angle of attack, temperature, pressure and wind.
- **In flight:** the weapon's position every 0.5 s.
- **At impact:** the impact point and terrain height, time of flight, and range/cross-track from the release point.

## Setting up the test mission

1. Mission Editor → new mission → any map with **flat ground** (a dry lake bed or desert works well).
2. Weather: **15 °C, no wind, no turbulence**. Note the QNH.
3. Add an A-10C II (Player or Client) with Mk-82 LD / BDU-50LD on parent stations (3, 4, 8, 9 or 5, 7), ~36,000 lb.
4. Triggers → **ONCE** → condition **TIME MORE (1)** → action **DO SCRIPT FILE** → `wdp_droplog.lua`.
5. Save, then fly. A message appears at mission start: *"WDP drop logger running"*.

## What to drop (singles unless noted)

You don't need to hit anything, and you don't need to fly the profiles perfectly. The logger records the actual
release conditions.

| # | Delivery | Release (above ground) | Airspeed |
|---|----------|-------------------------|----------|
| 1–3 | Level | ~1,000 / 3,000 / 5,000 ft | 300 KIAS |
| 4–5 | 30° dive | ~2,800 ft | 350 KIAS |
| 6–7 | 45° dive | ~4,200 ft | 350 KIAS |
| 8 | 2-bomb ripple, 70 ft | 30° dive, ~3,200 ft | 350 KIAS |

Wings level and 1 G at release (no pulling).

## Sending the results

Quit DCS (so the log is complete), then send `Saved Games\DCS\Logs\dcs.log`
(or `Saved Games\DCS.openbeta\Logs\dcs.log`). All the logger's lines start with `WDP,`.

The same script works for rockets and the gun later (it logs any weapon release).
