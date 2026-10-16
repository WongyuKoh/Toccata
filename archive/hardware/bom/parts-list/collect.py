"""현재 설계(v3.2 구매 목록 + v4 W1 r4.1 건반 액션) 부품 목록 수집 → rows.json"""
import openpyxl, json, re
V4X='/Users/kwg/Desktop/mydrive/project/Toccata/docs/report/toccata-purchase-list-v4.xlsx'
V4='/private/tmp/claude-501/-Users-kwg-Desktop-mydrive-project-Toccata/2f19e142-4ac2-4c90-bd1e-b3b469f97487/scratchpad/v4'
wb=openpyxl.load_workbook(V4X,data_only=True); ws=wb.worksheets[0]
rows=[]; ships=[]; store=None
for r in ws.iter_rows(min_row=6,values_only=True):
    if r[0] and isinstance(r[0],str) and r[0].startswith('■'): store=r[0][1:].strip(); continue
    if not isinstance(r[0],int): continue
    name=str(r[1]); code=r[10]
    if name.startswith('배송비'):
        ships.append(dict(store=store,seller=name.split('—',1)[1].strip(),fee=r[2],b=r[7],buy=r[8])); continue
    if r[8]!='O': continue
    if code and str(code).startswith('v4'): continue      # r3 건반 액션 → r4 카드로 바꿈
    rows.append(dict(code=code,name=name,unit=r[2],qty=r[3],use=r[4],price=r[5],url=r[6],b=r[7],store=store,seller=r[9] or store,src='v3.2+v4'))
d=json.load(open(f'{V4}/costsel/data_v4.json'))
for c in d['cards']:
    if c['default']!='cur': continue
    for it in c['options'][0]['items']:
        if it['unit']==0: continue   # v3 L40 재사용 (0원)
        st=it['store']; seller=re.sub(r'\s*\(.*$','',st).replace('11번가 ','').strip()
        use=c['role'].split(' · 필요량')[0]
        rows.append(dict(code=c['id'],name=it['name'],unit=it['unit'],qty=it['qty'],use=use,price=it['unit']*it['qty'],url=it['url'],
                         b={'base':'기본','consumable':'소모품','tool':'공구'}[it['b']],store=st,seller=seller,src='v4 r4',ship_fee=it['ship_fee'],ship=it['ship']))
json.dump(dict(rows=rows,ships=ships),open('rows.json','w'),ensure_ascii=False,indent=1)
import collections
print(len(rows)); print(collections.Counter(r['b'] for r in rows))
for s in ships: print('SHIP',s)
sellers=collections.Counter(r['seller'] for r in rows)
print(sellers)
