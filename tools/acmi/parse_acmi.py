"""Extract bomb releases from a Tacview / DKS telemetry ACMI (text, FileVersion 2.x).

For every Weapon+Bomb object: its full trajectory, the launching aircraft (nearest fixed-wing at release) and that
aircraft's state around release. Output: JSON list of drops for calibrate.py.

usage: python parse_acmi.py recording.txt.acmi drops.json
"""
import sys, json, math

KEEP_TYPES = ("Weapon+Bomb", "Air+FixedWing", "Ground")


def parse(path):
    objs = {}          # live objects: id -> dict(meta, samples)
    done = []          # finished objects
    t = 0.0
    ref_lon = ref_lat = 0.0
    globals_ = {}
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        pending = ""
        for raw in fh:
            line = raw.rstrip("\n")
            if line.endswith("\\"):           # continued line
                pending += line[:-1] + "\n"; continue
            line = pending + line; pending = ""
            if not line or line.startswith("FileType") or line.startswith("FileVersion"):
                continue
            if line[0] == "#":
                t = float(line[1:]); continue
            if line[0] == "-":
                oid = line[1:].strip()
                o = objs.pop(oid, None)
                if o: o["removed"] = t; done.append(o)
                continue
            oid, _, rest = line.partition(",")
            props = split_props(rest)
            if oid == "0":
                globals_.update(props)
                if "ReferenceLongitude" in props: ref_lon = float(props["ReferenceLongitude"])
                if "ReferenceLatitude" in props: ref_lat = float(props["ReferenceLatitude"])
                continue
            o = objs.get(oid)
            if o is None or ("Type" in props and o["meta"].get("Type") and props["Type"] != o["meta"]["Type"]):
                if o is not None:
                    o["removed"] = t; done.append(o)
                o = objs[oid] = {"id": oid, "meta": {}, "samples": [], "last": [None] * 9, "removed": None}
            for k in ("Type", "Name", "Pilot", "Group", "Coalition"):
                if k in props: o["meta"][k] = props[k]
            for k in ("WindDirection", "WindSpeed"):
                if k in props: o["meta"][k] = float(props[k])
            if "T" in props:
                parts = props["T"].split("|")
                last = o["last"]
                if len(parts) == 9:
                    for i, p in enumerate(parts):
                        if p != "": last[i] = float(p)
                elif len(parts) == 3:
                    for i, p in enumerate(parts):
                        if p != "": last[i] = float(p)
                elif len(parts) == 5:   # lon|lat|alt|U|V
                    for i, p in zip((0, 1, 2, 6, 7), parts):
                        if p != "": last[i] = float(p)
                elif len(parts) == 6:   # lon|lat|alt|roll|pitch|yaw
                    for i, p in enumerate(parts):
                        if p != "": last[i] = float(p)
                typ = o["meta"].get("Type", "")
                if any(k in typ for k in KEEP_TYPES) and None not in last[:3]:
                    o["samples"].append([t] + list(last))
    for o in objs.values():
        done.append(o)
    return done, globals_, (ref_lon, ref_lat)


def split_props(s):
    out, cur, esc = {}, "", False
    items = []
    for ch in s:
        if esc: cur += ch; esc = False; continue
        if ch == "\\": esc = True; continue
        if ch == ",": items.append(cur); cur = ""; continue
        cur += ch
    items.append(cur)
    for it in items:
        k, _, v = it.partition("=")
        out[k] = v
    return out


def nearest(samples, t):
    best = None
    for s in samples:
        if best is None or abs(s[0] - t) < abs(best[0] - t): best = s
    return best


def main(src, dst):
    objs, glob, ref = parse(src)
    bombs = [o for o in objs if "Weapon+Bomb" in o["meta"].get("Type", "") and len(o["samples"]) >= 3]
    planes = [o for o in objs if "Air+FixedWing" in o["meta"].get("Type", "")]
    grounds = [o for o in objs if o["meta"].get("Type", "").startswith("Ground") and o["samples"]]
    drops = []
    for b in bombs:
        s0 = b["samples"][0]; t0 = s0[0]
        # launcher = fixed-wing with a sample within 0.3 s and nearest in space (U/V/alt)
        best, bd = None, 1e9
        for p in planes:
            ps = [s for s in p["samples"] if abs(s[0] - t0) < 0.3]
            if not ps: continue
            s = min(ps, key=lambda s: abs(s[0] - t0))
            if None in (s[7], s[8], s0[7], s0[8]): continue
            d = math.dist((s[7], s[8], s[3]), (s0[7], s0[8], s0[3]))
            if d < bd: best, bd = p, d
        if best is None or bd > 200: continue
        # aircraft samples from 3 s before to 1 s after release
        ac = [s for s in best["samples"] if t0 - 3 <= s[0] <= t0 + 1]
        # nearby ground objects -> terrain elevation at impact
        si = b["samples"][-1]
        gel = []
        for g in grounds:
            gs = g["samples"][0]
            if gs[7] is None: continue
            dd = math.hypot(gs[7] - si[7], gs[8] - si[8])
            if dd < 400: gel.append((dd, gs[3], g["meta"].get("Name")))
        gel.sort()
        drops.append(dict(
            bomb_id=b["id"], weapon=b["meta"].get("Name"), t_release=t0, t_removed=b["removed"],
            pilot=best["meta"].get("Pilot") or best["meta"].get("Group"), group=best["meta"].get("Group"),
            launcher_dist_m=bd,
            wind_dir=best["meta"].get("WindDirection"), wind_speed=best["meta"].get("WindSpeed"),
            bomb=[[s[0], s[3], s[7], s[8], s[5], s[9]] for s in b["samples"]],          # t, alt, U, V, pitch, hdg
            aircraft=[[s[0], s[3], s[7], s[8], s[4], s[5], s[6], s[9]] for s in ac],  # t, alt, U, V, roll, pitch, yaw, hdg
            ground_near_impact=gel[:5]))
    meta = dict(temperature=float(glob.get("Temperature", "nan")), qnh=float(glob.get("QNH", "nan")),
                title=glob.get("Title"), source=glob.get("DataSource"))
    json.dump(dict(meta=meta, drops=drops), open(dst, "w"))
    print(f"{len(drops)} drops written to {dst}")
    for d in drops:
        print(d["weapon"], d["pilot"], f"t={d['t_release']:.1f}", f"samples={len(d['bomb'])}",
              f"launcher {d['launcher_dist_m']:.0f} m", "ground:", d["ground_near_impact"][:1])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
