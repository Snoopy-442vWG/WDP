"""Render a Z-sled card as a PNG in the DAPS card layout.

Altitudes are in thousands of feet, AGL by default (76 vFS / 442 vWG definition: base, track, release and abort are
heights above the target) or MSL (DAPS) with alt_ref="MSL". The target elevation is printed under the sled.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NM = 6076.12
W_PX, H_PX = 620, 840          # card size in pixels at the default dpi
SEM_LABEL = {"CLB": "CLM", "TLT": "TLT", "TRN": "TRN"}   # card shows the 3-3 names


def k(ft):
    return f"{ft / 1000:.1f}"


def render_sled(path, name, weapon_label, r, inp, fuze="N/T", xw_units="mils", alt_ref="AGL", dpi=200):
    """r = solve_sled() result, inp = the SledInput used. xw_units: "mils" (mils/kt, 76 vFS / 23FG, default) or "ft" (ft/kt, DAPS)."""
    fig = plt.figure(figsize=(W_PX / dpi, H_PX / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_PX); ax.set_ylim(H_PX, 0); ax.axis("off")
    LW = 1.0

    def hline(x0, x1, y, lw=LW): ax.plot([x0, x1], [y, y], c="k", lw=lw, solid_capstyle="butt")
    def vline(x, y0, y1, lw=LW): ax.plot([x, x], [y0, y1], c="k", lw=lw, solid_capstyle="butt")
    def txt(x, y, s, size=6.5, bold=False, ha="left", color="k"):
        ax.text(x, y, s, fontsize=size, weight="bold" if bold else "normal", ha=ha, va="center", color=color)

    # frame, title rows
    L, R, T, B = 6, 614, 4, 836
    for y in (T, 56, 108, 628, B): hline(L, R, y)
    vline(L, T, B); vline(R, T, B)
    txt(310, 31, weapon_label, size=15, ha="center")
    txt(310, 83, name, size=15, ha="center")

    # sled geometry (fixed drawing; numbers carry the information)
    base_y, trk_y, rel_y, abt_y = 160, 291, 421, 551
    bx0, bx1 = 108, 183
    def wire_x(y): return 183 + (437 - 183) * (y - base_y) / (abt_y - base_y)
    ax.plot([bx1, wire_x(abt_y)], [base_y, abt_y], c="k", lw=1.6)
    hline(bx0, bx1, base_y, 1.6)
    hline(wire_x(trk_y), wire_x(trk_y) + 75, trk_y, 1.6)
    hline(wire_x(rel_y), wire_x(rel_y) + 75, rel_y, 1.6)
    hline(wire_x(abt_y), wire_x(abt_y) + 75, abt_y, 1.6)

    big = 9.5
    e = inp.tgt_elev if alt_ref == "MSL" else 0.0
    alt = lambda agl: k(agl + e)
    txt(148, base_y - 15, alt(r["base"]), big, True, "center")
    txt(148, base_y + 12, f"{r['base_dist'] / NM:.1f}", 6, True, "center")
    txt(197, base_y - 12, f"{inp.base_kias:.0f}   KTS", 6.5)
    xt = wire_x(trk_y) + 37
    txt(xt, trk_y - 15, alt(r["trk"]), big, True, "center")
    xr = wire_x(rel_y) + 37
    txt(xr, rel_y - 15, alt(r["rel_agl"]), big, True, "center", color="red" if r.get("rel_below_abort") else "k")
    txt(xr + 54, rel_y - 12, f"{inp.rel_kias:.0f}   KTS", 6.5)
    xa = wire_x(abt_y) + 37
    txt(xa, abt_y - 15, alt(r["abort_agl"]), big, True, "center")
    txt(xa + 4, abt_y + 13, r["abort_reason"], 6, True, "center")

    # left column
    txt(112, 252, "AOD:", 6.5); txt(166, 252, f"{r['aod'] / 1000:.1f}", 6.5, True)
    txt(112, 356, "IHP:", 6.5); txt(171, 356, f"{r['ihp']:.0f}", 6.5, True)
    txt(112, 461, "IAA:", 6.5); txt(171, 461, f"{r['iaa']:.1f}", 6.5, True)
    txt(112, 564, "SEM:", 6.5); txt(160, 564, SEM_LABEL.get(r["sem"], r["sem"]), 6.5, True)
    txt(305, 591, f"{inp.tgt_elev:.0f}", 7, True, "right"); txt(318, 591, f"FT TGT ELEV  ·  ALT {alt_ref}", 6.5)
    if r.get("sem_warning"):
        txt(310, 612, "SEM: " + r["sem_warning"], 4.2, ha="center", color="red")
    elif r.get("rel_below_abort"):
        txt(310, 612, "RELEASE IS BELOW ABORT ALTITUDE", 5, True, "center", color="red")

    # bottom table
    rows_y = [628, 685, 736, 787, 836]
    for y in rows_y[1:-1]: hline(L, R, y)
    for x in (108, 355, 455): vline(x, 628, B)
    xw = f"{r['xw_ft']:.0f}" if xw_units == "ft" else f"{r['xw']:.1f}"
    rows = [("MTOF:", f"{r['mtof']:.1f}", "", "MIN ALT:", f"{inp.min_alt:.0f}"),
            ("DTOF:", f"{r['dtof']:.1f}", "", "FUZE:", fuze),
            ("QTY/INT:", f"{inp.qty}", f"{inp.spacing_ft:.0f}" if inp.qty > 1 else "", "H/T:", f"{r['ht']:.1f}"),
            ("MILS/IPP:", f"{r['mils']:.0f}", f"{r['ipp']:.0f}", "XW:", xw)]
    for i, (a, b, c, d, e) in enumerate(rows):
        yc = (rows_y[i] + rows_y[i + 1]) / 2
        txt(20, yc, a, 6.5)
        txt(180, yc, b, 6.5, True, "center")
        if c: txt(270, yc, c, 6.5, True, "center")
        txt(371, yc, d, 6.5)
        txt(532, yc, e, 6.5, True, "center")

    fig.savefig(path, dpi=dpi, facecolor="white")
    plt.close(fig)
    return path


if __name__ == "__main__":
    from engine import Aircraft, SledInput, mk82_ld, solve_sled
    ac = Aircraft(aoa_bias=20, aoa_scale=0.8)
    w = mk82_ld()   # DCS-calibrated
    # same inputs as the DAPS v0.942 example card: 82 45DB2, 3,369 ft target, release alt from the DAPS rule
    inp = SledInput(w, 45, None, 325, 310, 215, 2, 75, tgt_elev=3369)
    r = solve_sled(inp, ac)
    from dataclasses import replace
    inp = replace(inp, rel_agl=r["rel_agl"])
    from engine import dsms_name
    name = dsms_name("82", 45, "DB", 2)
    print(render_sled(f"samples/{name.replace(' ', '_')}_AGL.png", name, "MK-82LD", r, inp))
    print(render_sled(f"samples/{name.replace(' ', '_')}_MSL.png", name, "MK-82LD", r, inp, alt_ref="MSL"))
