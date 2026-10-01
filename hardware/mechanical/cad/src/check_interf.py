"""interference check inside one unit (module or end part): printed vs printed, printed vs bought.
Expected (design) contacts are listed with a reason; everything else is reported."""
import itertools, re, sys, json
from keyaction_parts import build_unit, G
notes=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
EXPECTED = [
    (r"-LEVER-|-FRAME|-PLUG", r"leverrod", "Ø3.9 출력 구멍 → Ø4.0 드릴 (S11, P22) / 마개 압입"),
    (r"-FRAME", r"-PLUG", "마개 Ø4.0 압입 (D18)"),
    (r"-KEY-", r"-CAPSTAN-", "캡스턴 나사가 Ø2.8 자가 잠김 구멍에 나사산을 냄 (D02)"),
    (r"-LEVER-", r"-STEEL-", "레버 쉼 각 회전 계산 오차 (< 0.001 mm)"),
    (r"-LEVER-", r"-FELTSTRIP-", "펠트 띠가 아래 립 끝면과 맞닿음"),
    (r"-FRAME", r"controlboard", "위치 핀 Ø2.8 ↔ 기판 구멍 Ø3.0"),
    (r"-FRAME", r"SBSCREW", "센서 바 M3×10이 Ø2.75 자리에 나사산을 냄 (P36)"),
    (r"-FRAME", r"balancepin", "밸런스 핀 Ø2.0 ↔ 출력 구멍 Ø1.95 가벼운 압입 (P32)"),
    (r"-FRAME", r"keyrod", "봉 받침 R2.05 ↔ 봉 Ø4 다각형 근사 오차 (< 0.01 mm3)"),
]
def unit(tag):
    if tag=='O1': return build_unit(G['parts'],G['plan'],'O1',0.0,'O1',{n:n+'1' for n in notes},None)
    E=G['end_parts']; s={'EL':'left','ER':'right'}[tag]
    return build_unit(E[s]['parts'],E[s]['plan'],tag,0.0,tag,{},s)
def overl(a,b):
    ba=a.solid.bounding_box(); bb=b.solid.bounding_box()
    if any(ba[i]>bb[i+3] or bb[i]>ba[i+3] for i in range(3)): return 0.0
    return (a.solid^b.solid).volume()
def run(tag):
    P=unit(tag); pr=[p for p in P if p.kind=='print']; ot=[p for p in P if p.kind!='print']
    bad=[]; exp=[]
    for a,b in list(itertools.combinations(pr,2))+[(a,b) for a in pr for b in ot]:
        v=overl(a,b)
        if v<=1e-3: continue
        why=None
        for ra,rb,w in EXPECTED:
            if (re.search(ra,a.id) and re.search(rb,b.id)) or (re.search(ra,b.id) and re.search(rb,a.id)):
                if not (re.search(ra,a.id) and re.search(ra,b.id) and ra!=rb): why=w; break
        (exp if why else bad).append((round(v,3),a.id,b.id,why or b.name_ko))
    return bad,exp
if __name__=='__main__':
    for tag in sys.argv[1:] or ['O1','EL','ER']:
        bad,exp=run(tag)
        print('==',tag,'unexpected',len(bad),'expected',len(exp))
        for r in sorted(bad,reverse=True)[:40]: print('  !',r)
        import collections
        c=collections.Counter(r[3] for r in exp)
        for k,v in c.items(): print('   ok',v,k)
