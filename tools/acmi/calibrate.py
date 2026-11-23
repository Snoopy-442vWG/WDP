"""Compare WDP's bomb model with real DCS drops extracted by parse_acmi.py, and fit drag scale + ejection velocity.

usage: python calibrate.py drops.json
"""
import sys, os, json, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "prototype"))
from engine import Atmos, mk82_ld, G, KT

FT = 3.28084


def linfit(ts, ys, t0):
    """least-squares line; returns (value at t0, slope)"""
    n = len(ts); mt = sum(ts) / n; my = sum(ys) / n
    sxx = sum((t - mt) ** 2 for t in ts) or 1e-9
    b = sum((t - mt) * (y - my) for t, y in zip(ts, ys)) / sxx
    return my + b * (t0 - mt), b


def quadfit(ts, ys, t0):
    """least-squares quadratic about t0; returns (value, first derivative) at t0"""
    xs = [t - t0 for t in ts]
    S = [sum(x ** k for x in xs) for k in range(5)]
    T = [sum(y * x ** k for x, y in zip(xs, ys)) for k in range(3)]
    A = [[S[0], S[1], S[2]], [S[1], S[2], S[3]], [S[2], S[3], S[4]]]
    # solve 3x3
    import copy
    M = [r[:] + [T[i]] for i, r in enumerate(A)]
    for i in range(3):
        p = max(range(i, 3), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        for r in range(3):
            if r != i:
                f = M[r][i] / M[i][i]
                M[r] = [a - f * b for a, b in zip(M[r], M[i])]
    c = [M[i][3] / M[i][i] for i in range(3)]
    return c[0], c[1]


def fly(w, atm, pos, vel, wind, z_gnd, dt=0.005):
    """3-D point-mass bomb from pos (ft: e, n, z) with velocity vel (ft/s) to z_gnd. Returns tof, e, n."""
    x, y, z = pos; vx, vy, vz = vel; t = 0.0
    m, A = w.mass_slug, w.area_ft2
    def acc(z, vx, vy, vz):
        rx, ry, rz = vx - wind[0], vy - wind[1], vz
        V = math.sqrt(rx * rx + ry * ry + rz * rz)
        k = 0.5 * atm.rho(z) * V * w.cd(V / atm.a(z)) * A / m
        return -k * rx, -k * ry, -k * rz - G
    while True:
        s = (x, y, z, vx, vy, vz)
        def f(s):
            a = acc(s[2], s[3], s[4], s[5]); return (s[3], s[4], s[5]) + a
        k1 = f(s); k2 = f(tuple(a + dt / 2 * b for a, b in zip(s, k1)))
        k3 = f(tuple(a + dt / 2 * b for a, b in zip(s, k2))); k4 = f(tuple(a + dt * b for a, b in zip(s, k3)))
        n = tuple(a + dt / 6 * (b + 2 * c + 2 * d + e) for a, b, c, d, e in zip(s, k1, k2, k3, k4))
        if n[2] <= z_gnd:
            fr = (s[2] - z_gnd) / (s[2] - n[2])
            return t + fr * dt, s[0] + fr * (n[0] - s[0]), s[1] + fr * (n[1] - s[1])
        x, y, z, vx, vy, vz = n; t += dt


def analyse(path):
    D = json.load(open(path))
    sl_temp = D["meta"]["temperature"]
    atm = Atmos.for_surface_temp(0.0, sl_temp)
    rows = []
    for d in D["drops"]:
        t0 = d["t_release"]
        # wind (meteorological 'from' direction), m/s -> ft/s toward
        wd, ws = math.radians(d["wind_dir"] or 0), (d["wind_speed"] or 0) * FT
        wind = (-ws * math.sin(wd), -ws * math.cos(wd))
        # aircraft velocity at release (linear fit over the 0.4 s before)
        ac = [s for s in d["aircraft"] if t0 - 0.45 <= s[0] <= t0 + 0.01]
        if len(ac) < 3: continue
        ts = [s[0] for s in ac]
        _, ve = linfit(ts, [s[2] * FT for s in ac], t0)
        _, vn = linfit(ts, [s[3] * FT for s in ac], t0)
        _, vz = linfit(ts, [s[1] * FT for s in ac], t0)
        pitch = ac[-1][5]; roll = ac[-1][4]
        # bomb state at release (quadratic fit over first 0.6 s)
        bs = [s for s in d["bomb"] if s[0] <= t0 + 0.6]
        bt = [s[0] for s in bs]
        be, bve = quadfit(bt, [s[2] * FT for s in bs], t0)
        bn, bvn = quadfit(bt, [s[3] * FT for s in bs], t0)
        bz, bvz = quadfit(bt, [s[1] * FT for s in bs], t0)
        # impact: extrapolate the last two samples to terrain height
        gnd = d["ground_near_impact"][0][1] * FT if d["ground_near_impact"] else d["bomb"][-1][1] * FT
        a, b = d["bomb"][-2], d["bomb"][-1]
        za, zb = a[1] * FT, b[1] * FT
        fr = (za - gnd) / (za - zb) if za != zb else 1.0
        ie = (a[2] + fr * (b[2] - a[2])) * FT; inn = (a[3] + fr * (b[3] - a[3])) * FT
        it = a[0] + fr * (b[0] - a[0])
        # geometry along the aircraft ground track
        trk = math.atan2(ve, vn)
        def along(e, n): return (e - be) * math.sin(trk) + (n - bn) * math.cos(trk)
        def cross(e, n): return (e - be) * math.cos(trk) - (n - bn) * math.sin(trk)
        # air-relative state
        ae, an = ve - wind[0], vn - wind[1]
        tas = math.sqrt(ae * ae + an * an + vz * vz)
        fpa = math.degrees(math.atan2(vz, math.hypot(ae, an)))
        # ejection: bomb velocity minus aircraft velocity
        dve, dvn, dvz = bve - ve, bvn - vn, bvz - vz
        rows.append(dict(weapon=d["weapon"], pilot=d["pilot"], t0=t0, rel_msl=bz, gnd=gnd, rel_agl=bz - gnd,
                         tas_kt=tas / KT, kcas=None, fpa=fpa, pitch=pitch, aoa_est=pitch - fpa, roll=roll,
                         ac_v=(ve, vn, vz), bomb_v=(bve, bvn, bvz), bomb_p=(be, bn, bz), wind=wind,
                         eject=(dve, dvn, dvz), tof=it - t0, rng=along(ie, inn), xtrk=cross(ie, inn),
                         impact_gap_ft=zb - gnd))
    return rows, atm


def predict(r, atm, cd_scale=1.0, v_ej=None):
    w = mk82_ld(cd_scale=cd_scale)
    if v_ej is None:                         # start from the bomb's own measured velocity (tests drag only)
        vel = r["bomb_v"]
    else:                                    # aircraft velocity + ejection v_ej along body-down normal
        ve, vn, vz = r["ac_v"]
        V = math.sqrt(ve * ve + vn * vn + vz * vz); h = math.hypot(ve, vn)
        g = math.atan2(-vz, h)               # dive angle (positive down)
        ue, un = ve / h, vn / h
        vel = (ve - v_ej * math.sin(g) * ue, vn - v_ej * math.sin(g) * un, vz - v_ej * math.cos(g))
    tof, e, n = fly(w, atm, r["bomb_p"], vel, r["wind"], r["gnd"])
    trk = math.atan2(r["ac_v"][0], r["ac_v"][1])
    be, bn, _ = r["bomb_p"]
    rng = (e - be) * math.sin(trk) + (n - bn) * math.cos(trk)
    return tof, rng


if __name__ == "__main__":
    rows, atm = analyse(sys.argv[1])
    print(f"{'weapon':9s} {'pilot':11s} {'AGL':>5} {'KTAS':>4} {'FPA':>6} {'pitch':>6} {'AoA':>5} {'roll':>5} "
          f"{'eject n':>7} {'TOF':>5} {'pred':>5} {'RNG':>6} {'pred':>6} {'err':>5}  gap")
    for r in rows:
        ve, vn, vz = r["ac_v"]; h = math.hypot(ve, vn); g = math.atan2(-vz, h)
        de, dn, dz = r["eject"]
        # ejection component along body-down normal (-sin g * track, -cos g * up)
        ue, un = ve / h, vn / h
        ej = -(de * ue + dn * un) * math.sin(g) - dz * math.cos(g)
        r["ej_n"] = ej
        tp, rp = predict(r, atm)
        print(f"{r['weapon']:9s} {r['pilot'][:11]:11s} {r['rel_agl']:5.0f} {r['tas_kt']:4.0f} {r['fpa']:6.1f} "
              f"{r['pitch']:6.1f} {r['aoa_est']:5.1f} {r['roll']:5.1f} {ej:7.1f} {r['tof']:5.2f} {tp:5.2f} "
              f"{r['rng']:6.0f} {rp:6.0f} {rp - r['rng']:5.0f}  {r['impact_gap_ft']:.0f}")
    json.dump([{k: v for k, v in r.items()} for r in rows], open("calib_rows.json", "w"))
