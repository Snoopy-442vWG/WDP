"""Render a Z-sled card as a PNG, in the 76 vFS / DAPS battle book layout.

Big altitude numbers are MSL (what the altimeter reads), in thousands of feet; the AGL value is shown small
underneath. The header carries the target elevation and temperature the sled was computed for.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

NM = 6076.12


def k(ft):
    return f"{ft / 1000:.1f}"


def render_sled(path, name, weapon_label, r, inp, fuze="N/T", dpi=200):
    """r = solve_sled() result, inp = SledInput used to compute it."""
    W, H = 4.0, 3.2                       # inches (card)
    fig = plt.figure(figsize=(W, H), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100); ax.set_ylim(0, 80); ax.axis("off")
    lw = 0.8
    box = dict(fill=False, lw=lw, ec="black")

    # outer frame + title rows
    ax.add_patch(Rectangle((1, 1), 98, 78, **box))
    ax.plot([1, 99], [72, 72], c="k", lw=lw)
    ax.plot([1, 99], [66, 66], c="k", lw=lw)
    ax.text(50, 75, name, ha="center", va="center", fontsize=11, weight="bold")
    ax.text(50, 69, weapon_label, ha="center", va="center", fontsize=10)

    # conditions line
    ax.text(3, 63.5, f"TGT ELEV {inp.tgt_elev:,.0f}' / {r['temp_c']:.0f}°C", fontsize=4.6, va="center")
    ax.text(97, 63.5, "ALT: MSL (AGL)", fontsize=4.6, va="center", ha="right")

    # BASE/PUP
    base_nm = r["base_dist"] / NM
    ax.text(48, 60.5, "BASE/PUP:", fontsize=4.6, ha="right", va="center")
    ax.text(49, 60.5, f"{base_nm:.1f}NM", fontsize=4.6, va="center")

    # the Z: base (top-left) -> track -> release (bottom-right)
    bx, by = 13, 55            # base label position
    tx, ty = 40, 50.5          # track
    rx, ry = 60, 30            # release
    ax.plot([3, 26], [52.5, 52.5], c="k", lw=1.2)          # base line
    ax.plot([27, 51], [47.5, 47.5], c="k", lw=1.2)         # track line
    ax.plot([25, 55], [55, 26], c="k", lw=1.2)             # dive wire
    ax.plot([50, 70], [26.5, 26.5], c="k", lw=1.2)         # release line
    ax.text(bx, by, k(r["base_msl"]), fontsize=13, weight="bold", ha="center", va="bottom")
    ax.text(bx, 50.5, f"({k(r['base'])})  {base_nm:.1f}", fontsize=4.6, ha="center", va="top")
    ax.text(27.5, 54.5, f"{inp.base_kias:.0f}", fontsize=5.5, va="center")
    ax.text(tx, ty, k(r["trk_msl"]), fontsize=13, weight="bold", ha="center", va="bottom")
    ax.text(tx, 46.5, f"({k(r['trk'])})  {inp.trk_kias:.0f}", fontsize=4.6, ha="center", va="top")
    ax.text(rx, 27.5, k(r["rel_msl"]), fontsize=13, weight="bold", ha="center", va="bottom")
    ax.text(rx, 25.5, f"({k(r['rel_agl'])})", fontsize=4.6, ha="center", va="top")
    ax.text(72, 28.5, f"{inp.rel_kias:.0f}", fontsize=5.5, va="center")

    # RT / UP boxes
    for y, lab in ((49, "RT"), (40, "UP")):
        ax.text(83.5, y + 4, lab, fontsize=5.5, ha="right", va="center")
        ax.add_patch(Rectangle((85, y), 13, 8.5, **box))

    # left column values
    ax.text(3, 40, "AOD:", fontsize=5); ax.text(13, 40, f"{r['aod'] / 1000:.1f}", fontsize=6.5, weight="bold")
    ax.text(5, 31, "IHP:", fontsize=5); ax.text(13, 31, f"{r['ihp']:.0f}", fontsize=6.5, weight="bold")
    ax.text(5, 22, "IAA:", fontsize=5); ax.text(13, 22, f"{r['iaa']:.0f}", fontsize=6.5, weight="bold")
    ax.text(3, 14.5, "SEM:", fontsize=5); ax.text(13, 14.5, r["sem"], fontsize=6.5, weight="bold")
    ax.text(70, 14, "MALT:", fontsize=4.6); ax.text(97, 14, f"{inp.min_alt:.0f}", fontsize=4.6, ha="right")
    if r.get("sem_warning"):
        ax.text(50, 19, "SEM CHECK: " + r["sem_warning"], fontsize=3.6, ha="center", color="red")

    # bottom table
    y0, rh = 1, 4.2
    rows = [("DTOF:", f"{r['dtof']:.1f}", "", "FUZ:", fuze),
            ("Qty/Int:", f"{inp.qty}", f"{inp.spacing_ft:.0f}" if inp.qty > 1 else "", "H/T:", f"{r['ht']:.1f}"),
            ("Mils/IPP:", f"{r['mils']:.0f}", f"{r['ipp']:.0f}", "XW:", f"{r['xw']:.1f}")]
    for i, (a, b, c, d, e) in enumerate(rows):
        y = y0 + rh * (len(rows) - 1 - i)
        ax.plot([1, 99], [y + rh, y + rh], c="k", lw=lw)
        ax.text(2, y + rh / 2, a, fontsize=5, va="center")
        ax.text(38 if c else 47, y + rh / 2, b, fontsize=5, va="center", ha="center")
        if c:
            ax.text(56, y + rh / 2, c, fontsize=5, va="center", ha="center")
        ax.text(70, y + rh / 2, d, fontsize=5, va="center")
        ax.text(97, y + rh / 2, e, fontsize=5, va="center", ha="right")
    ax.plot([68, 68], [1, 1 + rh * 3], c="k", lw=lw)
    ax.plot([84, 84], [1, 1 + rh * 3], c="k", lw=lw)

    fig.savefig(path, dpi=dpi, facecolor="white")
    plt.close(fig)
    return path


if __name__ == "__main__":
    from engine import Aircraft, SledInput, mk82_ld, solve_sled
    ac = Aircraft(aoa_bias=20, aoa_scale=0.8)
    w = mk82_ld(v_eject_fps=10)
    inp = SledInput(w, 30, 3200, 350, 310, 275, 2, 70, tgt_elev=1500, temp_c=20)
    r = solve_sled(inp, ac)
    print(render_sled("82_30DB2.png", "82 30DB2", "MK-82LD", r, inp))
