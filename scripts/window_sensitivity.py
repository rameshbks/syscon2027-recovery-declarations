"""Re-evaluate retained original traces; never collects new HTTP observations."""
from pathlib import Path
import sys,json,collections,argparse
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'stage4'))
from stage4_campaign import evaluate
def compute(base,out):
 keys=json.loads((base/'audit_keys.json').read_text());traces=collections.defaultdict(list)
 for line in (base/'traces.jsonl').open():
  r=json.loads(line);traces[r['session']].append(r)
 result=[]
 for w in (3,5,8,12):
  rows=[]
  for session,t in traces.items():
   rr,_=evaluate(t,bytes.fromhex(keys[session]),session,w)
   r=next(x for x in rr if x['strategy']=='gate_v3')
   rows.append(dict(r,scenario=t[0]['scenario'],seed=t[0]['seed']))
  s={k:sum(r[k] is True for r in rows) for k in ['unsafe_declaration','declaration_missing','post_declaration_failure','followup_censored']}
  s.update(window=w,declared=sum(not r['declaration_missing'] for r in rows),intermittent_future=sum(r['post_declaration_failure'] is True for r in rows if r['scenario']=='intermittent'))
  result.append(s)
 expected=json.loads((ROOT/'original_http/window_sensitivity.json').read_text())
 assert result==expected,'Sensitivity results differ'
 out.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();compute(a.input,a.out)
