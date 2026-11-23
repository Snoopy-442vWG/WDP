import sys, math
from engine import *
from refcases import cases
def run(cd_scale=1.0, vej=10.0, aoa_scale=1.0, aoa_bias=0.0, show=True, only_sgl=False):
    ac=Aircraft(aoa_scale=aoa_scale, aoa_bias=aoa_bias)
    rows=[]; err={}
    for c in cases():
        if only_sgl and c['qty']>1: continue
        w=mk82_ld(cd_scale=cd_scale, v_eject_fps=vej)
        r=solve_sled(SledInput(w,c['dive'],c['rel']*1000,c['rel_kias'],c['trk_kias'],c['base_kias'],c['qty'],c['sp'],tgt_elev=1500,temp_c=20),ac)
        d=dict(dtof=r['dtof']-c['dtof'], mils=r['mils']-c['mils'], br=r['br']/1000-c['br'], aod=r['aod']/1000-c['aod'],
               trk=r['trk']/1000-c['trk'], base=r['base']/1000-c['base'], bdist=r['base_dist']/1000-c['base_kft'],
               iaa=r['iaa']-c['iaa'], itp=r['itp']-c['itp'], ihp=r['ihp']-c['ihp'], ipp=r['ipp']-c['ipp'], ht=r['ht']-c['ht'], xw=r['xw']-c['xw'])
        for k,v in d.items(): err.setdefault(k,[]).append(v)
        rows.append((c,r,d))
        if show:
            print(f"{c['name']:9s} DTOF {r['dtof']:5.2f}/{c['dtof']:4.1f} MILS {r['mils']:5.0f}/{c['mils']:3d} BR {r['br']/1000:4.2f}/{c['br']:3.1f} AOD {r['aod']/1000:4.2f}/{c['aod']:3.1f} TRK {r['trk']/1000:4.2f}/{c['trk']:3.1f} BASE {r['base']/1000:5.2f}/{c['base']:4.1f} BD {r['base_dist']/1000:4.2f}/{c['base_kft']:3.1f} ITP {r['itp']:4.1f}/{c['itp']} IAA {r['iaa']:4.1f}/{c['iaa']} IHP {r['ihp']:4.0f}/{c['ihp']} IPP {r['ipp']:3.0f}/{c['ipp']} HT {r['ht']:4.2f}/{c['ht']} XW {r['xw']:4.2f}/{c['xw']}")
    rms={k:math.sqrt(sum(x*x for x in v)/len(v)) for k,v in err.items()}
    bias={k:sum(v)/len(v) for k,v in err.items()}
    return rows,rms,bias
if __name__=='__main__':
    rows,rms,bias=run()
    print({k:round(v,3) for k,v in rms.items()}); print({k:round(v,3) for k,v in bias.items()})
    print('DA', rows[0][1]['da'])
