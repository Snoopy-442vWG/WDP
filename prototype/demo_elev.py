from engine import *
ac = Aircraft(aoa_bias=20, aoa_scale=0.8)
w = mk82_ld()
print("82 45DB2 (5,000 ft AGL release, 350 KIAS, 2 @ 70 ft) at different target elevations")
print(f"{'Elev':>6} {'Temp':>5} {'BASE MSL':>8} {'TRK MSL':>7} {'REL MSL':>7} {'MALT MSL':>8} {'TAS':>4} {'DTOF':>5} {'MILS':>4} {'AOD':>5} {'BR':>5} {'IHP':>4} {'IPP':>3} {'XW':>4} SEM")
for elev, t in [(0, None), (1500, 20), (3369, None), (5000, None), (5000, 30)]:
    r = solve_sled(SledInput(w, 45, 5000, 350, 310, 250, 2, 70, tgt_elev=elev, temp_c=t), ac)
    print(f"{elev:6d} {r['temp_c']:5.1f} {r['base_msl']:8.0f} {r['trk_msl']:7.0f} {r['rel_msl']:7.0f} {r['malt_msl']:8.0f} {r['tas_kt']:4.0f} {r['dtof']:5.2f} {r['mils']:4.0f} {r['aod']:5.0f} {r['br']:5.0f} {r['ihp']:4.0f} {r['ipp']:3.0f} {r['xw']:4.1f} {r['sem']}")
print()
print("SEM defaults / checks")
for dive, hd in [(0,True),(10,True),(20,False),(20,True),(25,False),(30,False),(45,True),(60,False)]:
    print(f"  {dive:2d} deg {'HD' if hd else 'LD'} -> {default_sem(dive, hd)}")
print("  TLT at 45 deg ->", check_sem("TLT", 45))
print("  TLT at 20 deg ->", check_sem("TLT", 20))
