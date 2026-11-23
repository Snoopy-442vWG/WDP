# ACMI calibration tools

`parse_acmi.py` pulls every bomb release out of a Tacview / DKS-telemetry ACMI (text format, unzipped):
the bomb's trajectory, the launching A-10 and its state around release, and nearby ground objects for terrain height.
`calibrate.py` compares WDP's bomb model with each drop.

```
unzip recording.zip.acmi -d x
python parse_acmi.py x/<file>.txt.acmi drops.json
python calibrate.py drops.json
```

## Results — 2026-11-21 ETAR recording (DCS 2.9.31), 12 drops (4 BDU-50LD, 8 Mk-82)

| | Result |
|---|---|
| Drag | `cd_scale` **0.67** on the baseline Mk-82 curve. Started from each bomb's own release velocity, WDP predicts impact within 8 ft along track (RMS 4 ft) at 3,300–7,700 ft range, and time of flight within 0.01 s RMS. |
| Ejection velocity | 0–8 ft/s body-down, mean **4.2 ft/s** (was 10 ft/s). Scatter is probably release G (pilots not exactly 1 G). |
| Angle of attack | Not calibrated: the recording has no G or gross weight. Measured pitch − flight path ranged 18–65 mils. Needs the controlled test drops (`tools/dcs/`). |
| BDU-50LD vs Mk-82 | Fly the same in DCS (one model fits both). |

Effect on a sled (1,500 ft target, 20 °C): with the DCS calibration bombs carry ~60 ft further than the CWDS
(real-world) numbers, so total mils come out ~8 mils lower than the battle books, e.g. 82 30DB1 191 → 183,
82 45DB2 177 → 169. DTOF is unchanged within 0.05 s.
