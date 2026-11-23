"""DAPS-replacement prototype calculation engine (Python; will be ported to C#).
Units internally: feet, seconds, ft/s, degrees for angles at the interface.
"""
import math
from dataclasses import dataclass, field

G = 32.174           # ft/s^2
KT = 1.687810        # ft/s per knot
MIL_PER_DEG = 17.45  # 3-3 convention (1 deg = 17.45 mils)
R_AIR = 1716.49      # ft*lbf/(slug*R)

# ---------------------------------------------------------------- atmosphere
@dataclass
class Atmos:
    dT_C: float = 0.0  # temperature offset from ISA (deg C)

    @staticmethod
    def for_surface_temp(elev_ft, temp_c):
        return Atmos(temp_c - (15.0 - 0.0019812 * elev_ft))

    def T(self, h):   # Kelvin
        return 288.15 - 0.0019812 * h + self.dT_C
    def p(self, h):   # lbf/ft^2 (pressure altitude == geometric here)
        return 2116.22 * (1 - 6.87559e-6 * h) ** 5.25588
    def rho(self, h): # slug/ft^3
        return self.p(h) / (R_AIR * self.T(h) * 1.8)
    def a(self, h):   # speed of sound ft/s
        return 49.0223 * math.sqrt(self.T(h) * 1.8)
    def tas(self, kcas, h):
        """CAS (knots) -> TAS (ft/s), compressible."""
        a0, p0 = 1116.45, 2116.22
        vc = kcas * KT
        qc = p0 * ((1 + 0.2 * (vc / a0) ** 2) ** 3.5 - 1)
        M = math.sqrt(5 * ((qc / self.p(h) + 1) ** (2 / 7) - 1))
        return M * self.a(h)
    def density_alt(self, h):
        # altitude in ISA with same density
        rho = self.rho(h); lo, hi = -5000.0, 60000.0
        isa = Atmos(0)
        for _ in range(60):
            mid = (lo + hi) / 2
            if isa.rho(mid) > rho: lo = mid
            else: hi = mid
        return (lo + hi) / 2

# ---------------------------------------------------------------- weapons
@dataclass
class Weapon:
    name: str
    mass_kg: float
    caliber_m: float
    cd_table: list            # [(mach, cd)] based on caliber area
    cd_scale: float = 1.0     # tuning factor (fit to CWDS / DCS Tacview)
    v_eject_fps: float = 0.0  # ejector velocity normal to flight path
    high_drag: bool = False   # retarded delivery (Mk-82AIR open, etc.)
    # chute / retard (high drag) not yet modelled

    @property
    def mass_slug(self): return self.mass_kg * 2.20462 / G
    @property
    def area_ft2(self): return math.pi * (self.caliber_m * 3.28084) ** 2 / 4

    def cd(self, M):
        t = self.cd_table
        if M <= t[0][0]: return t[0][1] * self.cd_scale
        for (m0, c0), (m1, c1) in zip(t, t[1:]):
            if M <= m1:
                return (c0 + (c1 - c0) * (M - m0) / (m1 - m0)) * self.cd_scale
        return t[-1][1] * self.cd_scale

# Baseline Mk-82 LD drag-vs-Mach shape (approximate published shape for the
# low-drag GP bomb with fuze/lugs; absolute level is tuned by cd_scale).
MK82_CD = [(0.0, 0.20), (0.6, 0.20), (0.75, 0.21), (0.85, 0.26), (0.90, 0.33),
           (0.95, 0.45), (1.00, 0.55), (1.10, 0.60), (1.50, 0.52)]

def mk82_ld(**kw):
    # mass/caliber from DCS (dcs-lua-datamine weapons/bombs/Mk_82.lua)
    return Weapon("MK-82LD", 228.0, 0.273, MK82_CD, **kw)

# ---------------------------------------------------------------- trajectory
def drop(w: Weapon, atm: Atmos, h_rel_msl, tgt_msl, tas_fps, dive_deg,
         wind=(0.0, 0.0, 0.0), dt=0.01, crab=False):
    """Integrate bomb from release to target-plane impact.
    Frame: x along attack heading (ground), y right, z up. Aircraft velocity is
    tas along the air-mass flight path (dive) + wind. wind = (wx, wy, 0) ft/s.
    Returns dict: tof, x (bomb range), y (lateral), vimp."""
    g = math.radians(dive_deg)
    ux, uz = math.cos(g), -math.sin(g)           # flight path (air)
    nx, nz = -math.sin(g), -math.cos(g)          # body 'down' normal
    vx = tas_fps * ux + w.v_eject_fps * nx + wind[0]
    vy = 0.0 if crab else wind[1]   # crab: ground track held toward target
    vz = tas_fps * uz + w.v_eject_fps * nz
    x = y = 0.0; z = h_rel_msl; t = 0.0
    m, A = w.mass_slug, w.area_ft2

    def acc(z, vx, vy, vz):
        rx, ry, rz = vx - wind[0], vy - wind[1], vz
        V = math.sqrt(rx * rx + ry * ry + rz * rz)
        M = V / atm.a(z)
        k = 0.5 * atm.rho(z) * V * w.cd(M) * A / m
        return -k * rx, -k * ry, -k * rz - G

    while True:
        s = (x, y, z, vx, vy, vz)
        def f(s):
            ax, ay, az = acc(s[2], s[3], s[4], s[5])
            return (s[3], s[4], s[5], ax, ay, az)
        k1 = f(s)
        k2 = f(tuple(a + dt / 2 * b for a, b in zip(s, k1)))
        k3 = f(tuple(a + dt / 2 * b for a, b in zip(s, k2)))
        k4 = f(tuple(a + dt * b for a, b in zip(s, k3)))
        n = tuple(a + dt / 6 * (b + 2 * c + 2 * d + e) for a, b, c, d, e in zip(s, k1, k2, k3, k4))
        if n[2] <= tgt_msl:
            fr = (s[2] - tgt_msl) / (s[2] - n[2])
            x = s[0] + fr * (n[0] - s[0]); y = s[1] + fr * (n[1] - s[1])
            t += fr * dt
            return dict(tof=t, x=x, y=y)
        x, y, z, vx, vy, vz = n; t += dt

# ---------------------------------------------------------------- aircraft
# A-10C 1G angle-of-attack (mils, ZSL to relative wind) vs KIAS (rows) and
# pressure altitude (cols), from DAPS CALCULATIONS!AOA_DATA. Scaled by
# load factor (cos dive in a steady dive) and gross weight.
AOA_KIAS = [200, 225, 250, 275, 300, 325, 350, 375, 400, 425, 450]
AOA_ALT = [20000, 17500, 15000, 12500, 10000, 7500, 5000, 2500, 0]
AOA_MILS = [
 [131.9,131.5,131.1,130.7,130.2,129.7,129.2,128.7,128.3],
 [107.6,106.7,105.8,104.9,104.0,103.1,102.5,101.9,101.3],
 [99.7,89.7,88.7,87.6,86.5,85.4,84.7,83.9,83.1],
 [89.1,79.1,77.6,76.1,74.6,73.1,72.2,71.3,70.4],
 [75.0,72.9,70.8,68.7,66.6,64.5,63.4,62.4,61.4],
 [72.5,70.0,67.3,64.8,62.2,59.6,58.0,56.5,55.0],
 [72.1,69.1,66.1,62.9,59.8,56.7,54.7,52.8,50.9],
 [65.5,63.7,61.8,59.9,58.0,56.1,53.8,51.4,49.0],
 [58.9,58.6,58.3,58.0,57.6,57.2,54.3,51.3,48.3],
 [56.4,55.9,55.4,55.0,54.7,54.4,52.8,51.2,49.6],
 [53.7,53.2,52.9,52.6,52.3,52.0,51.7,51.4,51.1]]

def _interp(xs, ys, x):
    if xs[0] > xs[-1]:
        xs, ys = xs[::-1], ys[::-1]
    if x <= xs[0]: return ys[0]
    for i in range(len(xs) - 1):
        if x <= xs[i + 1]:
            return ys[i] + (ys[i + 1] - ys[i]) * (x - xs[i]) / (xs[i + 1] - xs[i])
    return ys[-1]

@dataclass
class Aircraft:
    gw_lb: float = 36000.0
    ref_gw_lb: float = 36000.0
    aoa_scale: float = 1.0
    aoa_bias: float = 0.0
    def aoa_mils(self, kias, alt_msl, nz):
        row = [_interp(AOA_ALT, [AOA_MILS[i][j] for j in range(len(AOA_ALT))], alt_msl)
               for i in range(len(AOA_KIAS))]
        a1g = _interp(AOA_KIAS, row, kias)
        # AoA = zero-lift offset + lift-dependent part scaling with load factor and weight
        a0 = self.aoa_bias
        return a0 + self.aoa_scale * (a1g - a0) * nz * self.gw_lb / self.ref_gw_lb

# ---------------------------------------------------------------- safe escape
# DSMS escape maneuver codes (JAFDTC EscapeManeuvers): CLB is the jet's name for
# the 3-3 Climbing (CLM) SEM.
SEM_CLB, SEM_TRN, SEM_TLT = "CLB", "TRN", "TLT"

def default_sem(dive_deg, high_drag=False):
    """Default safe escape maneuver for a planned dive angle.
    - 30 deg dive or steeper: CLB (climbing) -- squadron rule.
    - Steeper than 20 deg: CLB, because TRN/TLT are only valid up to 20 deg (3-3 5.6.3/5.6.4).
    - 20 deg or shallower: CLB for low-drag weapons, TLT for high-drag, matching the
      76th / 23FG battle books. The planner can override."""
    if dive_deg >= 30 or dive_deg > 20:
        return SEM_CLB
    return SEM_TLT if high_drag else SEM_CLB

def check_sem(sem, dive_deg):
    """Return a warning string if the chosen SEM is not valid for the dive angle."""
    if sem in (SEM_TRN, SEM_TLT) and dive_deg > 20:
        return f"{sem} is only valid for deliveries up to 20 deg of dive (3-3 5.6); use CLB"
    return None

# ---------------------------------------------------------------- sled
@dataclass
class SledInput:
    weapon: Weapon
    dive: float
    rel_agl: float
    rel_kias: float
    trk_kias: float
    base_kias: float
    qty: int = 1
    spacing_ft: float = 0.0
    tgt_elev: float = 0.0      # target elevation, ft MSL
    temp_c: float = None       # temperature at target, deg C (None = ISA standard day)
    track_time: float = None   # default per 23FG/3-3 rule
    min_alt: float = 1000.0    # MALT, ft above target
    sem: str = None            # None = default by dive angle (see default_sem)

def solve_sled(inp: SledInput, ac: Aircraft):
    temp_c = inp.temp_c if inp.temp_c is not None else 15.0 - 0.0019812 * inp.tgt_elev
    atm = Atmos.for_surface_temp(inp.tgt_elev, temp_c)
    sem = inp.sem or default_sem(inp.dive, inp.weapon.high_drag)
    sem_warning = check_sem(sem, inp.dive)
    w, g = inp.weapon, inp.dive
    h_rel = inp.tgt_elev + inp.rel_agl
    tas = atm.tas(inp.rel_kias, h_rel)
    r = drop(w, atm, h_rel, inp.tgt_elev, tas, g)
    # ripple: stick centred on target -> first bomb lands short by half stick
    half_stick = (inp.qty - 1) * inp.spacing_ft / 2
    br = r["x"] + half_stick
    # last bomb: aircraft continues down the wire; find release interval that
    # gives the planned ground spacing between impacts. DTOF = last bomb TOF.
    dtof_last, interval = r["tof"], 0.0
    if inp.qty > 1 and inp.spacing_ft > 0:
        gr = math.radians(g)
        def impact_after(dt_rel):
            s_wire = tas * dt_rel
            h2 = h_rel - s_wire * math.sin(gr)
            r2 = drop(w, atm, h2, inp.tgt_elev, tas, g)
            return s_wire * math.cos(gr) + r2["x"] - r["x"], r2["tof"]
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if impact_after(mid)[0] < inp.spacing_ft: lo = mid
            else: hi = mid
        interval = (lo + hi) / 2
        # CWDS DTOF matches the centre of the stick
        dtof_last = impact_after(interval * (inp.qty - 1) / 2)[1]
    tan_g = math.tan(math.radians(g))
    aod = inp.rel_agl / tan_g - br
    los = math.degrees(math.atan2(inp.rel_agl, br))
    nz = math.cos(math.radians(g))
    aoa_rel = ac.aoa_mils(inp.rel_kias, h_rel, nz)
    mils = (los - g) * MIL_PER_DEG + aoa_rel
    # track: straight wire, track_time before release, IAS linear trk->rel
    tt = inp.track_time if inp.track_time is not None else 3.0
    steps = 100; s = 0.0; hh = h_rel
    for i in range(steps):  # integrate backwards up the wire
        f = 1 - (i + 0.5) / steps
        kias = inp.trk_kias + (inp.rel_kias - inp.trk_kias) * f
        v = atm.tas(kias, hh)
        ds = v * tt / steps; s += ds; hh += ds * math.sin(math.radians(g))
    trk_agl = inp.rel_agl + s * math.sin(math.radians(g))
    d_trk = trk_agl / tan_g - aod
    itp = math.degrees(math.atan2(trk_agl, d_trk))
    iaa = itp - g
    aoa_trk = ac.aoa_mils(inp.trk_kias, inp.tgt_elev + trk_agl, nz)
    # CWDS convention: IHP + IPP = planned total sight setting, so IHP uses the
    # release-condition AoA (the sight setting set in the jet), not track AoA.
    ihp = iaa * MIL_PER_DEG + aoa_rel
    ipp = mils - ihp
    k = 60 if g == 45 else (70 if g >= 60 else 50)
    base_agl = trk_agl + k * g
    base_dist = base_agl / tan_g - aod
    # wind sensitivities
    hw = 10 * KT
    rh = drop(w, atm, h_rel, inp.tgt_elev, tas, g, wind=(-hw, 0, 0))
    br_h = rh["x"] + half_stick
    # with headwind the ground flight path is steeper; pilot holds the same
    # ground-referenced dive/release alt -> compare required depression
    los_h = math.degrees(math.atan2(inp.rel_agl, br_h))
    ht = abs((los_h - los) * MIL_PER_DEG) / 10
    # crosswind: aircraft drifts with the air mass (wings-level drift method);
    # aim-off upwind, expressed in mils/kt at release slant range (CWDS X/W)
    rx = drop(w, atm, h_rel, inp.tgt_elev, tas, g, wind=(0, 10 * KT, 0))
    sr = math.hypot(inp.rel_agl, br)
    xw_ft = abs(rx["y"]) / 10
    xw = xw_ft / sr * 1000
    e = inp.tgt_elev
    msl = dict(base_msl=base_agl + e, trk_msl=trk_agl + e, rel_msl=inp.rel_agl + e,
               malt_msl=inp.min_alt + e)
    return dict(**msl, sem=sem, sem_warning=sem_warning, temp_c=temp_c, rel_agl=inp.rel_agl,
                tgt_elev=e, dtof=dtof_last, tof_first=r["tof"], interval_s=interval, mils=mils, br=br, aod=aod, trk=trk_agl, itp=itp, iaa=iaa,
                ihp=ihp, ipp=ipp, xw_ft=xw_ft, slant=sr, aoa_trk=aoa_trk, base=base_agl, base_dist=base_dist, ht=ht, xw=xw,
                aoa_rel=aoa_rel, tas_kt=tas / KT, da=atm.density_alt(inp.tgt_elev))
