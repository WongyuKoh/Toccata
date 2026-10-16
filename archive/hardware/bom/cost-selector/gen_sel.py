"""Toccata v4 재료 절감 선택기 페이지 생성.

입력: data_old.json, imgs_old.json (build_data.py), data_v4.json, imgs_v4.json (build_v4.py)
출력: out/index.html (Artifact 한 파일, 사진은 data URI)
"""
import html, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)
PAGE_CSS = '/Users/kwg/Desktop/mydrive/project/Toccata/docs/report/toccata-build-set/src/page.css'

D = json.load(open(os.path.join(HERE, 'data_old.json')))
IM = json.load(open(os.path.join(HERE, 'imgs_old.json')))
if os.path.exists(os.path.join(HERE, 'data_v4.json')):
    V = json.load(open(os.path.join(HERE, 'data_v4.json')))
    IM.update(json.load(open(os.path.join(HERE, 'imgs_v4.json'))))
    D['cards'] = V['cards'] + D['cards']
    D['ship'].update(V.get('ship', {}))
    D['v4meta'] = V.get('meta', {})
if os.path.exists(os.path.join(HERE, 'removed_r4.json')):
    D['dropped'] = D['dropped'] + json.load(open(os.path.join(HERE, 'removed_r4.json')))
CARDS, SHIP, CATS = D['cards'], D['ship'], D['cats']
PRESETS = json.load(open(os.path.join(HERE, 'presets.json'))) if os.path.exists(os.path.join(HERE, 'presets.json')) else {}

E = lambda s: html.escape(str(s if s is not None else ''), quote=True)
BK = {'base': '기본', 'consumable': '소모품', 'tool': '공구'}


def won(n):
    return f'{int(round(n)):,}'


def opt_price(o):
    return sum(i['qty'] * i['unit'] for i in o['items'])


def img(key, alt):
    if key and key in IM:
        return f'<img src="data:image/jpeg;base64,{IM[key]}" alt="{E(alt)}" loading="lazy">'
    return '<span class="noimg">사진 없음</span>'


def item_html(it):
    amt = it['qty'] * it['unit']
    flags = ''
    if not it.get('verified', True):
        flags += '<span class="fl w">가격 미확인</span>'
    if it['b'] != 'base':
        flags += f'<span class="fl">{BK[it["b"]]}</span>'
    link = f'<a href="{E(it["url"])}" target="_blank" rel="noopener">{E((it.get("store") or "판매처").split(" (")[0])} ↗</a>' if it.get('url') else E(it.get('store') or '')
    note = f'<p class="inote">{E(it["note"])}</p>' if it.get('note') else ''
    spec = f'<p class="inote">{E(it["spec"])}</p>' if it.get('spec') else ''
    return (f'<div class="it"><div class="th">{img(it.get("img"), it["name"])}</div><div class="ib">'
            f'<div class="inm">{E(it["name"])} {flags}</div>{spec}'
            f'<div class="ipp mono">{won(it["qty"])} × {won(it["unit"])} = <b>{won(amt)}</b>원</div>'
            f'<div class="ilk">{link}</div>{note}</div></div>')


def bullets(xs, cls):
    xs = [x for x in xs if x]
    return f'<ul class="{cls}">' + ''.join(f'<li>{E(x)}</li>' for x in xs) + '</ul>' if xs else ''


def card_html(c):
    cur = c['options'][0]
    base_price = opt_price(cur)
    dflt = c.get('default', 'cur')
    rows = []
    for o in c['options']:
        p = opt_price(o)
        d = p - base_price
        dtxt = '' if o['id'] == 'cur' else (f'<span class="dl {"dn" if d < 0 else "up"}">{"−" if d < 0 else "+"}{won(abs(d))}</span>' if d else '<span class="dl">±0</span>')
        badge = ''
        if o['id'] != 'cur':
            badge += f'<span class="src">{E(o.get("src") or "")}</span>' if o.get('src') else ''
            if not o.get('verified', True):
                badge += '<span class="fl w">일부 미확인</span>'
            if o.get('fits') is False:
                badge += f'<span class="fl w">{E(o.get("fitlabel") or "설계 변경 필요")}</span>'
        det = ''.join(item_html(i) for i in o['items'])
        det += bullets(o.get('pros', []), 'pros') + bullets(o.get('cons', []), 'cons')
        if o.get('note'):
            det += f'<p class="onote">{E(o["note"])}</p>'
        if o.get('labor'):
            det += f'<p class="onote">추가 작업: {E(o["labor"])}</p>'
        rows.append(f'''<div class="opt" data-o="{E(o['id'])}"><button type="button" class="ob" aria-pressed="{'true' if o['id'] == dflt else 'false'}" data-c="{E(c['id'])}" data-o="{E(o['id'])}">
<span class="ot">{E(o['title'])}</span><span class="op mono">{won(p)}원</span>{dtxt}{badge}</button>
<details class="od"><summary>내용 보기</summary>{det}</details></div>''')
    rows.append(f'''<div class="opt none" data-o="none"><button type="button" class="ob" aria-pressed="{'true' if dflt == 'none' else 'false'}" data-c="{E(c['id'])}" data-o="none">
<span class="ot">사용 안함</span><span class="op mono">0원</span><span class="dl dn">−{won(base_price)}</span></button>
<p class="unote">{E(c.get('unused', ''))}</p></div>''')
    tag = f'<span class="tag4">4차에서 바뀔 수 있음</span>' if c.get('r4') else ''
    r4n = f'<p class="r4n">4차 메모: {E(c["r4note"])}</p>' if c.get('r4note') else ''
    shown = 0 if dflt == 'none' else base_price
    slab = '기본: 사용 안함' if dflt == 'none' else '현재 목록'
    return f'''<article class="pc" id="c-{E(c['id'])}" data-cat="{E(c['cat'])}"><header><div><h4>{E(c['title'])} {tag}</h4><p class="role">{E(c.get('role', ''))}</p>{r4n}</div>
<div class="csum"><span class="mono" data-sum="{E(c['id'])}">{won(shown)}원</span><span class="cstate" data-state="{E(c['id'])}">{slab}</span></div></header>
<div class="opts">{''.join(rows)}</div></article>'''


sections = []
for cat, (cname, cdesc) in CATS.items():
    cs = [c for c in CARDS if c['cat'] == cat]
    if not cs:
        continue
    sections.append(f'<section class="cat" id="cat-{cat}" data-cat="{cat}"><h3>{E(cname)} <span class="cnt mono">{len(cs)}</span></h3><p class="muted small">{E(cdesc)}</p><div class="pcs">{"".join(card_html(c) for c in cs)}</div></section>')

chips = ''.join(f'<button type="button" class="chip" data-f="{cat}">{E(n)}</button>' for cat, (n, _) in CATS.items() if any(c['cat'] == cat for c in CARDS))
dropped = ''.join(f'<li>{E(d["name"])} <span class="mono muted">({E(d["code"])}, {won(d["price"])}원)</span> — {E(d["reason"])}</li>' for d in D['dropped'])

model = dict(cards=[dict(id=c['id'], cat=c['cat'], d=c.get('default', 'cur'), options=[dict(id=o['id'], items=[dict(q=i['qty'], u=i['unit'], b=i['b'], s=i.get('ship'), f=i.get('ship_fee', 0)) for i in o['items']]) for o in c['options']]) for c in CARDS],
             ship={k: dict(fee=v['fee'], b=v['b'], thr=v.get('thr'), vat=v.get('vat', False), label=v.get('label', k)) for k, v in SHIP.items()},
             presets=PRESETS)

css = open(PAGE_CSS, encoding='utf-8').read()
extra = r'''
.sumbar{position:sticky;top:env(safe-area-inset-top,0px);z-index:20;background:color-mix(in srgb,var(--paper) 94%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--rule)}
.sumbar .wrap{display:grid;grid-template-columns:repeat(4,minmax(0,1fr)) auto;gap:10px;align-items:center;padding-block:10px}
.sk{display:flex;flex-direction:column;gap:1px}
.sk span{font-size:11.5px;color:var(--ink-3)}
.sk b{font-family:var(--mono);font-size:17px;font-variant-numeric:tabular-nums}
.sk i{font-style:normal;font-family:var(--mono);font-size:12px}
.sk i.dn{color:var(--good)} .sk i.up{color:var(--felt)}
.limit{grid-column:1/-1;height:6px;border-radius:3px;background:var(--rule);overflow:hidden}
.limit span{display:block;height:100%;background:var(--blue);width:0}
.sbtns{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.sbtns button,.chip,.pbtn{font:inherit;font-size:13px;border:1px solid var(--rule-2);background:var(--card);color:var(--ink);border-radius:8px;padding:6px 10px;cursor:pointer}
.sbtns button:hover,.chip:hover,.pbtn:hover{border-color:var(--blue)}
@media (max-width:760px){.sumbar .wrap{grid-template-columns:repeat(2,minmax(0,1fr))}.sbtns{grid-column:1/-1;justify-content:flex-start}}
.tools{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:14px 0}
.chip[aria-pressed="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.pbtn[aria-pressed="true"]{background:var(--tint-blue);border-color:var(--blue);color:var(--blue-ink)}
.cat{margin-top:26px}
.cat h3{margin:0 0 2px}
.cnt{font-size:12px;color:var(--ink-3);font-weight:500}
.pcs{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px;margin-top:10px}
@media (max-width:420px){.pcs{grid-template-columns:minmax(0,1fr)}}
.pc{background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:12px 12px 10px;display:flex;flex-direction:column;gap:8px;min-width:0}
.pc.changed{border-color:var(--blue)}
.pc.unused{border-color:var(--felt)}
.pc header{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.pc h4{font-size:15px;line-height:1.35;margin:0}
.pc .role{font-size:12.5px;color:var(--ink-2);margin:3px 0 0;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.csum{text-align:right;display:flex;flex-direction:column;gap:2px;flex:none}
.csum .mono{font-weight:600}
.cstate{font-size:11px;color:var(--ink-3)}
.pc.changed .cstate{color:var(--blue)} .pc.unused .cstate{color:var(--felt)}
.tag4{display:inline-block;font-size:10.5px;font-weight:500;background:var(--tint-amber);color:var(--amber);border-radius:5px;padding:1px 6px;vertical-align:2px}
.opts{display:flex;flex-direction:column;gap:6px}
.ob{width:100%;display:flex;flex-wrap:wrap;gap:4px 8px;align-items:baseline;text-align:left;font:inherit;font-size:13.5px;background:var(--paper);color:var(--ink);border:1px solid var(--rule);border-radius:9px;padding:8px 10px;cursor:pointer}
.ob:hover{border-color:var(--blue)}
.ob[aria-pressed="true"]{border-color:var(--blue);background:var(--tint-blue);box-shadow:inset 3px 0 0 var(--blue)}
.none .ob[aria-pressed="true"]{border-color:var(--felt);background:var(--felt-soft);box-shadow:inset 3px 0 0 var(--felt)}
.ot{flex:1 1 60%;min-width:0}
.op{font-weight:600}
.dl{font-family:var(--mono);font-size:12px;color:var(--ink-3)}
.dl.dn{color:var(--good)} .dl.up{color:var(--felt)}
.src{font-size:11px;color:var(--ink-3);border:1px solid var(--rule);border-radius:5px;padding:0 5px}
.fl{font-size:10.5px;border-radius:5px;padding:0 5px;background:var(--rule);color:var(--ink-2)}
.fl.w{background:var(--tint-amber);color:var(--amber)}
.od summary{font-size:12px;color:var(--blue);cursor:pointer;padding:3px 2px;list-style:none}
.od summary::-webkit-details-marker{display:none}
.od summary::before{content:"＋ ";font-family:var(--mono)}
.od[open] summary::before{content:"－ "}
.od{padding:0 2px}
.it{display:grid;grid-template-columns:64px 1fr;gap:9px;padding:7px 0;border-top:1px dashed var(--rule)}
.th{width:64px;height:64px;background:#fff;border:1px solid var(--rule);border-radius:7px;overflow:hidden;display:grid;place-items:center}
.th img{width:100%;height:100%;object-fit:contain}
.noimg{font-size:10px;color:#7E889A;text-align:center}
.inm{font-size:13px;line-height:1.35}
.ipp{font-size:12px;color:var(--ink-2)}
.ilk a{font-size:12px}
.inote,.onote,.unote{font-size:12px;color:var(--ink-2);margin:3px 0 0;max-width:none}
.unote{padding:0 4px}
.pros,.cons{margin:6px 0 0;padding-left:1.1em;font-size:12.5px}
.pros li::marker{content:"＋ ";color:var(--good)} .cons li::marker{content:"－ ";color:var(--felt)}
.hidden-card{display:none}
.drops{font-size:13px;color:var(--ink-2)}
.r4n{font-size:11.5px;color:var(--amber);margin:4px 0 0;max-width:none}
#copied{font-size:12px;color:var(--good)}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;color:var(--ink-2);margin:10px 0 4px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.lg{display:inline-block;width:18px;height:12px;border-radius:3px;border:2px solid var(--rule-2)}
.lg-sel{background:var(--tint-blue);border-color:var(--blue);border-left-width:4px}
.lg-chg{border-color:var(--blue);background:var(--card)}
.lg-none{border-color:var(--felt);background:var(--card)}
.pc.changed{box-shadow:0 0 0 1px var(--blue)}
.pc.unused{box-shadow:0 0 0 1px var(--felt)}

.shipd summary{cursor:pointer;color:var(--blue)}
.shipd p{max-width:none}
'''
js = r'''
(function(){
const M=__MODEL__;
const byId={}; M.cards.forEach(c=>{byId[c.id]=c});
const KEY='toccata-v4-costsel';
let sel={};
try{ sel=JSON.parse(localStorage.getItem(KEY)||'{}')||{}; }catch(e){ sel={}; }
function idOf(c){ return (c.id in sel)? sel[c.id] : c.d; }
function optOf(c){ const id=idOf(c); if(id==='none') return null; return c.options.find(o=>o.id===id)||c.options[0]; }
function price(o){ return o? o.items.reduce((s,i)=>s+i.q*i.u,0):0; }
function totals(pick){
  const t={base:0,consumable:0,tool:0}; const grp={};
  M.cards.forEach(c=>{ const o=pick(c); if(!o) return; o.items.forEach(i=>{ const a=i.q*i.u; t[i.b]+=a;
    if(i.s){ const g=grp[i.s]||(grp[i.s]={sum:0,f:0,b:i.b}); g.sum+=a; if(i.f) g.f=Math.max(g.f,i.f); } }); });
  const ships=[];
  Object.entries(grp).forEach(([k,g])=>{ const r=M.ship[k]; let fee=0,b=g.b;
    if(r){ b=r.b; if(r.thr){ const ord=r.vat? g.sum/1.1 : g.sum; fee= ord<r.thr? r.fee:0; } else fee=r.fee; }
    else fee=g.f||0;
    if(fee){ t[b]+=fee; ships.push([r?r.label:k.replace(/^O:/,''),fee]); } });
  return {t,ships};
}
const BASE=totals(c=>c.d==='none'?null:(c.options.find(o=>o.id===c.d)||c.options[0]));
const fmt=n=>Math.round(n).toLocaleString('ko-KR');
function sgn(d){ return d===0?'±0':(d<0?'−':'+')+fmt(Math.abs(d)); }
function render(){
  const {t,ships}=totals(optOf);
  const all=t.base+t.consumable+t.tool, all0=BASE.t.base+BASE.t.consumable+BASE.t.tool;
  [['base',t.base,BASE.t.base],['consumable',t.consumable,BASE.t.consumable],['tool',t.tool,BASE.t.tool],['all',all,all0]].forEach(([k,v,v0])=>{
    const el=document.querySelector('[data-k="'+k+'"]'); if(!el) return;
    el.querySelector('b').textContent=fmt(v)+'원';
    const i=el.querySelector('i'); const d=v-v0; i.textContent=sgn(d); i.className=d<0?'dn':(d>0?'up':''); });
  const lim=document.querySelector('.limit span'); if(lim) lim.style.width=Math.min(100,t.base/10000)+'%';
  const lt=document.getElementById('limtxt'); if(lt) lt.textContent='기본 구성 '+fmt(t.base)+'원 / 한도 1,000,000원 ('+Math.round(t.base/10000)+'%)';
  const sh=document.getElementById('shiplist'); if(sh) sh.textContent=ships.length? ships.map(s=>s[0]+' '+fmt(s[1])+'원').join(' · ') : '없음';
  const ss=document.getElementById('shipsum'); if(ss) ss.textContent=ships.length+'곳 · '+fmt(ships.reduce((a,s)=>a+s[1],0))+'원';
  let changed=0, unused=0;
  M.cards.forEach(c=>{ const id=idOf(c); const card=document.getElementById('c-'+c.id); if(!card) return;
    card.querySelectorAll('.ob').forEach(b=>b.setAttribute('aria-pressed', b.dataset.o===id?'true':'false'));
    card.classList.toggle('changed', id!==c.d && id!=='none'); card.classList.toggle('unused', id==='none' && c.d!=='none');
    if(id!==c.d){ if(id==='none') unused++; else changed++; }
    const o=optOf(c); card.querySelector('[data-sum]').textContent=fmt(price(o))+'원';
    const lab=id===c.d?(c.d==='none'?'기본: 사용 안함':'현재 목록'):(id==='none'?'사용 안함':(id==='cur'?'현재 목록':'절감안 선택'));
    card.querySelector('[data-state]').textContent=lab; });
  const cc=document.getElementById('chg'); if(cc) cc.textContent='바꾼 부품 '+changed+' · 사용 안함 '+unused;
  document.querySelectorAll('.pbtn').forEach(b=>{ const p=b.dataset.p; const ps=p==='cur'?{}:(M.presets[p]||{}).sel||{};
    const same=M.cards.every(c=>idOf(c)===((c.id in ps)?ps[c.id]:c.d)); b.setAttribute('aria-pressed',same?'true':'false'); });
  try{ localStorage.setItem(KEY, JSON.stringify(sel)); }catch(e){}
}
document.addEventListener('click',e=>{
  const b=e.target.closest('.ob'); if(b){ const c=b.dataset.c, o=b.dataset.o; if(o===byId[c].d) delete sel[c]; else sel[c]=o; render(); return; }
  const p=e.target.closest('.pbtn'); if(p){ sel = p.dataset.p==='cur'? {} : Object.assign({}, (M.presets[p.dataset.p]||{}).sel||{}); render(); return; }
  const f=e.target.closest('.chip'); if(f){ const on=f.getAttribute('aria-pressed')!=='true';
    document.querySelectorAll('.chip').forEach(x=>x.setAttribute('aria-pressed','false')); if(on) f.setAttribute('aria-pressed','true');
    const cat=on?f.dataset.f:null; document.querySelectorAll('section.cat').forEach(s=>{ s.hidden = !!cat && s.dataset.cat!==cat; }); return; }
  if(e.target.id==='copy'){ const lines=M.cards.filter(c=>idOf(c)!==c.d).map(c=>c.id+'='+idOf(c));
    const txt=lines.length? lines.join('; ') : '(현재 목록 그대로)';
    const done=()=>{ const s=document.getElementById('copied'); if(s){ s.textContent='복사했습니다'; setTimeout(()=>{s.textContent=''},2000);} };
    if(navigator.clipboard&&navigator.clipboard.writeText){ navigator.clipboard.writeText(txt).then(done,()=>{ const ta=document.getElementById('codebox'); ta.value=txt; ta.hidden=false; ta.select(); }); }
    else { const ta=document.getElementById('codebox'); ta.value=txt; ta.hidden=false; ta.select(); }
  }
  if(e.target.id==='reset'){ sel={}; render(); }
});
render();
})();
'''
meta = D.get('v4meta', {})
presets_html = ''.join(f'<button type="button" class="pbtn" data-p="{E(k)}" title="{E(v.get("desc", ""))}">{E(v["label"])}</button>' for k, v in PRESETS.items())
page = f'''<title>Toccata v4 재료 절감</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">
<style>{css}{extra}</style>
<header class="tb"><div class="wrap"><div><div class="kicker">Toccata · v4 재료 목록 · 절감 선택</div>
<h1>재료 목록과 절감 선택</h1>
<p class="sub">지금 구매 목록(v3.2 + 고르신 절감 22개)에 v4 건반 액션(4차 설계)을 반영한 목록입니다. 부품마다 현재 목록, 더 싼 대안, 사용 안함 중 하나를 고르면 합계가 바로 바뀝니다.</p></div>
<div class="tbgrid"><div><b>날짜</b>2026-09-28</div><div><b>기준</b>구매 목록 + v4 4차</div><div><b>부품 카드</b>{len(CARDS)}</div><div><b>한도</b>기본 100만원</div></div></div></header>
<div class="sumbar" role="region" aria-label="합계"><div class="wrap">
<div class="sk" data-k="base"><span>기본 구성</span><b>0원</b><i></i></div>
<div class="sk" data-k="consumable"><span>소모품</span><b>0원</b><i></i></div>
<div class="sk" data-k="tool"><span>공구</span><b>0원</b><i></i></div>
<div class="sk" data-k="all"><span>합계 (배송비 포함)</span><b>0원</b><i></i></div>
<div class="sbtns"><button type="button" id="copy">선택 코드 복사</button><button type="button" id="reset">처음으로</button></div>
<div class="limit" aria-hidden="true"><span></span></div>
</div></div>
<main class="wrap">
<div class="tools"><span class="small muted">묶음 선택</span>{presets_html}<span class="small muted" id="chg"></span><span id="copied" aria-live="polite"></span></div>
<textarea id="codebox" hidden rows="2" style="width:100%" aria-label="선택 코드"></textarea>
<p class="small muted" id="limtxt"></p><details class="shipd small muted"><summary>붙는 배송비 <span id="shipsum"></span></summary><p id="shiplist"></p></details>
<div class="legend small"><span><i class="lg lg-sel"></i>카드 안 파란 칸 = 그 부품에서 지금 고른 항목</span><span><i class="lg lg-chg"></i>파란 카드 테두리 = 현재 목록에서 바꾼 부품</span><span><i class="lg lg-none"></i>빨간 카드 테두리 = 사용 안함</span><span>카드 금액은 물건값만, 배송비는 맨 위 합계에서 판매처마다 한 번 더함</span></div>
<div class="tools"><span class="small muted">분야</span>{chips}</div>
<div class="note small">초록 숫자는 현재 목록보다 싸진 금액입니다. "가격 미확인" 표시는 판매 페이지를 열어 확인하지 못한 가격입니다. 고른 내용은 이 브라우저에만 저장됩니다. 확정하려면 "선택 코드 복사"를 눌러 대화창에 붙여 주세요.</div>
{''.join(sections)}
<section class="cat"><h3>v4에서 목록에서 뺀 부품</h3><ul class="drops">{dropped}</ul></section>
</main>
<footer><div class="wrap">가격은 표시가 없는 한 2026-09-24~28에 판매 페이지에서 확인한 값입니다(VAT 포함). 배송비는 판매처마다 한 번만 붙고, 아이씨뱅큐·엘레파츠·Bambu Lab은 주문 금액이 무료배송 기준을 넘으면 0원입니다.</div></footer>
<script>{js.replace('__MODEL__', json.dumps(model, ensure_ascii=False))}</script>
'''
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(page)
print('cards', len(CARDS), 'bytes', len(page.encode()))
